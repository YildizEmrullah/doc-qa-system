"""
Genel yardımcı fonksiyonlar.
Dosya doğrulama, boyut biçimleme ve metin yardımcıları.
"""

from pathlib import Path
from typing import Set


def format_file_size(size_bytes: int) -> str:
    """Bayt cinsinden dosya boyutunu okunabilir formata çevirir"""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 ** 2:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 ** 3:
        return f"{size_bytes / 1024 ** 2:.1f} MB"
    return f"{size_bytes / 1024 ** 3:.1f} GB"


def is_allowed_extension(filename: str, allowed: Set[str]) -> bool:
    """Dosya uzantısının izin verilenler arasında olup olmadığını kontrol eder"""
    return Path(filename).suffix.lower() in allowed


def truncate_text(text: str, max_length: int = 200, suffix: str = "...") -> str:
    """Metni belirtilen uzunlukta keser ve sonuna suffix ekler"""
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


def highlight_query_terms(text: str, query: str) -> str:
    """Metin içindeki sorgu terimlerini <mark> etiketi ile işaretler"""
    import re
    terms = [t for t in query.split() if len(t) > 2]
    for term in terms:
        pattern = re.compile(re.escape(term), re.IGNORECASE)
        text = pattern.sub(f"<mark>{term}</mark>", text)
    return text
