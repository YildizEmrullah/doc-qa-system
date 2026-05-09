"""
Metin bölümleme (chunking) servisi.
Doküman metnini embedding için uygun boyutlu parçalara böler.
Sliding window yöntemiyle örtüşen chunk'lar oluşturur.
"""

import logging
from typing import List, Dict, Any

from app.config import settings

logger = logging.getLogger(__name__)


def split_text(
    pages: List[Dict[str, Any]],
    document_id: str,
    filename: str,
    chunk_size: int = None,
    chunk_overlap: int = None,
) -> List[Dict[str, Any]]:
    """
    Doküman sayfalarını örtüşen chunk'lara böler.

    Args:
        pages:        load_document() çıktısı - {"text", "page_number"} listesi
        document_id:  Benzersiz doküman kimliği
        filename:     Orijinal dosya adı (metadata için)
        chunk_size:   Chunk başına karakter sayısı (varsayılan: config)
        chunk_overlap: Chunk'lar arası örtüşme (varsayılan: config)

    Returns:
        Chunk listesi - her eleman bir dict
    """
    chunk_size = chunk_size or settings.CHUNK_SIZE
    chunk_overlap = chunk_overlap or settings.CHUNK_OVERLAP

    all_chunks: List[Dict[str, Any]] = []
    chunk_index = 0

    for page in pages:
        page_text = page["text"]
        page_number = page["page_number"]

        # Bu sayfadaki metni chunk'lara böl
        raw_chunks = _sliding_window_split(page_text, chunk_size, chunk_overlap)

        for chunk_text in raw_chunks:
            if not chunk_text.strip():
                continue

            all_chunks.append({
                "id": f"{document_id}_chunk_{chunk_index:04d}",
                "document_id": document_id,
                "filename": filename,
                "page_number": page_number,
                "chunk_index": chunk_index,
                "text": chunk_text.strip(),
            })
            chunk_index += 1

    logger.info(
        f"Chunking tamamlandı: {len(pages)} sayfa → {len(all_chunks)} chunk "
        f"(boyut={chunk_size}, örtüşme={chunk_overlap})"
    )
    return all_chunks


def _sliding_window_split(
    text: str,
    chunk_size: int,
    chunk_overlap: int,
) -> List[str]:
    """
    Sliding window yöntemiyle metni chunk'lara böler.
    Mümkünse cümle sınırlarında böler (nokta / satır sonu).
    """
    if len(text) <= chunk_size:
        return [text]

    chunks: List[str] = []
    start = 0

    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]

        # Cümle sınırında kesmeye çalış (son %. veya \n)
        if end < len(text):
            best_break = _find_sentence_boundary(chunk)
            if best_break > chunk_size * 0.5:
                chunk = text[start : start + best_break + 1]

        chunks.append(chunk)
        step = len(chunk) - chunk_overlap
        start += max(step, 1)  # Sonsuz döngüyü önle

    return chunks


def _find_sentence_boundary(text: str) -> int:
    """
    Metin içinde en iyi kesme noktasını bulur.
    Önce nokta+boşluk, ardından newline arar.
    """
    for sep in (". ", "! ", "? ", "\n", "،", "。"):
        pos = text.rfind(sep)
        if pos > 0:
            return pos + len(sep) - 1
    return len(text)
