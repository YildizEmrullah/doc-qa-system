"""
Doküman yükleme servisi.
PDF ve TXT dosyalarından temiz, birleşik metin çıkarır.
"""

import logging
import re
from pathlib import Path
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


def load_document(file_path: Path) -> List[Dict[str, Any]]:
    ext = file_path.suffix.lower()
    if ext == ".pdf":
        return _load_pdf(file_path)
    elif ext == ".txt":
        return _load_txt(file_path)
    else:
        raise ValueError(f"Desteklenmeyen dosya türü: '{ext}'")


def _load_pdf(file_path: Path) -> List[Dict[str, Any]]:
    """
    PDF'ten metin çıkarır.
    1. pdfplumber (kelime bazlı, en temiz sonuç)
    2. PyMuPDF  (pdfplumber başarısız veya boş kalırsa)
    3. Her ikisi de boş kalırsa → OCR hatası mesajı
    """
    pages = _load_pdf_pdfplumber(file_path)

    if not pages:
        logger.info("pdfplumber metin bulamadı, PyMuPDF deneniyor...")
        pages = _load_pdf_pymupdf(file_path)

    if not pages:
        logger.info("pdfplumber ve PyMuPDF başarısız, OCR deneniyor...")
        pages = _load_pdf_ocr(file_path)

    if not pages:
        raise ValueError(
            "PDF'ten metin çıkarılamadı. "
            "Dosya tamamen taramalı (görüntü tabanlı) veya şifrelenmiş olabilir. "
            "OCR için Tesseract kurulumu gereklidir."
        )

    logger.info(f"PDF: {len(pages)} sayfa yüklendi — {file_path.name}")
    return pages


def _load_pdf_pdfplumber(file_path: Path) -> List[Dict[str, Any]]:
    """pdfplumber ile kelime-bazlı metin çıkarımı."""
    import pdfplumber

    pages = []
    try:
        with pdfplumber.open(file_path) as pdf:
            if not pdf.pages:
                return []
            for page_num, page in enumerate(pdf.pages, start=1):
                words = page.extract_words()
                if words:
                    text = _words_to_text(words)
                else:
                    text = page.extract_text() or ""
                text = _clean_text(text)
                if text and len(text) > 20:
                    pages.append({"text": text, "page_number": page_num})
    except Exception as e:
        logger.warning(f"pdfplumber hatası: {e}")
    return pages


def _load_pdf_pymupdf(file_path: Path) -> List[Dict[str, Any]]:
    """PyMuPDF (fitz) ile metin çıkarımı — pdfplumber'a alternatif."""
    try:
        import fitz  # pymupdf
    except ImportError:
        logger.warning("PyMuPDF kurulu değil, pip install pymupdf")
        return []

    pages = []
    try:
        doc = fitz.open(str(file_path))
        for page_num, page in enumerate(doc, start=1):
            text = page.get_text("text")
            text = _clean_text(text)
            if text and len(text) > 20:
                pages.append({"text": text, "page_number": page_num})
        doc.close()
    except Exception as e:
        logger.warning(f"PyMuPDF hatası: {e}")
    return pages


def _words_to_text(words: list) -> str:
    """
    Kelime listesini satır satır birleştirir.
    Aynı satırdaki kelimeler boşlukla, farklı satırlar newline ile ayrılır.
    """
    if not words:
        return ""

    lines = []
    current_line = []
    current_top = None
    tolerance = 3  # piksel toleransı

    for w in words:
        top = round(w["top"])
        if current_top is None or abs(top - current_top) <= tolerance:
            current_line.append(w["text"])
            current_top = top
        else:
            if current_line:
                lines.append(" ".join(current_line))
            current_line = [w["text"]]
            current_top = top

    if current_line:
        lines.append(" ".join(current_line))

    return "\n".join(lines)


def _load_pdf_ocr(file_path: Path) -> List[Dict[str, Any]]:
    """
    Taramalı PDF'ler için OCR.
    Gereksinimler: pip install pytesseract pdf2image + Tesseract-OCR
    """
    import os

    try:
        import pytesseract
    except ImportError:
        logger.warning("OCR kütüphanesi eksik: pip install pytesseract")
        return []

    # Tesseract executable
    for candidate in [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    ]:
        if os.path.exists(candidate):
            pytesseract.pytesseract.tesseract_cmd = candidate
            break

    # Proje içindeki tessdata klasörünü göster (tur + eng dil paketleri burada)
    project_tessdata = Path(__file__).resolve().parents[2] / "tessdata"
    if project_tessdata.exists():
        os.environ["TESSDATA_PREFIX"] = str(project_tessdata)
        logger.info(f"TESSDATA_PREFIX: {project_tessdata}")

    # Hangi diller mevcut?
    try:
        available = pytesseract.get_languages()
    except Exception:
        available = ["eng"]
    lang = "tur+eng" if "tur" in available else "eng"
    logger.info(f"OCR dili: {lang}")

    # PyMuPDF ile PDF sayfalarını görüntüye çevir (poppler gerekmez)
    pages = []
    try:
        import fitz
        from PIL import Image
        import io

        doc = fitz.open(str(file_path))
        logger.info(f"OCR: {len(doc)} sayfa işlenecek")

        for page_num, page in enumerate(doc, start=1):
            # 200 DPI eşdeğeri: scale=200/72 ≈ 2.78
            mat = fitz.Matrix(2.78, 2.78)
            pix = page.get_pixmap(matrix=mat, colorspace=fitz.csRGB)
            img_data = pix.tobytes("png")
            img = Image.open(io.BytesIO(img_data))

            text = pytesseract.image_to_string(img, lang=lang)
            text = _clean_text(text)
            if text and len(text) > 20:
                pages.append({"text": text, "page_number": page_num})
                logger.info(f"  OCR Sayfa {page_num}: {len(text)} karakter")

        doc.close()
    except Exception as e:
        logger.warning(f"OCR hatası: {e}")

    return pages


def _load_txt(file_path: Path) -> List[Dict[str, Any]]:
    content = None
    for enc in ["utf-8", "utf-8-sig", "latin-1", "cp1254"]:
        try:
            content = file_path.read_text(encoding=enc)
            break
        except UnicodeDecodeError:
            continue

    if not content or not content.strip():
        raise ValueError("TXT dosyası boş veya okunamadı.")

    return [{"text": _clean_text(content), "page_number": 1}]


def _clean_text(text: str) -> str:
    """Metni temizler: sayfa numaraları, kırık satırlar, gereksiz boşluklar."""

    # Satır sonu tire birleştirmesi (Türkçe: "kulla-\nnıcı" → "kullanıcı")
    text = re.sub(r'-\n(\w)', r'\1', text)

    # Tek başına duran sayıları kaldır (sayfa numaraları)
    text = re.sub(r'(?m)^\s*\d{1,3}\s*$', '', text)

    # Çok kısa satırları (sadece 1-2 karakter) kaldır
    text = re.sub(r'(?m)^\s*.{1,2}\s*$', '', text)

    # Birden fazla boşluğu teke indir
    text = re.sub(r'[ \t]{2,}', ' ', text)

    # 3+ satır sonunu 2'ye indir
    text = re.sub(r'\n{3,}', '\n\n', text)

    return text.strip()


def get_page_count(file_path: Path) -> int:
    if file_path.suffix.lower() == ".pdf":
        import pdfplumber
        with pdfplumber.open(file_path) as pdf:
            return len(pdf.pages)
    return 1
