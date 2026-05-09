"""
Doküman yükleme endpoint'leri.
POST /api/upload — PDF veya TXT dosyasını alır, RAG pipeline'ını çalıştırır.
"""

import logging
import re
import time
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.config import settings
from app.models.schemas import UploadResponse
from app.services.rag_service import process_document

router = APIRouter(prefix="/upload", tags=["Doküman Yükleme"])
logger = logging.getLogger(__name__)


@router.post("", response_model=UploadResponse, summary="Doküman yükle ve işle")
async def upload_document(file: UploadFile = File(...)):
    """
    PDF veya TXT doküman yükler ve RAG sistemine entegre eder.

    **Adımlar:**
    1. Dosya türü ve boyut doğrulama
    2. Diske kaydetme
    3. Metin çıkarma (PDF/TXT)
    4. Chunk'lara bölme
    5. Embedding oluşturma
    6. Vektör veritabanına kaydetme
    """
    # ─── Doğrulama ────────────────────────────────────────────────
    file_ext = Path(file.filename).suffix.lower()

    if file_ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Desteklenmeyen dosya türü: '{file_ext}'. "
                f"Kabul edilen türler: "
                f"{', '.join(sorted(settings.ALLOWED_EXTENSIONS))}"
            ),
        )

    content = await file.read()

    if len(content) == 0:
        raise HTTPException(
            status_code=400,
            detail="Dosya boş. Lütfen içerik bulunan bir dosya yükleyin.",
        )

    max_bytes = settings.MAX_FILE_SIZE_MB * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"Dosya çok büyük. Maksimum izin verilen boyut: {settings.MAX_FILE_SIZE_MB} MB",
        )

    # ─── Diske kaydet ─────────────────────────────────────────────
    safe_name = _safe_filename(file.filename)
    file_path = settings.UPLOAD_DIR / safe_name

    with open(file_path, "wb") as f:
        f.write(content)

    logger.info(f"Dosya kaydedildi: {file_path} ({len(content):,} bayt)")

    # ─── Pipeline'ı çalıştır ──────────────────────────────────────
    try:
        result = process_document(file_path, file.filename)
        return result

    except ValueError as exc:
        # Beklenen iş kuralı hataları (boş PDF, taranan PDF vb.)
        _cleanup(file_path)
        raise HTTPException(status_code=422, detail=str(exc))

    except Exception as exc:
        _cleanup(file_path)
        logger.exception(f"Doküman işleme hatası: {exc}")
        raise HTTPException(
            status_code=500,
            detail=f"Doküman işlenirken beklenmedik bir hata oluştu: {exc}",
        )


# ─── Yardımcı Fonksiyonlar ────────────────────────────────────────

def _safe_filename(filename: str) -> str:
    """
    Güvenli dosya adı üretir.
    Path traversal ve özel karakter saldırılarını engeller.
    """
    basename = Path(filename).name
    safe     = re.sub(r"[^\w\-_.]", "_", basename)
    ts       = int(time.time())
    stem     = Path(safe).stem[:50]   # Uzun isimleri kısalt
    suffix   = Path(safe).suffix
    return f"{ts}_{stem}{suffix}"


def _cleanup(path: Path) -> None:
    """Hata durumunda yarım kalan dosyayı siler"""
    try:
        if path.exists():
            path.unlink()
    except Exception:
        pass
