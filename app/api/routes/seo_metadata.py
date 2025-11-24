"""
SEO Metadata Routes
===================
Route per generazione automatica metadata SEO ottimizzati
"""

from pathlib import Path
from typing import Optional, List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.config import settings
from app.core.usage_tracker import track_action
from app.models.user import User
from app.models.job import Job, JobType, JobStatus
from app.services.seo_metadata_service import SEOMetadataService, SEOMetadataParams

router = APIRouter()


# ==================== Pydantic Schemas ====================

class SEOMetadataRequest(BaseModel):
    """Schema per richiesta generazione SEO metadata"""
    video_path: str
    output_name: Optional[str] = "seo_metadata"

    # Parametri SEO
    num_hashtags: int = Field(default=10, ge=1, le=30, description="Numero hashtag da generare")
    num_tags: int = Field(default=30, ge=1, le=100, description="Numero tag da generare")
    language: str = Field(default="it", description="Lingua output (it, en, es, fr, de, pt)")

    # Parametri thumbnail
    generate_thumbnail: bool = Field(default=True, description="Genera thumbnail accattivante")
    thumbnail_style: str = Field(default="modern", description="Stile thumbnail: modern, minimal, bold, gradient")
    thumbnail_text_overlay: bool = Field(default=True, description="Aggiungi testo su thumbnail")

    # Parametri analisi
    num_frames_to_analyze: int = Field(default=5, ge=1, le=10, description="Frame da analizzare")
    analyze_audio: bool = Field(default=True, description="Analizza audio per contesto")

    # Target platform
    target_platform: str = Field(default="youtube", description="Platform: youtube, instagram, tiktok, facebook")

    class Config:
        protected_namespaces = ()  # Permette model_ fields


class SEOMetadataResponse(BaseModel):
    """Schema per risposta SEO metadata"""
    job_id: str
    status: str
    message: str
    title: Optional[str] = None
    description: Optional[str] = None
    hashtags: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    thumbnail_path: Optional[str] = None
    progress: int = 0


# ==================== Helper Functions ====================

def create_seo_job(
    user: User,
    params: SEOMetadataRequest,
    db: Session
) -> Job:
    """Crea job generazione SEO nel database"""
    job = Job(
        user_id=user.id,
        job_type=JobType.SEO_METADATA,
        status=JobStatus.PENDING,
        parameters=params.dict()
    )

    db.add(job)
    db.commit()
    db.refresh(job)

    return job


def process_seo_task(job_id: str, params: SEOMetadataRequest, db: Session):
    """Task background per generazione SEO metadata"""
    # Converti job_id da stringa a UUID
    try:
        job_id_uuid = UUID(job_id)
    except (ValueError, AttributeError):
        return

    job = db.query(Job).filter(Job.id == job_id_uuid).first()

    if not job:
        return

    try:
        # Aggiorna status
        job.status = JobStatus.PROCESSING
        job.progress = 0
        db.commit()

        # Configura servizio
        service = SEOMetadataService(settings)

        # Prepara parametri
        seo_params = SEOMetadataParams(
            video_path=Path(params.video_path),
            output_dir=settings.output_dir / params.output_name,
            num_hashtags=params.num_hashtags,
            num_tags=params.num_tags,
            language=params.language,
            generate_thumbnail=params.generate_thumbnail,
            thumbnail_style=params.thumbnail_style,
            thumbnail_text_overlay=params.thumbnail_text_overlay,
            num_frames_to_analyze=params.num_frames_to_analyze,
            analyze_audio=params.analyze_audio,
            target_platform=params.target_platform
        )

        # Callback per aggiornare progresso
        def progress_callback(progress: int, message: str):
            job.progress = progress
            job.message = message
            db.commit()

        # Genera metadata SEO
        result = service.generate(seo_params, progress_callback)

        # Aggiorna job
        job.status = JobStatus.COMPLETED
        job.progress = 100
        job.result = result
        db.commit()

    except Exception as e:
        job.status = JobStatus.FAILED
        job.error_message = str(e)
        db.commit()


# ==================== Routes ====================

