"""
RAG (Retrieval-Augmented Generation) pipeline servisi.
Doküman yükleme ve soru-cevap iş akışını uçtan uca yönetir.
"""

import json
import logging
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

from app.config import settings
from app.models.schemas import (
    AskResponse,
    DocumentMetadata,
    Source,
    UploadResponse,
)
from app.services.document_loader import load_document
from app.services.embedding_service import get_embedding_service
from app.services.llm_service import generate_answer, _is_summary_question
from app.services.text_splitter import split_text
from app.services.vector_store import get_vector_store

logger = logging.getLogger(__name__)

# Doküman metadata'sı için JSON dosya yolu
_DOCS_DB = settings.DATA_DIR / "documents.json"


# ─── Metadata Veritabanı (basit JSON) ────────────────────────────

def _load_docs() -> List[Dict[str, Any]]:
    """Doküman listesini JSON dosyasından yükler"""
    if not _DOCS_DB.exists():
        return []
    with open(_DOCS_DB, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_docs(docs: List[Dict[str, Any]]) -> None:
    """Doküman listesini JSON dosyasına yazar"""
    with open(_DOCS_DB, "w", encoding="utf-8") as f:
        json.dump(docs, f, ensure_ascii=False, indent=2, default=str)


# ─── Pipeline: Doküman İşleme ─────────────────────────────────────

def process_document(file_path: Path, original_filename: str) -> UploadResponse:
    """
    Yükleme pipeline'ı:
    1. Metni çıkar (PDF/TXT)
    2. Chunk'lara böl
    3. Embedding oluştur
    4. Vektör deposuna kaydet
    5. Metadata'yı JSON'a kaydet

    Args:
        file_path:         Diske kaydedilmiş dosyanın yolu
        original_filename: Kullanıcının yüklediği orijinal dosya adı

    Returns:
        UploadResponse (başarı/hata bilgisi + doküman metadata'sı)
    """
    doc_id   = uuid.uuid4().hex[:12]
    file_ext = file_path.suffix.lower().lstrip(".")

    logger.info(f"▶ Doküman işleniyor: {original_filename} (ID: {doc_id})")

    # 1. Metin çıkarma
    logger.info("  [1/4] Metin çıkarılıyor...")
    pages = load_document(file_path)
    page_count = len(pages) if file_ext == "pdf" else 1

    # 2. Chunking
    logger.info("  [2/4] Chunk'lara bölünüyor...")
    chunks = split_text(
        pages=pages,
        document_id=doc_id,
        filename=original_filename,
    )
    if not chunks:
        raise ValueError("Doküman işlendikten sonra hiç chunk oluşmadı.")

    # 3. Embedding üretimi
    logger.info(f"  [3/4] {len(chunks)} chunk için embedding oluşturuluyor...")
    emb_service = get_embedding_service()
    texts       = [c["text"] for c in chunks]
    embeddings  = emb_service.embed_texts(texts)

    # 4. Vektör deposuna kayıt
    logger.info("  [4/4] Vektör deposuna kaydediliyor...")
    vec_store = get_vector_store()
    vec_store.add_chunks(chunks, embeddings)

    # 5. Metadata kaydet
    doc_meta: Dict[str, Any] = {
        "id":            doc_id,
        "filename":      original_filename,
        "original_name": original_filename,
        "file_type":     file_ext,
        "file_size":     file_path.stat().st_size,
        "page_count":    page_count,
        "chunk_count":   len(chunks),
        "created_at":    datetime.now().isoformat(),
        "status":        "ready",
    }
    docs = _load_docs()
    docs.append(doc_meta)
    _save_docs(docs)

    logger.info(f"✔ İşlem tamamlandı: {doc_id} ({len(chunks)} chunk)")

    return UploadResponse(
        success=True,
        message=f"'{original_filename}' başarıyla işlendi.",
        document=DocumentMetadata(**doc_meta),
        chunk_count=len(chunks),
    )


# ─── Pipeline: Soru-Cevap ─────────────────────────────────────────

def answer_question(
    question: str,
    document_id: Optional[str] = None,
    top_k: int = 5,
) -> AskResponse:
    """
    RAG sorgu pipeline'ı:
    1. Soruyu embedding'e çevir
    2. En alakalı chunk'ları bul (retrieval)
    3. LLM ile cevap üret
    4. Cevap + kaynakları döndür

    Args:
        question:    Kullanıcının sorusu
        document_id: Belirli bir dokümana sınırla (None = tümünde ara)
        top_k:       Kaç kaynak getirilecek

    Returns:
        AskResponse (cevap metni + kaynak listesi + süre)
    """
    t0 = time.time()
    logger.info(f"❓ Soru: '{question[:60]}...'")

    # 1. Soru embedding'i
    emb_service = get_embedding_service()
    query_vec   = emb_service.embed_query(question)

    # Özet/genel sorular için daha fazla chunk getir
    effective_top_k = 15 if _is_summary_question(question) else top_k

    # 2. Benzerlik araması
    vec_store = get_vector_store()
    similar   = vec_store.search(
        query_embedding=query_vec,
        top_k=effective_top_k,
        document_id=document_id,
    )

    # 3. LLM cevap üretimi
    answer = generate_answer(question, similar)

    # 4. Kaynakları formatla
    sources = [
        Source(
            text=c["text"],
            filename=c["metadata"].get("filename", "?"),
            page_number=c["metadata"].get("page_number", 0),
            chunk_index=c["metadata"].get("chunk_index", 0),
            similarity_score=c.get("score", 0.0),
        )
        for c in similar
    ]

    elapsed = int((time.time() - t0) * 1000)
    model   = settings.LLM_MODEL if settings.OPENAI_API_KEY else "demo-mode"

    logger.info(f"✔ Cevap üretildi ({elapsed}ms)")

    return AskResponse(
        answer=answer,
        sources=sources,
        processing_time_ms=elapsed,
        model_used=model,
    )


# ─── Doküman Yönetimi ────────────────────────────────────────────

def list_documents() -> List[DocumentMetadata]:
    """Yüklenmiş tüm dokümanların metadata listesini döndürür"""
    docs = _load_docs()
    return [DocumentMetadata(**d) for d in docs]


def delete_document(document_id: str) -> Tuple[bool, str]:
    """
    Dokümanı sistemden komple siler:
    - Vektör deposundan chunk'ları sil
    - Yüklenen dosyayı sil
    - Metadata JSON'dan kaldır

    Returns:
        (başarı: bool, mesaj: str)
    """
    docs = _load_docs()
    doc  = next((d for d in docs if d["id"] == document_id), None)

    if not doc:
        return False, f"Doküman bulunamadı: {document_id}"

    # Vektör deposundan sil
    vec_store     = get_vector_store()
    deleted_count = vec_store.delete_document(document_id)

    # Dosyayı diskten sil
    file_path = settings.UPLOAD_DIR / doc.get("filename", "")
    if file_path.exists():
        file_path.unlink()

    # JSON kayıttan çıkar
    _save_docs([d for d in docs if d["id"] != document_id])

    msg = f"'{doc['filename']}' silindi ({deleted_count} chunk kaldırıldı)."
    logger.info(msg)
    return True, msg
