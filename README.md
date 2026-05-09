# DocuAsk — RAG-Based Intelligent Document Q&A System

> Bachelor's Capstone Project · Python · FastAPI · ChromaDB · Llama 3.3 · Sentence Transformers · OCR

![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?logo=fastapi&logoColor=white)
![ChromaDB](https://img.shields.io/badge/ChromaDB-0.5-orange)
![License](https://img.shields.io/badge/License-MIT-green)

---

## Overview

**DocuAsk** is a web application that enables users to ask natural language questions about their own PDF and TXT documents and receive accurate, source-cited answers powered by a **RAG (Retrieval-Augmented Generation)** pipeline.

### Problem Statement

Traditional keyword search cannot understand the *semantic content* of a document. Users studying long academic papers, lecture slides, or technical manuals must manually scan through pages to find relevant information — a slow and inefficient process.

### Solution

DocuAsk solves this with a two-stage AI pipeline:

1. **Retrieval** — The user's question is converted to a vector embedding and matched against pre-indexed document chunks using cosine similarity.
2. **Generation** — A large language model (LLM) generates a response *strictly* from the retrieved context, with page-level citations.

The system explicitly refuses to hallucinate: if the answer is not in the document, it says so.

---

## Features

- **Multi-format support** — PDF (text-based and scanned/OCR) and TXT files
- **Semantic search** — Vector similarity via ChromaDB, not keyword matching
- **Source citations** — Every answer references the exact page and chunk it came from
- **Free LLM** — Powered by Groq API (Llama 3.3 70B), no OpenAI cost required
- **Local embeddings** — `all-MiniLM-L6-v2` via Sentence Transformers, runs offline
- **OCR pipeline** — Scanned PDFs are processed via Tesseract + PyMuPDF
- **Clean REST API** — FastAPI with auto-generated Swagger docs at `/api/docs`
- **Modern Web UI** — Vanilla JS, no framework dependency, markdown-rendered responses

---

## Tech Stack

| Layer | Technology | Version | Role |
|---|---|---|---|
| **Backend** | FastAPI | 0.111 | Async REST API, automatic Swagger docs |
| **Server** | Uvicorn | 0.29 | ASGI server |
| **Frontend** | HTML / CSS / Vanilla JS | — | No framework dependency |
| **PDF Parsing** | pdfplumber + PyMuPDF | 0.11 / 1.27 | Text extraction (primary + fallback) |
| **OCR** | Tesseract + pytesseract | 5.5 | Scanned PDF text recognition |
| **Embeddings** | Sentence Transformers | — | `all-MiniLM-L6-v2`, runs locally |
| **LLM** | Groq API (Llama 3.3 70B) | — | Answer generation, free tier |
| **Vector DB** | ChromaDB | 0.5 | Persistent vector store, cosine similarity |
| **Schema** | Pydantic v2 | 2.7 | Type-safe request/response models |
| **Testing** | Pytest | 8.2 | Unit and integration tests |

---

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│  BROWSER  (HTML / CSS / Vanilla JS)                      │
│  File Upload · Question Form · Answer + Source Display   │
└─────────────────────┬────────────────────────────────────┘
                      │  HTTP REST
┌─────────────────────▼────────────────────────────────────┐
│  FASTAPI BACKEND                                          │
│                                                           │
│  POST /api/upload            POST /api/ask                │
│        │                           │                      │
│  ┌─────▼──────────┐      ┌─────────▼──────────┐          │
│  │ INDEXING       │      │ QUERY PIPELINE     │          │
│  │ ─────────────  │      │ ─────────────────  │          │
│  │ Extract text   │      │ Embed question     │          │
│  │ Chunk (1200c)  │      │ Similarity search  │          │
│  │ Embed chunks   │      │ Build context      │          │
│  │ Store vectors  │      │ Call LLM           │          │
│  └────────────────┘      └────────────┬───────┘          │
└─────────────────────────────────────  ┼ ─────────────────┘
                                        │
          ┌─────────────────────────────┼────────────┐
          │                            │            │
   ┌──────▼──────┐              ┌──────▼──────┐    │
   │  ChromaDB   │              │  Groq API   │    │
   │  (vectors + │              │  Llama 3.3  │    │
   │  metadata)  │              │  70B        │    │
   └─────────────┘              └─────────────┘    │
                                                   │
                               data/documents.json ┘
```

### RAG Pipeline — Step by Step

**Indexing** (triggered on file upload):
```
PDF / TXT File
    ↓
[1] Text Extraction    → pdfplumber (primary) → PyMuPDF (fallback) → Tesseract OCR (scanned)
    ↓
[2] Text Cleaning      → Remove headers/footers, fix hyphenation, normalize whitespace
    ↓
[3] Chunking           → 1200-char sliding window, 150-char overlap
    ↓
[4] Embedding          → all-MiniLM-L6-v2 → 384-dimensional vectors
    ↓
[5] Vector Store       → ChromaDB with metadata (page_number, chunk_index, filename)
```

**Querying** (triggered on question submit):
```
User Question
    ↓
[1] Question Embedding → Same model as indexing
    ↓
[2] Similarity Search  → Cosine similarity, top-k chunks retrieved
    ↓
[3] Context Building   → Deduplicated chunks formatted with page references
    ↓
[4] LLM Generation    → Llama 3.3 70B with strict "answer from context only" prompt
    ↓
[5] Response Format   → Answer text + source chunks + page numbers + similarity scores
```

### Project Structure

```
doc-qa-system/
├── app/
│   ├── main.py                  # FastAPI entry point, routers, middleware
│   ├── config.py                # Environment variable management (pydantic-settings)
│   ├── models/
│   │   └── schemas.py           # Pydantic request/response schemas
│   ├── services/
│   │   ├── document_loader.py   # PDF/TXT/OCR text extraction
│   │   ├── text_splitter.py     # Sliding-window chunking
│   │   ├── embedding_service.py # Sentence Transformers wrapper
│   │   ├── vector_store.py      # ChromaDB CRUD operations
│   │   ├── llm_service.py       # Groq/OpenAI/Demo LLM abstraction
│   │   └── rag_service.py       # End-to-end pipeline orchestration
│   ├── routers/
│   │   ├── upload.py            # POST /api/upload
│   │   ├── ask.py               # POST /api/ask
│   │   └── documents.py         # GET/DELETE /api/documents
│   └── utils/
│       └── helpers.py
├── static/
│   ├── css/style.css            # Custom CSS (no framework)
│   └── js/app.js                # Vanilla JS application class
├── templates/
│   └── index.html               # Jinja2 single-page template
├── tessdata/                    # Tesseract language data (tur + eng)
├── uploads/                     # Uploaded files (gitignored)
├── data/                        # Document metadata JSON
├── vector_store/                # ChromaDB persistent storage (gitignored)
├── tests/
│   └── test_main.py
├── .env.example
├── requirements.txt
└── run.py
```

---

## Getting Started

### Prerequisites

- Python 3.10+
- [Groq API key](https://console.groq.com) — free, no credit card required
- *(Optional)* [Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki) for scanned PDFs

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/YildizEmrullah/doc-qa-system.git
cd doc-qa-system

# 2. Create virtual environment
python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
copy .env.example .env   # Windows
# cp .env.example .env   # macOS/Linux
```

### Environment Variables (`.env`)

```env
# LLM — get a free key at https://console.groq.com
GROQ_API_KEY=gsk_...

# Optional: OpenAI (falls back to Groq if not set)
OPENAI_API_KEY=

# Embedding model (runs locally, no API key needed)
EMBEDDING_MODEL=text-embedding-3-small

# LLM model
LLM_MODEL=gpt-4o-mini

# Vector database
VECTOR_DB=chroma

# RAG parameters
CHUNK_SIZE=1200
CHUNK_OVERLAP=150
TOP_K_RESULTS=5
MAX_TOKENS=1500
```

### Run

```bash
uvicorn app.main:app --reload
```

Open **http://localhost:8000** in your browser.

Swagger API docs: **http://localhost:8000/api/docs**

---

## API Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Web UI |
| `GET` | `/api/health` | System health check |
| `POST` | `/api/upload` | Upload and index a PDF/TXT file |
| `POST` | `/api/ask` | Submit a question, receive answer + sources |
| `GET` | `/api/documents` | List all indexed documents |
| `GET` | `/api/documents/stats` | System statistics |
| `DELETE` | `/api/documents/{id}` | Delete a document and its vectors |
| `GET` | `/api/docs` | Swagger UI |

### POST `/api/ask` — Request

```json
{
  "question": "What is attention mechanism?",
  "document_id": "abc123def456",
  "top_k": 5
}
```

### POST `/api/ask` — Response

```json
{
  "answer": "The attention mechanism allows the model to weigh...",
  "sources": [
    {
      "text": "Attention mechanisms were introduced by Bahdanau et al...",
      "filename": "transformer_paper.pdf",
      "page_number": 4,
      "chunk_index": 12,
      "similarity_score": 0.91
    }
  ],
  "processing_time_ms": 1243,
  "model_used": "Groq/Llama-3.3-70b"
}
```

---

## OCR Support

DocuAsk supports scanned (image-based) PDFs through a three-tier extraction pipeline:

1. **pdfplumber** — word-coordinate-based extraction (fastest, best quality)
2. **PyMuPDF** — fallback for PDFs pdfplumber cannot parse
3. **Tesseract OCR** — for fully scanned pages with no embedded text

To enable OCR, install [Tesseract](https://github.com/UB-Mannheim/tesseract/wiki) and place `tur.traineddata` + `eng.traineddata` in the `tessdata/` directory.

---

## Running Tests

```bash
pytest tests/ -v
```

---

## Future Work

- [ ] Multi-turn conversation memory (chat history)
- [ ] Re-ranking with cross-encoder models
- [ ] Streaming LLM responses (Server-Sent Events)
- [ ] User session management (per-user document isolation)
- [ ] Fine-tuned domain-specific embedding model
- [ ] Docker containerization
- [ ] Kubernetes deployment with horizontal scaling

---

## Academic Context

This project was developed as a Bachelor's capstone thesis exploring the integration of large language models with document retrieval systems.

**Key research areas addressed:**
- Hallucination mitigation in LLMs via grounded generation
- Semantic search vs. keyword search in closed-domain QA
- Chunking strategy impact on retrieval quality
- Trade-offs between cloud LLMs (OpenAI) and open-source alternatives (Llama)

**Reference:** Lewis et al. (2020). *Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks*. NeurIPS 2020.

---

## License

MIT License — see [LICENSE](LICENSE) for details.

---

*Developed by [Emrullah Yıldız](https://github.com/YildizEmrullah) · Computer Engineering · Bachelor's Capstone Project*
