"""
DocuAsk — FastAPI uygulama giriş noktası.
Router'ları, statik dosyaları, middleware ve yaşam döngüsü olaylarını yapılandırır.
"""

import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.config import settings
from app.routers import ask, documents, upload
from app.services.embedding_service import get_embedding_service
from app.services.vector_store import get_vector_store

# ─── Loglama ──────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ─── FastAPI Uygulaması ───────────────────────────────────────────

app = FastAPI(
    title="DocuAsk — Doküman Tabanlı Akıllı Soru-Cevap Sistemi",
    description=(
        "RAG (Retrieval-Augmented Generation) mimarisi ile "
        "PDF ve TXT dokümanlarına doğal dilde soru sorma platformu."
    ),
    version="1.0.0",
    docs_url="/api/docs",    # Swagger UI
    redoc_url="/api/redoc",  # ReDoc
)

# ─── Middleware ───────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],       # Geliştirme ortamı; üretimde sınırlandırın
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Statik Dosyalar & Şablonlar ──────────────────────────────────

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# ─── Router'lar ───────────────────────────────────────────────────

app.include_router(upload.router,    prefix="/api")
app.include_router(ask.router,       prefix="/api")
app.include_router(documents.router, prefix="/api")

# ─── Sayfalar ─────────────────────────────────────────────────────

@app.get("/", include_in_schema=False)
async def index(request: Request):
    """Ana web arayüzünü sunar"""
    return templates.TemplateResponse(request=request, name="index.html")


# ─── Sistem Endpoint'leri ─────────────────────────────────────────

@app.get("/api/health", tags=["Sistem"])
async def health_check():
    """Sistem sağlık durumunu döndürür"""
    vec_store = get_vector_store()
    groq_on  = bool(settings.GROQ_API_KEY)
    openai_on = bool(settings.OPENAI_API_KEY)
    return {
        "status": "ok",
        "openai_configured": openai_on or groq_on,
        "groq_configured": groq_on,
        "llm_provider": "groq" if groq_on else ("openai" if openai_on else "demo"),
        "vector_db": settings.VECTOR_DB,
        "total_chunks": vec_store.get_total_chunks(),
    }


# ─── Hata Yöneticileri ────────────────────────────────────────────

@app.exception_handler(404)
async def not_found(request: Request, exc):
    return JSONResponse(status_code=404, content={"detail": "Endpoint bulunamadı"})


@app.exception_handler(500)
async def server_error(request: Request, exc):
    logger.error(f"Sunucu hatası: {exc}")
    return JSONResponse(status_code=500, content={"detail": "Sunucu hatası oluştu"})


# ─── Yaşam Döngüsü ───────────────────────────────────────────────

@app.on_event("startup")
async def on_startup():
    """Uygulama başlangıcında servisleri ön-yükler"""
    logger.info("=" * 55)
    logger.info("  DocuAsk başlatılıyor...")
    logger.info("=" * 55)

    # Singleton'ları başlat (ilk istek gecikmesini önler)
    get_vector_store()
    emb = get_embedding_service()

    status_key = "✓ Yapılandırıldı" if settings.OPENAI_API_KEY else "✗ Eksik (Demo Modu)"
    logger.info(f"  OpenAI API Key : {status_key}")
    logger.info(f"  Embedding      : {emb.get_model_name()}")
    logger.info(f"  LLM Modeli     : {settings.LLM_MODEL}")
    logger.info(f"  Vektör DB      : {settings.VECTOR_DB}")
    logger.info(f"  Swagger UI     : http://localhost:8000/api/docs")
    logger.info("=" * 55)
