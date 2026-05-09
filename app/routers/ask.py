"""
Soru-cevap endpoint'leri.
POST /api/ask — Kullanıcı sorusunu alır, RAG pipeline ile yanıtlar.
"""

import logging

from fastapi import APIRouter, HTTPException

from app.models.schemas import AskRequest, AskResponse
from app.services.rag_service import answer_question
from app.services.vector_store import get_vector_store

router = APIRouter(prefix="/ask", tags=["Soru-Cevap"])
logger = logging.getLogger(__name__)


@router.post("", response_model=AskResponse, summary="Doküman hakkında soru sor")
async def ask_question(request: AskRequest):
    """
    Yüklü dokümanlara dayalı soru yanıtlama.

    **Pipeline:**
    1. Soruyu embedding'e çevir
    2. Vektör veritabanında benzerlik araması yap (top-k)
    3. Bulunan chunk'ları LLM'e bağlam olarak ver
    4. Cevap + kaynak chunk'ları döndür

    **İstek gövdesi:**
    - `question`: Kullanıcının sorusu (3–1000 karakter)
    - `document_id`: Belirli bir dokümana filtrele (opsiyonel)
    - `top_k`: Kaç kaynak getirilecek (1–10, varsayılan 5)
    """
    # Sistemde doküman var mı kontrol et
    vec_store    = get_vector_store()
    total_chunks = vec_store.get_total_chunks()

    if total_chunks == 0:
        raise HTTPException(
            status_code=400,
            detail=(
                "Henüz hiçbir doküman yüklenmedi. "
                "Önce sol panelden bir PDF veya TXT dosyası yükleyin."
            ),
        )

    question = request.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Soru boş bırakılamaz.")

    try:
        result = answer_question(
            question=question,
            document_id=request.document_id,
            top_k=request.top_k,
        )
        return result

    except Exception as exc:
        logger.exception(f"Soru yanıtlama hatası: {exc}")
        raise HTTPException(
            status_code=500,
            detail=f"Soru yanıtlanırken bir hata oluştu: {exc}",
        )
