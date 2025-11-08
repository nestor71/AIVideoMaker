"""
AIVideoMaker Professional - Main Entry Point
=============================================
Versione 2.0.0 - Architettura Modulare Enterprise-Grade

Avvio applicazione:
    python main.py

    oppure

    uvicorn main:app --reload --host 0.0.0.0 --port 8000

Author: AIVideoMaker Team
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path

from app.core.config import settings
from app.core.database import init_db
from app.core.rate_limit import RateLimitMiddleware

# Setup logging
logging.basicConfig(
    level=logging.INFO if settings.environment != "production" else logging.WARNING,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(settings.log_file),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifecycle manager - Startup/Shutdown events
    """
    # ========== STARTUP ==========
    logger.info("=" * 60)
    logger.info(f"🚀 Avvio {settings.app_name} v{settings.app_version}")
    logger.info(f"   Environment: {settings.environment}")
    logger.info(f"   API: {settings.api_host}:{settings.api_port}")
    logger.info("=" * 60)

    # Inizializza database
    try:
        logger.info("Inizializzazione database...")
        init_db()
        logger.info("✅ Database ready")
    except Exception as e:
        logger.error(f"❌ Errore inizializzazione database: {e}")
        raise

    # Setup utente demo (solo in development)
    if settings.environment != "production":
        try:
            from app.core.database import SessionLocal
            from app.core.demo_setup import setup_demo_user

            db = SessionLocal()
            setup_demo_user(db)
            db.close()
        except Exception as e:
            logger.warning(f"⚠️  Errore setup demo user: {e}")

    # Verifica directory
    for directory in [settings.upload_dir, settings.output_dir, settings.temp_dir]:
        if not directory.exists():
            directory.mkdir(parents=True, exist_ok=True)
            logger.info(f"✅ Directory creata: {directory}")

    logger.info("✅ Startup completato\n")

    yield

    # ========== SHUTDOWN ==========
    logger.info("\n💤 Shutdown applicazione...")
    logger.info("✅ Shutdown completato")


# Crea FastAPI app
app = FastAPI(
    title=settings.app_name,
    description="Professional Video Editing Suite con architettura modulare",
    version=settings.app_version,
    lifespan=lifespan,
    docs_url="/docs" if settings.debug else None,  # Swagger UI
    redoc_url="/redoc" if settings.debug else None,  # ReDoc
)

# ==================== MIDDLEWARE ====================

# Rate Limiting (eseguito per primo)
app.add_middleware(
    RateLimitMiddleware,
    enabled=settings.rate_limit_enabled
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================== STATIC FILES ====================

app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/uploads", StaticFiles(directory=settings.upload_dir), name="uploads")
app.mount("/outputs", StaticFiles(directory=settings.output_dir), name="outputs")

# ==================== TEMPLATES ====================

templates = Jinja2Templates(directory="templates")

# ==================== ROUTES ====================

# Import routes
from app.api.routes import (
    auth,
    admin,
    chromakey,
    translation,
    thumbnail,
    youtube,
    pipeline,
    metadata,
    logo,
    transcription,  # Abilitato - Whisper opzionale (graceful degradation)
    # screen_record,  # Richiede PyGetWindow (non installato)
    seo_metadata    # Abilitato - Whisper opzionale (graceful degradation)
)

# Import file upload route
from app.api.routes import files

# ==================== HTML ROUTES ====================

@app.get("/")
async def index(request: Request):
    """Serve interfaccia web principale"""
    return templates.TemplateResponse("index_new.html", {"request": request})

@app.get("/translation")
async def translation_page(request: Request):
    """Serve pagina dedicata traduzione video"""
    return templates.TemplateResponse("translation.html", {"request": request})

# ==================== API STATUS ROUTES ====================

@app.get("/health")
async def health_check():
    """Health check endpoint per monitoring"""
    return {
        "status": "healthy",
        "version": settings.app_version,
        "environment": settings.environment
    }

@app.get("/api-status")
async def api_status():
    """Status API completo"""
    return {
        "app": settings.app_name,
        "version": settings.app_version,
        "status": "running",
        "environment": settings.environment,
        "message": "AIVideoMaker Professional API v2.0"
    }

@app.get("/demo-credentials")
async def get_demo_credentials():
    """
    Ottieni credenziali demo per auto-login.

    SOLO in development mode.
    In production ritorna 404.
    """
    if settings.environment == "production":
        raise HTTPException(status_code=404, detail="Not found")

    from app.core.demo_setup import get_demo_credentials

    credentials = get_demo_credentials()
    if not credentials:
        raise HTTPException(status_code=404, detail="Demo mode disabled")

    return credentials

# ==================== API ROUTES ====================

# Core routes
app.include_router(auth.router, prefix=f"{settings.api_prefix}/auth", tags=["Authentication"])
app.include_router(admin.router, prefix=f"{settings.api_prefix}/admin", tags=["Admin"])
app.include_router(files.router, prefix="/api", tags=["File Upload"])  # Endpoint compatibilità /api/upload

# Processing routes
app.include_router(chromakey.router, prefix=f"{settings.api_prefix}/chromakey", tags=["Chromakey"])
app.include_router(translation.router, prefix=f"{settings.api_prefix}/translation", tags=["Translation"])
app.include_router(thumbnail.router, prefix=f"{settings.api_prefix}/thumbnail", tags=["Thumbnail"])
app.include_router(youtube.router, prefix=f"{settings.api_prefix}/youtube", tags=["YouTube"])
app.include_router(pipeline.router, prefix=f"{settings.api_prefix}/pipelines", tags=["Pipeline AUTO"])
app.include_router(logo.router, prefix=f"{settings.api_prefix}/logo", tags=["Logo Overlay"])
app.include_router(metadata.router, prefix=f"{settings.api_prefix}/metadata", tags=["Metadata Extraction"])
app.include_router(transcription.router, prefix=f"{settings.api_prefix}/transcription", tags=["Transcription"])  # Abilitato - Whisper opzionale
app.include_router(seo_metadata.router, prefix=f"{settings.api_prefix}/seo", tags=["SEO Metadata AI"])  # Abilitato - Whisper opzionale

# Temporarily disabled routes
# app.include_router(screen_record.router, prefix=f"{settings.api_prefix}/screen-record", tags=["Screen Recording"])  # Richiede PyGetWindow

# ==================== ERROR HANDLERS ====================

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": str(exc) if settings.debug else "An error occurred"
        }
    )


if __name__ == "__main__":
    import uvicorn

    logger.info(f"Starting {settings.app_name} on {settings.api_host}:{settings.api_port}")

    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
        log_level="info" if settings.debug else "warning"
    )
