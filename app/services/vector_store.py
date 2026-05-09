"""
Vektör veritabanı servisi.
ChromaDB kullanarak chunk embedding'lerini saklar ve benzerlik araması yapar.
Veriler disk'e kalıcı olarak yazılır (yeniden başlatmada kaybolmaz).
"""

import logging
from typing import List, Dict, Any, Optional

import chromadb

from app.config import settings

logger = logging.getLogger(__name__)


class ChromaVectorStore:
    """ChromaDB tabanlı vektör deposu"""

    COLLECTION_NAME = "document_chunks"

    def __init__(self):
        # Disk'e kalıcı olarak yaz
        self._client = chromadb.PersistentClient(
            path=str(settings.VECTOR_STORE_DIR)
        )
        # Cosine similarity için koleksiyon oluştur/aç
        self._collection = self._client.get_or_create_collection(
            name=self.COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
        logger.info(
            f"Vektör deposu hazır — "
            f"dizin: {settings.VECTOR_STORE_DIR}, "
            f"toplam chunk: {self._collection.count()}"
        )

    # ─── Yazma ────────────────────────────────────────────────────

    def add_chunks(
        self,
        chunks: List[Dict[str, Any]],
        embeddings: List[List[float]],
    ) -> None:
        """
        Chunk'ları embedding'leriyle birlikte veritabanına ekler.

        Args:
            chunks:     split_text() çıktısı (id, text, metadata alanları gerekli)
            embeddings: Her chunk için embedding vektörü
        """
        if not chunks:
            return

        self._collection.add(
            ids=[c["id"] for c in chunks],
            embeddings=embeddings,
            documents=[c["text"] for c in chunks],
            metadatas=[
                {
                    "document_id": c["document_id"],
                    "filename":    c["filename"],
                    "page_number": c["page_number"],
                    "chunk_index": c["chunk_index"],
                }
                for c in chunks
            ],
        )
        logger.info(f"{len(chunks)} chunk eklendi")

    # ─── Okuma ────────────────────────────────────────────────────

    def search(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        document_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Sorgu vektörüne en yakın chunk'ları döndürür.

        Args:
            query_embedding: Sorgunun vektör temsili
            top_k:           Kaç sonuç isteniyor
            document_id:     Belirli bir dokümana filtrele (None = hepsi)

        Returns:
            [{"id", "text", "metadata", "score"}, ...]  (score: 0-1, yüksek = iyi)
        """
        total = self._collection.count()
        if total == 0:
            return []

        n_results = min(top_k, total)
        where_filter = {"document_id": document_id} if document_id else None

        results = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=where_filter,
            include=["documents", "metadatas", "distances"],
        )

        chunks = []
        for i in range(len(results["ids"][0])):
            # ChromaDB cosine mesafesini (0=özdeş, 2=zıt) similarity'ye çevir
            similarity = round(1.0 - results["distances"][0][i], 4)
            chunks.append({
                "id":       results["ids"][0][i],
                "text":     results["documents"][0][i],
                "metadata": results["metadatas"][0][i],
                "score":    similarity,
            })

        return chunks

    # ─── Silme ────────────────────────────────────────────────────

    def delete_document(self, document_id: str) -> int:
        """
        Bir dokümana ait tüm chunk'ları siler.

        Returns:
            Silinen chunk sayısı
        """
        existing = self._collection.get(
            where={"document_id": document_id},
            include=[],
        )
        ids = existing["ids"]

        if ids:
            self._collection.delete(ids=ids)
            logger.info(f"Silindi: {len(ids)} chunk (doküman: {document_id})")

        return len(ids)

    # ─── İstatistikler ────────────────────────────────────────────

    def get_total_chunks(self) -> int:
        """Toplam chunk sayısını döndürür"""
        return self._collection.count()

    def get_document_chunk_count(self, document_id: str) -> int:
        """Belirli bir dokümanın chunk sayısını döndürür"""
        result = self._collection.get(
            where={"document_id": document_id},
            include=[],
        )
        return len(result["ids"])


# ─── Singleton ────────────────────────────────────────────────────

_instance: ChromaVectorStore | None = None


def get_vector_store() -> ChromaVectorStore:
    """ChromaVectorStore singleton'ını döndürür"""
    global _instance
    if _instance is None:
        _instance = ChromaVectorStore()
    return _instance
