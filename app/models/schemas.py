"""
Pydantic veri modelleri.
API istek ve yanıtları için tip güvenli şemalar.
"""

from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


# ─── Doküman Modelleri ────────────────────────────────────────────

class DocumentMetadata(BaseModel):
    """Yüklenen bir dokümanın metadata bilgisi"""
    id: str
    filename: str
    original_name: str
    file_type: str              # "pdf" veya "txt"
    file_size: int              # Bayt cinsinden
    page_count: int
    chunk_count: int
    created_at: datetime
    status: str = "ready"       # "processing" | "ready" | "error"


class UploadResponse(BaseModel):
    """Doküman yükleme yanıtı"""
    success: bool
    message: str
    document: Optional[DocumentMetadata] = None
    chunk_count: int = 0


class DocumentListResponse(BaseModel):
    """Doküman listesi yanıtı"""
    documents: List[DocumentMetadata]
    total: int


class DeleteResponse(BaseModel):
    """Doküman silme yanıtı"""
    success: bool
    message: str


# ─── Soru-Cevap Modelleri ────────────────────────────────────────

class AskRequest(BaseModel):
    """Kullanıcının soru isteği"""
    question: str = Field(
        ...,
        min_length=3,
        max_length=1000,
        description="Kullanıcının doküman hakkında sorduğu soru"
    )
    document_id: Optional[str] = Field(
        default=None,
        description="Belirli bir dokümana sorgu (None ise tümünde ara)"
    )
    top_k: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Getirilecek kaynak chunk sayısı"
    )


class Source(BaseModel):
    """Cevabın dayandığı kaynak chunk"""
    text: str
    filename: str
    page_number: int
    chunk_index: int
    similarity_score: float


class AskResponse(BaseModel):
    """LLM tarafından üretilen cevap ve kaynaklar"""
    answer: str
    sources: List[Source]
    processing_time_ms: int
    model_used: str


# ─── Sistem Modelleri ────────────────────────────────────────────

class HealthResponse(BaseModel):
    """Sistem sağlık durumu"""
    status: str
    openai_configured: bool
    vector_db: str
    total_documents: int
    total_chunks: int


class StatsResponse(BaseModel):
    """Sistem istatistikleri"""
    total_documents: int
    total_chunks: int
    embedding_model: str
    llm_model: str
    openai_configured: bool
    vector_db: str