@router.post("/generate", response_model=SEOMetadataResponse, status_code=status.HTTP_202_ACCEPTED)
async def generate_seo_metadata(
    request: SEOMetadataRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Genera metadata SEO ottimizzati per video

    **Genera automaticamente con AI:**
    - **Titolo** accattivante e SEO-friendly
    - **Descrizione** completa con keywords ottimizzate
    - **Hashtag** rilevanti (numero configurabile: 1-30)
    - **Tag** SEO (numero configurabile: 1-100)
    - **Thumbnail** accattivante con text overlay (opzionale)

    **Parametri:**

    - **video_path**: Path del video da analizzare
    - **output_name**: Nome cartella output (default: "seo_metadata")
    - **num_hashtags**: Numero hashtag da generare (1-30, default: 10)
    - **num_tags**: Numero tag da generare (1-100, default: 30)
    - **language**: Lingua output (it, en, es, fr, de, pt - default: it)
    - **generate_thumbnail**: Genera thumbnail (default: true)
    - **thumbnail_style**: Stile thumbnail (modern, minimal, bold, gradient - default: modern)
    - **thumbnail_text_overlay**: Testo su thumbnail (default: true)
    - **num_frames_to_analyze**: Frame da analizzare (1-10, default: 5)
    - **analyze_audio**: Trascrivi audio per contesto (default: true)
    - **target_platform**: Platform target (youtube, instagram, tiktok, facebook - default: youtube)

    **Platform-specific limits:**

    - **YouTube**: Titolo 100 char, Descrizione 5000 char, Hashtag max 15, Thumbnail 1280x720
    - **Instagram**: Titolo 150 char, Descrizione 2200 char, Hashtag max 30, Thumbnail 1080x1080
    - **TikTok**: Titolo 150 char, Descrizione 2200 char, Hashtag max 20, Thumbnail 1080x1920
    - **Facebook**: Titolo 255 char, Descrizione 63k char, Hashtag max 10, Thumbnail 1200x630

    **Richiede:**
    - OpenAI API key configurata nel .env (OPENAI_API_KEY)
    - JWT token authentication

    **Elaborazione asincrona in background.**
    Usa GET /jobs/{job_id} per monitorare progresso e ottenere risultati.
    """
    # Valida video path
    video_path = Path(request.video_path)
    if not video_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Video non trovato: {request.video_path}"
        )

    # Valida OpenAI API key
    if not settings.openai_api_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="OpenAI API key non configurata. Aggiungi OPENAI_API_KEY al file .env"
        )

    # Valida parametri
    if request.language not in SEOMetadataService.SUPPORTED_LANGUAGES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Lingua non supportata. Disponibili: {SEOMetadataService.SUPPORTED_LANGUAGES}"
        )

    if request.thumbnail_style not in SEOMetadataService.THUMBNAIL_STYLES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Stile thumbnail non valido. Disponibili: {SEOMetadataService.THUMBNAIL_STYLES}"
        )

    if request.target_platform not in SEOMetadataService.PLATFORMS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Platform non supportata. Disponibili: {list(SEOMetadataService.PLATFORMS.keys())}"
        )

    # Crea job
    job = create_seo_job(current_user, request, db)

    # Avvia task in background
    background_tasks.add_task(process_seo_task, str(job.id), request, db)

    # Track action
    track_action(db, current_user.id, "action", {"job_id": str(job.id)})

    return {
        "job_id": str(job.id),
        "status": "accepted",
        "message": f"Generazione SEO metadata avviata. Analisi AI in corso per {request.target_platform}...",
        "progress": 0
    }


@router.post("/upload", response_model=SEOMetadataResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_and_generate_seo(
    video: UploadFile = File(..., description="Video da analizzare"),
    num_hashtags: int = Form(10, ge=1, le=30),
    num_tags: int = Form(30, ge=1, le=100),
    language: str = Form("it"),
    generate_thumbnail: bool = Form(True),
    thumbnail_style: str = Form("modern"),
    target_platform: str = Form("youtube"),
    background_tasks: BackgroundTasks = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Upload video e genera metadata SEO

    Upload di video in un'unica chiamata, poi genera metadata SEO ottimizzati.

    Richiede JWT token. Elaborazione asincrona in background.
    """
    # Salva file upload
    video_path = settings.upload_dir / f"seo_{current_user.id}_{video.filename}"

    with open(video_path, "wb") as f:
        content = await video.read()
        f.write(content)

    # Crea request
    request = SEOMetadataRequest(
        video_path=str(video_path),
        output_name=f"seo_{video.filename}",
        num_hashtags=num_hashtags,
        num_tags=num_tags,
        language=language,
        generate_thumbnail=generate_thumbnail,
        thumbnail_style=thumbnail_style,
        target_platform=target_platform
    )

    # Crea job
    job = create_seo_job(current_user, request, db)

    # Avvia task in background
    background_tasks.add_task(process_seo_task, str(job.id), request, db)

    return {
        "job_id": str(job.id),
        "status": "accepted",
        "message": f"Video caricato. Generazione SEO metadata per {target_platform} avviata...",
        "progress": 0
    }


@router.get("/jobs/{job_id}", response_model=SEOMetadataResponse)
async def get_job_status(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Ottieni status job generazione SEO metadata

    - **job_id**: ID del job

    **Response quando completato:**
    - title: Titolo SEO-optimized
    - description: Descrizione completa
    - hashtags: Lista hashtag (#tag1, #tag2, ...)
    - tags: Lista tag (tag1, tag2, ...)
    - thumbnail_path: Path thumbnail generata (se richiesta)

    Richiede JWT token. Puoi vedere solo i tuoi job.
    """
    # Converti job_id da stringa a UUID
    try:
        job_id_uuid = UUID(job_id)
    except (ValueError, AttributeError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Job ID non valido"
        )

    job = db.query(Job).filter(
        Job.id == job_id_uuid,
        Job.user_id == current_user.id,
        Job.job_type == JobType.SEO_METADATA
    ).first()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job non trovato"
        )

    response = {
        "job_id": str(job.id),
        "status": job.status.value,
        "message": job.message or (
            "Generazione SEO in corso..." if job.status == JobStatus.PROCESSING
            else "Metadata SEO generati!" if job.status == JobStatus.COMPLETED
            else job.error_message or "Job in attesa"
        ),
        "progress": job.progress
    }

    # Aggiungi risultati se completato
    if job.status == JobStatus.COMPLETED and job.result:
        response.update({
            "title": job.result.get("title"),
            "description": job.result.get("description"),
            "hashtags": job.result.get("hashtags"),
            "tags": job.result.get("tags"),
            "thumbnail_path": job.result.get("thumbnail_path")
        })

    return response
