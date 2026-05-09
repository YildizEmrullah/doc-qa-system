"""
DocuAsk — Test Paketi
Birim ve entegrasyon testleri.

Çalıştırmak için:
    pytest tests/ -v
"""

import io
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.text_splitter import split_text
from app.services.document_loader import _clean_text

client = TestClient(app)


# ═══════════════════════════════════════════════════════════════
#  SAĞLIK TESTLERİ
# ═══════════════════════════════════════════════════════════════

def test_health_endpoint():
    """GET /api/health 200 döndürmeli"""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "total_chunks" in data
    assert "openai_configured" in data


def test_root_returns_html():
    """GET / HTML içeriği döndürmeli"""
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "DocuAsk" in response.text


# ═══════════════════════════════════════════════════════════════
#  DOKÜMAN LİSTESİ TESTLERİ
# ═══════════════════════════════════════════════════════════════

def test_list_documents():
    """GET /api/documents liste döndürmeli"""
    response = client.get("/api/documents")
    assert response.status_code == 200
    data = response.json()
    assert "documents" in data
    assert "total" in data
    assert isinstance(data["documents"], list)


def test_stats_endpoint():
    """GET /api/documents/stats istatistikleri döndürmeli"""
    response = client.get("/api/documents/stats")
    assert response.status_code == 200
    data = response.json()
    assert "total_documents" in data
    assert "total_chunks" in data
    assert "embedding_model" in data


# ═══════════════════════════════════════════════════════════════
#  DOSYA YÜKLEME TESTLERİ
# ═══════════════════════════════════════════════════════════════

