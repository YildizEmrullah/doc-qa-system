"""
Embedding servisi.
OpenAI text-embedding veya yerel sentence-transformers ile
metin vektörleştirme yapar. API anahtarı yoksa mock vektörler üretir.
"""

import logging
import random
from typing import List

from app.config import settings

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Metin embedding'i üretir; provider otomatik seçilir"""

    def __init__(self):
        self.provider: str = ""
        self.model_name: str = ""
        self.dimension: int = 384
        self._client = None
        self._local_model = None

        if settings.OPENAI_API_KEY:
            self._init_openai()
        else:
            self._init_local()

    # ─── Başlatıcılar ─────────────────────────────────────────────

    def _init_openai(self):
        """OpenAI embedding client'ını başlatır. Kota yoksa yerel modele geçer."""
        from openai import OpenAI
        client = OpenAI(api_key=settings.OPENAI_API_KEY)

        # Kota kontrolü — küçük bir test isteği gönder
        try:
            client.embeddings.create(model=settings.EMBEDDING_MODEL, input=["test"])
            self._client = client
            self.provider = "openai"
            self.model_name = settings.EMBEDDING_MODEL
            self.dimension = 1536
            logger.info(f"Embedding: OpenAI/{self.model_name}")
        except Exception as e:
            logger.warning(f"OpenAI kullanılamıyor ({e}). Yerel modele geçiliyor...")
            self._init_local()

    def _init_local(self):
        """Ücretsiz yerel model ile embedding yapar"""
        logger.warning(
            "OPENAI_API_KEY bulunamadı — "
            "sentence-transformers veya mock embedding kullanılacak."
        )
        try:
            from sentence_transformers import SentenceTransformer
            model_id = "all-MiniLM-L6-v2"
            self._local_model = SentenceTransformer(model_id)
            self.provider = "local"
            self.model_name = model_id
            self.dimension = 384
            logger.info(f"Embedding: sentence-transformers/{model_id}")
        except ImportError:
            self.provider = "mock"
            self.model_name = "mock-random"
            self.dimension = 384
            logger.warning(
                "sentence-transformers bulunamadı — "
                "Demo modu: rastgele mock embedding üretilecek."
            )

    # ─── Genel API ────────────────────────────────────────────────

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Metin listesini vektörlere çevirir"""
        if not texts:
            return []

        if self.provider == "openai":
            return self._embed_openai(texts)
        elif self.provider == "local":
            return self._embed_local(texts)
        else:
            return self._embed_mock(texts)

    def embed_query(self, query: str) -> List[float]:
        """Tek bir sorguyu vektöre çevirir"""
        return self.embed_texts([query])[0]

    def get_model_name(self) -> str:
        """Kullanılan provider ve model adını döndürür"""
        return f"{self.provider}/{self.model_name}"

    # ─── Provider İmplementasyonları ─────────────────────────────

    def _embed_openai(self, texts: List[str]) -> List[List[float]]:
        """OpenAI API ile batch embedding üretir. Kota hatası alınırsa yerel modele geçer."""
        try:
            all_embeddings: List[List[float]] = []
            batch_size = 100

            for i in range(0, len(texts), batch_size):
                batch = texts[i : i + batch_size]
                response = self._client.embeddings.create(
                    model=self.model_name,
                    input=batch
                )
                all_embeddings.extend([item.embedding for item in response.data])

            return all_embeddings

        except Exception as e:
            # 429 kota hatası veya başka API hatası → yerel modele geç
            logger.warning(f"OpenAI embedding hatası ({e}). Yerel modele geçiliyor...")
            self._init_local()
            if self.provider == "local":
                return self._embed_local(texts)
            return self._embed_mock(texts)

    def _embed_local(self, texts: List[str]) -> List[List[float]]:
        """sentence-transformers ile yerel embedding üretir"""
        embeddings = self._local_model.encode(
            texts, convert_to_numpy=True, show_progress_bar=False
        )
        return embeddings.tolist()

    def _embed_mock(self, texts: List[str]) -> List[List[float]]:
        """Test amaçlı rastgele vektörler üretir (gerçek anlam yok)"""
        return [
            [random.uniform(-1.0, 1.0) for _ in range(self.dimension)]
            for _ in texts
        ]


# ─── Singleton ────────────────────────────────────────────────────

_instance: EmbeddingService | None = None


def get_embedding_service() -> EmbeddingService:
    """EmbeddingService singleton'ını döndürür"""
    global _instance
    if _instance is None:
        _instance = EmbeddingService()
    return _instance
