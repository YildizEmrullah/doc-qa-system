# DocuAsk — Büyük Dil Modeli Destekli Doküman Tabanlı Akıllı Soru-Cevap Sistemi

> Bitirme Projesi · Python · FastAPI · RAG · ChromaDB · OpenAI

---

## İçindekiler

1. [Proje Tanımı](#1-proje-tanımı)
2. [Kullanılan Teknolojiler](#2-kullanılan-teknolojiler)
3. [Sistem Mimarisi](#3-sistem-mimarisi)
4. [Kurulum Adımları](#4-kurulum-adımları)
5. [Ortam Değişkenleri (.env)](#5-ortam-değişkenleri-env)
6. [Uygulamayı Çalıştırma](#6-uygulamayı-çalıştırma)
7. [API Endpoint Listesi](#7-api-endpoint-listesi)
8. [RAG Akışı](#8-rag-akışı)
9. [Demo Kullanım Senaryosu](#9-demo-kullanım-senaryosu)
10. [Gelecek Geliştirmeler](#10-gelecek-geliştirmeler)
11. [Akademik Rapor İçin Teknik Açıklamalar](#11-akademik-rapor-için-teknik-açıklamalar)

---

## 1. Proje Tanımı

**DocuAsk**, kullanıcıların PDF ve TXT formatındaki belgeler üzerinden doğal dilde soru sorabildikleri, yapay zeka destekli bir web uygulamasıdır.

### Problem Tanımı

Geleneksel arama motorları anahtar kelime eşleşmesine dayanır ve belgenin **anlamsal içeriğini** kavrayamaz. Kullanıcılar, uzun akademik makaleler, ders notları veya teknik belgelerdeki bilgiye hızla erişmek istediklerinde ilgili bölümü manuel olarak bulmak zorunda kalırlar.

### Çözüm

**RAG (Retrieval-Augmented Generation)** mimarisi bu problemi iki aşamada çözer:
1. **Retrieval:** Kullanıcının sorusuna anlamsal olarak en yakın belge parçaları bulunur.
2. **Generation:** Büyük dil modeli (LLM) yalnızca bu parçalara dayalı, kaynak gösterir şekilde cevap üretir.

---

## 2. Kullanılan Teknolojiler

| Katman | Teknoloji | Versiyon | Açıklama |
|---|---|---|---|
| **Backend** | FastAPI | 0.111 | Async REST API, Swagger otomatik dokümantasyon |
| **Sunucu** | Uvicorn | 0.29 | ASGI sunucu |
| **Frontend** | HTML/CSS/JS | — | Vanilla JS, framework bağımlılığı yok |
| **PDF Okuma** | pdfplumber | 0.11 | Sayfa koordinatlı metin çıkarma |
| **Embedding** | OpenAI / sentence-transformers | — | Anlamsal vektör temsili |
| **LLM** | GPT-4o-mini | — | Cevap üretimi |
| **Vektör DB** | ChromaDB | 0.5 | Kalıcı vektör deposu |
| **Veri Şeması** | Pydantic v2 | 2.7 | Tip güvenli istek/yanıt modelleri |
| **Test** | Pytest | 8.2 | Birim ve entegrasyon testleri |

---

## 3. Sistem Mimarisi

```
┌──────────────────────────────────────────────────────────────┐
│  TARAYICI (HTML/CSS/JS)                                      │
│  Dosya Yükleme · Soru Formu · Cevap + Kaynak Gösterimi      │
└────────────────────┬─────────────────────────────────────────┘
                     │ HTTP REST
┌────────────────────▼─────────────────────────────────────────┐
│  FASTAPI BACKEND                                              │
│                                                              │
│  POST /api/upload          POST /api/ask                     │
│        │                         │                           │
│  ┌─────▼──────────┐    ┌─────────▼──────────┐               │
│  │ INDEXING       │    │ QUERY PIPELINE     │               │
│  │ ─────────────  │    │ ──────────────     │               │
│  │ Metin Çıkart   │    │ Soru → Embed       │               │
│  │ Chunk'la       │    │ Similarity Search  │               │
│  │ Embed Üret     │    │ Context Birleştir  │               │
│  │ ChromaDB'ye    │    │ LLM'e Gönder       │               │
│  └────────────────┘    └──────────────┬─────┘               │
└────────────────────────────────────── ┼─────────────────────┘
                                        │
         ┌──────────────────────────────┼────────────┐
         │                             │            │
  ┌──────▼──────┐             ┌────────▼──────┐    │
  │  ChromaDB   │             │  OpenAI API   │    │
  │  (Vektörler │             │  Embeddings + │    │
  │  + Metadata)│             │  GPT-4o-mini  │    │
  └─────────────┘             └───────────────┘    │
                                                   │
                              data/documents.json ─┘
```

### Klasör Yapısı

```
doc-qa-system/
├── app/
│   ├── main.py                  # FastAPI giriş noktası
│   ├── config.py                # Ortam değişkenleri
│   ├── models/
│   │   └── schemas.py           # Pydantic şemaları
│   ├── services/
│   │   ├── document_loader.py   # PDF/TXT okuma
│   │   ├── text_splitter.py     # Chunking
│   │   ├── embedding_service.py # Vektörleştirme
│   │   ├── vector_store.py      # ChromaDB işlemleri
│   │   ├── llm_service.py       # LLM cevap üretimi
│   │   └── rag_service.py       # Pipeline orkestratörü
│   ├── routers/
│   │   ├── upload.py
│   │   ├── ask.py
│   │   └── documents.py
│   └── utils/
│       └── helpers.py
├── static/
│   ├── css/style.css
│   └── js/app.js
├── templates/
│   └── index.html
├── uploads/                     # Yüklenen dosyalar
├── data/                        # documents.json
├── vector_store/                # ChromaDB kalıcı verisi
├── tests/
│   └── test_main.py
├── .env.example
├── requirements.txt
└── run.py
```

---

## 4. Kurulum Adımları

### Ön Gereksinimler
- Python 3.10 veya üzeri
- pip paket yöneticisi
- (Opsiyonel) OpenAI hesabı ve API anahtarı

### Adım 1 — Projeyi İndirin

```bash
cd C:\Users\Emrullah
# Proje zaten doc-qa-system/ klasöründe mevcut
cd doc-qa-system
```

### Adım 2 — Sanal Ortam Oluşturun

```bash
# Windows PowerShell
python -m venv venv
.\venv\Scripts\activate
```

### Adım 3 — Bağımlılıkları Yükleyin

```bash
pip install -r requirements.txt
```

> **Not:** Eğer sentence-transformers kullanmak istiyorsanız (OpenAI yoksa):
> ```bash
> pip install sentence-transformers torch
> ```

### Adım 4 — Ortam Değişkenlerini Ayarlayın

```bash
# .env.example dosyasını kopyala
copy .env.example .env
# Ardından .env dosyasını düzenleyin
```

---

## 5. Ortam Değişkenleri (.env)

```env
# OpenAI API anahtarı (yoksa Demo Modu aktif olur)
OPENAI_API_KEY=sk-...

# Embedding modeli
EMBEDDING_MODEL=text-embedding-3-small

# LLM modeli
LLM_MODEL=gpt-4o-mini

# Vektör veritabanı
VECTOR_DB=chroma

# RAG parametreleri
CHUNK_SIZE=800
CHUNK_OVERLAP=150
TOP_K_RESULTS=5
MAX_TOKENS=1500
```

### OpenAI API Anahtarı Nereye Koyulur?

1. [platform.openai.com](https://platform.openai.com) adresinden hesap açın
2. **API Keys** bölümünden yeni key oluşturun
3. `.env` dosyasındaki `OPENAI_API_KEY=` satırına yapıştırın

> **Demo Modu:** API anahtarı olmadan sistem çalışır, retrieval (benzer bölüm bulma) işlevi gösterilir ancak gerçek LLM cevabı üretilmez. Jüri gösterimleri için yeterlidir.

---

## 6. Uygulamayı Çalıştırma

### Geliştirme Sunucusu (Önerilen)

```bash
# Sanal ortamı aktifleştirmeyi unutmayın
.\venv\Scripts\activate

# Çalıştır
python run.py
```

Uygulama şu adreste açılır: **http://localhost:8000**

### Alternatif — Uvicorn Direkt

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Swagger API Dökümantasyonu

```
http://localhost:8000/api/docs
```

### Testleri Çalıştır

```bash
pytest tests/ -v
```

---

## 7. API Endpoint Listesi

| Metod | Endpoint | Açıklama |
|---|---|---|
| `GET` | `/` | Web arayüzü |
| `GET` | `/api/health` | Sistem sağlık kontrolü |
| `POST` | `/api/upload` | PDF/TXT yükle ve işle |
| `POST` | `/api/ask` | Soru sor, cevap al |
| `GET` | `/api/documents` | Yüklü dokümanları listele |
| `GET` | `/api/documents/stats` | Sistem istatistikleri |
| `DELETE` | `/api/documents/{id}` | Dokümanı sil |
| `GET` | `/api/docs` | Swagger UI |

### POST /api/ask — İstek Gövdesi

```json
{
  "question": "Makine öğrenmesi nedir?",
  "document_id": "abc123",
  "top_k": 5
}
```

### POST /api/ask — Yanıt

```json
{
  "answer": "Makine öğrenmesi, sistemlerin veriden otomatik öğrenmesini...",
  "sources": [
    {
      "text": "Makine öğrenmesi algoritmaları üç ana kategoriye...",
      "filename": "ders_notu.pdf",
      "page_number": 4,
      "chunk_index": 12,
      "similarity_score": 0.91
    }
  ],
  "processing_time_ms": 1243,
  "model_used": "gpt-4o-mini"
}
```

---

## 8. RAG Akışı

```
INDEXING (Dosya Yüklendiğinde)
──────────────────────────────────────────────────
PDF/TXT Dosyası
    ↓
[1] Metin Çıkarma     → pdfplumber sayfa sayfa metin alır
    ↓
[2] Temizleme         → Gereksiz boşluk, başlık/altbilgi temizlenir
    ↓
[3] Chunking          → 800 kar. parça, 150 kar. örtüşme (sliding window)
    ↓
[4] Embedding         → text-embedding-3-small → 1536 boyutlu vektör
    ↓
[5] ChromaDB Kaydı    → vektör + metadata (sayfa no, chunk index, dosya adı)

QUERYING (Soru Sorulduğunda)
──────────────────────────────────────────────────
Kullanıcı Sorusu
    ↓
[1] Soru Embedding    → Soruyu vektöre çevir
    ↓
[2] Similarity Search → ChromaDB'de cosine similarity ile top-5 chunk bul
    ↓
[3] Prompt Hazırla    → Bulunan chunk'lar + soru → prompt template
    ↓
[4] LLM Çağrısı       → GPT-4o-mini sadece context'ten cevap üretir
    ↓
[5] Yanıt Formatla    → Cevap + kaynak chunk'lar + sayfa no → JSON
    ↓
Kullanıcıya Göster
```

### LLM Sistem Prompt'u

```
Sen doküman tabanlı bir soru-cevap asistanısın.
Sadece verilen bağlam bilgilerine dayanarak cevap ver.
Eğer cevap bağlamda yoksa "Bu bilgi yüklenen dokümanda bulunamadı." de.
Asla tahmin yapma. Cevabı açık, kısa ve akademik dille ver.
```

---

## 9. Demo Kullanım Senaryosu

### Jüri Sunum Akışı (5 dakika)

1. **[0:00–0:30]** Tarayıcıda `http://localhost:8000` aç
   - İstatistik kartlarını göster (başlangıçta sıfır)
   - "RAG mimarisi bu panelde canlı çalışıyor" de

2. **[0:30–1:30]** Bir PDF yükle (ders notu, makale vb.)
   - Sürükle-bırak ile yükle
   - İlerleme adımlarını göster: "Metin çıkarılıyor → Parçalanıyor → Embedding"
   - İstatistikler güncellenir: chunk sayısı artar

3. **[1:30–3:30]** Üç farklı soru sor

   ```
   Soru 1: "Bu doküman ne hakkında?"
   → Genel özet cevabı + 5 kaynak bölümü

   Soru 2: "[Belgede geçen spesifik konu] nedir?"
   → Kesin, sayfa numaralı kaynak cevabı

   Soru 3: "Bu belgede olmayan bir şey" (halüsinasyon testi)
   → "Bu bilgi yüklenen dokümanda bulunamadı." — Sistem doğruyu söylüyor!
   ```

4. **[3:30–4:30]** Kaynak panelini incele
   - "Sayfa 4'ten geldi, %91 eşleşme" göster
   - "Bu geleneksel aramadan farklı: anlamsal benzerlik kullanıyoruz" açıkla

5. **[4:30–5:00]** Mimari şemayı göster, sorular

---

## 10. Gelecek Geliştirmeler

### Kısa Vadeli (v1.1)
- [ ] Konuşma geçmişi (önceki soruları hatırla)
- [ ] Doküman özetleme endpoint'i (`POST /api/summarize`)
- [ ] Cevap güven skoru gösterimi
- [ ] Karanlık mod

### Orta Vadeli (v1.2)
- [ ] Ollama entegrasyonu (tamamen offline/ücretsiz LLM)
- [ ] Re-ranking (cross-encoder ile sonuçları yeniden sırala)
- [ ] Kullanıcı oturum yönetimi (her kullanıcı kendi dokümanları)
- [ ] SQLite ile soru geçmişi kayıt

### İleri Düzey (v2.0)
- [ ] Taramalı PDF OCR desteği (pytesseract)
- [ ] Çok dilli embedding desteği
- [ ] Kubernetes ile ölçeklenebilir dağıtım
- [ ] LLM Fine-tuning (domain-specific model)

---

## 11. Akademik Rapor İçin Teknik Açıklamalar

### Projenin Amacı

Bu çalışma, büyük dil modellerinin (BDM) bilgi erişim sistemleriyle entegrasyonunu araştırmakta; kullanıcıların kendi yükledikleri belgeler üzerinden doğal dilde soru sorabildiği, kaynak gösterir şekilde cevap üretilen bir platform geliştirmeyi amaçlamaktadır.

### RAG Mimarisi Açıklaması

Retrieval-Augmented Generation (RAG), Lewis et al. (2020) tarafından önerilen bir mimaridir. İki ana bileşenden oluşur: **retriever** (ilgili bilgiyi bulan) ve **generator** (cevap üreten). Bu yapı, büyük dil modellerinin iki temel kısıtlamasını aşar: (1) eğitim kesme tarihi sonrasındaki bilgiye erişim yokluğu, (2) kapalı alan sorularında halüsinasyon üretme eğilimi.

### Vektör Veritabanı Açıklaması

ChromaDB, metin parçalarının anlamsal vektör temsillerini (embedding) saklayan ve kosinüs benzerliğine dayalı hızlı benzerlik araması yapan gömülü bir vektör veritabanıdır. Her vektörle birlikte metadata (dosya adı, sayfa numarası, chunk sırası) saklanarak kaynak gösterimi mümkün kılınmıştır.

### Embedding Açıklaması

Metin embedding'i, doğal dil metinlerini yüksek boyutlu vektör uzayında noktalara dönüştürme işlemidir. Anlamca yakın metinler bu uzayda birbirine yakın konumlanır. Bu çalışmada OpenAI'ın `text-embedding-3-small` modeli kullanılmış; 1536 boyutlu vektörler üretilmiştir.

### Chunking Stratejisi

Belgeler 800 karakter boyutunda, 150 karakter örtüşmeli (sliding window) parçalara ayrılmıştır. Örtüşme, parça sınırlarında kopan bağlamsal bilginin bir sonraki parçaya taşınmasını sağlar. Parça sınırları mümkün olduğunca cümle sonlarına (nokta, satır sonu) denk getirilmiştir.

### LLM Cevap Üretim Süreci

Retrieval aşamasında bulunan top-k chunk'lar, önceden tasarlanmış bir prompt template'e bağlam olarak eklenir. GPT-4o-mini, düşük temperature (0.3) değeriyle çağrılarak tutarlı ve olgusal cevaplar üretmesi sağlanır. "Sadece bağlamdan cevap ver" yönergesi, hallüsinasyon riskini minimize eder.

### Test ve Değerlendirme

Sistem, birim testleri (metin temizleme, chunking doğruluğu) ve entegrasyon testleri (uçtan uca yükleme-sorgulama-silme pipeline'ı) ile doğrulanmıştır. Manuel değerlendirmede belgede yer alan soruların büyük çoğunluğuna kaynaklı cevap üretilmiş; belgede bulunmayan sorularda sistem doğru şekilde "bulunamadı" yanıtı vermiştir.

### Sonuç ve Gelecek Çalışmalar

Bu çalışmada uygulanan RAG mimarisi, büyük dil modellerinin kapalı alan (closed-domain) sorularındaki güvenilirliğini önemli ölçüde artırmaktadır. Gelecek çalışmalarda re-ranking mekanizması, çok-dönüşümlü konuşma yönetimi ve yerel açık kaynak LLM entegrasyonu (Ollama/Llama-3) planlanmaktadır.

---

*Bu proje [Öğrenci Adı] tarafından [Üniversite Adı] Bilgisayar Mühendisliği Bölümü bitirme projesi kapsamında geliştirilmiştir.*