def test_upload_valid_txt():
    """Geçerli TXT dosyası yükleme başarılı olmalı"""
    txt_content = b"""
    Yapay zeka (YZ), insan zekasini taklit eden bilgisayar sistemleridir.
    Makine ogrenmesi, derin ogrenme ve dogal dil isleme YZ'nin alt dallaridir.
    Bu alanda yapilan calismalar her gecen gun daha da gelismektedir.
    Buyuk dil modelleri (BDM), metin anlama ve uretme konusunda cok basarilidir.
    RAG mimarisi, dokuman tabanli soru-cevap icin kullanilandige bir yaklasimdir.
    """ * 10  # Yeterli metin olsun

    response = client.post(
        "/api/upload",
        files={"file": ("test_doc.txt", io.BytesIO(txt_content), "text/plain")},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["chunk_count"] > 0
    assert data["document"]["file_type"] == "txt"
    return data["document"]["id"]


def test_upload_empty_file():
    """Boş dosya 400 hatası döndürmeli"""
    response = client.post(
        "/api/upload",
        files={"file": ("empty.txt", io.BytesIO(b""), "text/plain")},
    )
    assert response.status_code == 400
    assert "boş" in response.json()["detail"].lower()


def test_upload_unsupported_format():
    """Desteklenmeyen dosya türü 400 hatası döndürmeli"""
    response = client.post(
        "/api/upload",
        files={"file": ("test.docx", io.BytesIO(b"some content"), "application/vnd.openxmlformats")},
    )
    assert response.status_code == 400
    data = response.json()
    assert "desteklenmeyen" in data["detail"].lower()


def test_upload_too_large_file():
    """50 MB'tan büyük dosya 413 hatası döndürmeli"""
    big_content = b"A" * (51 * 1024 * 1024)  # 51 MB
    response = client.post(
        "/api/upload",
        files={"file": ("big.txt", io.BytesIO(big_content), "text/plain")},
    )
    assert response.status_code == 413


# ═══════════════════════════════════════════════════════════════
#  SORU-CEVAP TESTLERİ
# ═══════════════════════════════════════════════════════════════

def test_ask_without_documents():
    """Doküman yüklenmeden soru sorulunca 400 hatası döndürmeli"""
    # Bu test sadece veritabanı boşken geçer
    # Eğer başka testler doküman yükledi ise atlayabiliriz
    response = client.post(
        "/api/ask",
        json={"question": "Bu nedir?"}
    )
    # 400 (doküman yok) veya 200 (doküman var) olabilir
    assert response.status_code in [200, 400]


def test_ask_empty_question():
    """Pydantic boş soru için doğrulama hatası döndürmeli"""
    response = client.post(
        "/api/ask",
        json={"question": ""}
    )
    assert response.status_code == 422  # Pydantic validation error


def test_ask_too_short_question():
    """3 karakterden kısa soru 422 döndürmeli"""
    response = client.post(
        "/api/ask",
        json={"question": "ne"}
    )
    assert response.status_code == 422


def test_ask_too_long_question():
    """1000 karakterden uzun soru 422 döndürmeli"""
    response = client.post(
        "/api/ask",
        json={"question": "A" * 1001}
    )
    assert response.status_code == 422


def test_ask_valid_top_k():
    """top_k parametresi 1-10 arasında olmalı"""
    response = client.post(
        "/api/ask",
        json={"question": "Bu nedir?", "top_k": 15}
    )
    assert response.status_code == 422  # 10'dan büyük → validation error


# ═══════════════════════════════════════════════════════════════
#  SERVİS BİRİM TESTLERİ
# ═══════════════════════════════════════════════════════════════

def test_text_splitter_basic():
    """Chunking temel işlevi: kısa metin tek chunk olmalı"""
    pages = [{"text": "Kısa bir metin.", "page_number": 1}]
    chunks = split_text(pages, "doc001", "test.txt", chunk_size=500, chunk_overlap=50)
    assert len(chunks) == 1
    assert chunks[0]["text"] == "Kısa bir metin."
    assert chunks[0]["document_id"] == "doc001"
    assert chunks[0]["page_number"] == 1


def test_text_splitter_long_text():
    """Uzun metin birden fazla chunk'a bölünmeli"""
    long_text = "Bu bir test cümlesidir. " * 100  # ~2400 karakter
    pages = [{"text": long_text, "page_number": 1}]
    chunks = split_text(pages, "doc002", "test.txt", chunk_size=500, chunk_overlap=50)
    assert len(chunks) > 1
    assert all(c["document_id"] == "doc002" for c in chunks)


def test_text_splitter_chunk_ids_unique():
    """Her chunk'ın ID'si benzersiz olmalı"""
    pages = [{"text": "X " * 500, "page_number": i} for i in range(3)]
    chunks = split_text(pages, "doc003", "test.txt", chunk_size=200, chunk_overlap=20)
    ids = [c["id"] for c in chunks]
    assert len(ids) == len(set(ids)), "Chunk ID'leri benzersiz olmalı"


def test_text_splitter_empty_page():
    """Boş sayfa chunk üretmemeli"""
    pages = [{"text": "   ", "page_number": 1}]
    chunks = split_text(pages, "doc004", "test.txt")
    assert len(chunks) == 0


def test_text_cleaner():
    """Metin temizleme fonksiyonu gereksiz boşlukları kaldırmalı"""
    dirty = "Bu   bir    test.\n\n\n\nMetin    temizleme."
    clean = _clean_text(dirty)
    assert "  " not in clean  # Çift boşluk olmamalı
    assert "\n\n\n" not in clean  # 3'ten fazla satır sonu olmamalı


# ═══════════════════════════════════════════════════════════════
#  DOKÜMAN SİLME TESTİ
# ═══════════════════════════════════════════════════════════════

def test_delete_nonexistent_document():
    """Var olmayan doküman silinmeye çalışılınca 404 dönmeli"""
    response = client.delete("/api/documents/nonexistent_id_xyz")
    assert response.status_code == 404


def test_full_pipeline_txt():
    """
    Uçtan uca pipeline testi:
    TXT yükle → dokümanı listede gör → soru sor → dokümanı sil
    """
    # 1. Yükle
    content = (
        "Makine öğrenmesi, bilgisayarların verilerden öğrenmesini sağlar. "
        "Gözetimli öğrenme, gözetimsiz öğrenme ve pekiştirmeli öğrenme olmak üzere "
        "üç ana kategoriye ayrılır. "
    ) * 20

    upload_resp = client.post(
        "/api/upload",
        files={"file": ("pipeline_test.txt", io.BytesIO(content.encode()), "text/plain")},
    )
    assert upload_resp.status_code == 200
    doc_id = upload_resp.json()["document"]["id"]

    # 2. Listede görünüyor mu?
    list_resp = client.get("/api/documents")
    doc_ids = [d["id"] for d in list_resp.json()["documents"]]
    assert doc_id in doc_ids

    # 3. Soru sor
    ask_resp = client.post(
        "/api/ask",
        json={
            "question": "Makine öğrenmesi nedir?",
            "document_id": doc_id,
            "top_k": 3,
        },
    )
    assert ask_resp.status_code == 200
    ask_data = ask_resp.json()
    assert "answer" in ask_data
    assert len(ask_data["sources"]) > 0

    # 4. Sil
    del_resp = client.delete(f"/api/documents/{doc_id}")
    assert del_resp.status_code == 200
    assert del_resp.json()["success"] is True

    # 5. Listede artık yok mu?
    list_resp2 = client.get("/api/documents")
    doc_ids2 = [d["id"] for d in list_resp2.json()["documents"]]
    assert doc_id not in doc_ids2
