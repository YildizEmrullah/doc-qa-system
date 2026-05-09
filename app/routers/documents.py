"""
Doküman yönetim endpoint'leri.
GET  /api/documents        — Doküman listesi
DELETE /api/documents/{id} — Doküman sil
GET  /api/documents/stats  — Sistem istatistikleri
"""

import logging

from fastapi import APIRouter, HTTPException

from app.models.schemas import DeleteResponse, DocumentListResponse, StatsResponse
from app.services.embedding_service import get_embedding_service
from app.services.rag_service import delete_document, list_documents
from app.services.vector_store import get_vector_store
from app.config import settings

router = APIRouter(prefix="/documents", tags=["Doküman Yönetimi"])
logger = logging.getLogger(__name__)


@router.get("", response_model=DocumentListResponse, summary="Yüklü dokümanları listele")
async def get_documents():
    """Yüklenmiş tüm dokümanları metadata bilgileriyle döndürür."""
    docs = list_documents()
    return DocumentListResponse(documents=docs, total=len(docs))


@router.delete(
    "/{document_id}",
    response_model=DeleteResponse,
    summary="Dokümanı sil",
)
async def remove_document(document_id: str):
    """
    Belirtilen dokümanı ve ona ait tüm vektör kayıtlarını siler.
    Yüklenen dosyayı da diskten kaldırır.
    """
    success, message = delete_document(document_id)

    if not success:
        raise HTTPException(status_code=404, detail=message)

    return DeleteResponse(success=True, message=message)


@router.get("/stats", response_model=StatsResponse, summary="Sistem istatistikleri")
async def get_stats():
    """
    Anlık sistem durumunu döndürür:
    - Toplam doküman ve chunk sayısı
    - Kullanılan embedding ve LLM modeli
    - OpenAI yapılandırma durumu
    """
    vec_store = get_vector_store()
    emb       = get_embedding_service()
    docs      = list_documents()

    if settings.GROQ_API_KEY:
        llm_model = "Groq/Llama-3.3-70b"
    elif settings.OPENAI_API_KEY:
        llm_model = settings.LLM_MODEL
    else:
        llm_model = "demo-mode"

    return StatsResponse(
        total_documents=len(docs),
        total_chunks=vec_store.get_total_chunks(),
        embedding_model=emb.get_model_name(),
        llm_model=llm_model,
        openai_configured=bool(settings.OPENAI_API_KEY or settings.GROQ_API_KEY),
        vector_db=settings.VECTOR_DB,
    )
