"""
Uygulama konfigürasyonu.
Tüm ayarlar .env dosyasından yüklenir.
"""

from pydantic_settings import BaseSettings
from pathlib import Path
from typing import Set
import logging

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """Uygulama ayarları - .env dosyasından okunur"""

    # ─── API Anahtarları ──────────────────────────────────────────
    OPENAI_API_KEY: str = ""
    GROQ_API_KEY: str = ""

    # ─── Model Ayarları ───────────────────────────────────────────
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    LLM_MODEL: str = "gpt-4o-mini"
    VECTOR_DB: str = "chroma"

    # ─── RAG Parametreleri ────────────────────────────────────────
    CHUNK_SIZE: int = 800          # Chunk başına karakter sayısı
    CHUNK_OVERLAP: int = 150       # Chunk'lar arası örtüşme
    TOP_K_RESULTS: int = 5         # Retrieval sonuç sayısı
    MAX_TOKENS: int = 1500         # LLM maksimum çıktı token'ı

    # ─── Dosya Ayarları ───────────────────────────────────────────
    MAX_FILE_SIZE_MB: int = 50
    ALLOWED_EXTENSIONS: Set[str] = {".pdf", ".txt"}

    # ─── Dizin Yolları ────────────────────────────────────────────
    UPLOAD_DIR: Path = Path("uploads")
    DATA_DIR: Path = Path("data")
    VECTOR_STORE_DIR: Path = Path("vector_store")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Global ayarlar nesnesi
settings = Settings()

# Gerekli dizinleri oluştur
settings.UPLOAD_DIR.mkdir(exist_ok=True)
settings.DATA_DIR.mkdir(exist_ok=True)
settings.VECTOR_STORE_DIR.mkdir(exist_ok=True)

# Placeholder dosyaları oluştur (git takibi için)
(settings.UPLOAD_DIR / ".gitkeep").touch()
(settings.DATA_DIR / ".gitkeep").touch()
(settings.VECTOR_STORE_DIR / ".gitkeep").touch()
