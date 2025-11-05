"""
Thumbnail Routes
================
Route per generazione thumbnail YouTube con AI
"""

from pathlib import Path
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.config import settings
from app.models.user import User
from app.models.job import Job, JobType, JobStatus
from app.services.thumbnail_service import ThumbnailService, ThumbnailParams, ThumbnailSource

router = APIRouter()


# ==================== Pydantic Schemas ====================

class ThumbnailRequest(BaseModel):
    """Schema per richiesta generazione thumbnail"""
    source_type: str  # "ai", "upload", "video_frame"
    output_name: Optional[str] = "thumbnail.jpg"

    # Per source_type = "ai"
    prompt: Optional[str] = None
    style: Optional[str] = "cinematic"  # Vedi ThumbnailService.AI_STYLES

    # Per source_type = "upload"
    image_path: Optional[str] = None

    # Per source_type = "video_frame"
    video_path: Optional[str] = None
    frame_timestamp: Optional[float] = 0.0  # Secondi nel video

    # Parametri testo overlay
    text_overlay: Optional[str] = None
    text_position: str = "center"  # "top", "center", "bottom"
    text_size: int = 72
    text_color: str = "white"
    text_style: str = "bold"  # "bold", "outline", "shadow"


class ThumbnailResponse(BaseModel):
    """Schema per risposta thumbnail"""
    job_id: str
    status: str
    message: str
    output_path: Optional[str] = None
    preview_url: Optional[str] = None
    progress: int = 0


class StyleList(BaseModel):
    """Lista stili AI disponibili"""
    styles: dict[str, str]


# ==================== Helper Functions ====================

def create_thumbnail_job(
    user: User,
    params: ThumbnailRequest,
    db: Session
) -> Job:
    """Crea job thumbnail nel database"""
    job = Job(
        user_id=user.id,
        job_type=JobType.THUMBNAIL,
        status=JobStatus.PENDING,
        parameters=params.dict()
    )

    db.add(job)
    db.commit()
    db.refresh(job)

    return job


def process_thumbnail_task(job_id: str, params: ThumbnailRequest, db: Session):
    """Task background per generazione thumbnail"""
    job = db.query(Job).filter(Job.id == job_id).first()

    if not job:
        return

    try:
        # Aggiorna status
        job.status = JobStatus.PROCESSING
        job.progress = 0
        db.commit()

        # Configura servizio
        service = ThumbnailService(settings)

        # Determina source type
        if params.source_type == "ai":
            source = ThumbnailSource.AI
        elif params.source_type == "upload":
            source = ThumbnailSource.UPLOAD
        elif params.source_type == "video_frame":
            source = ThumbnailSource.VIDEO_FRAME
        else:
            raise ValueError(f"source_type non valido: {params.source_type}")

        # Prepara parametri
        thumbnail_params = ThumbnailParams(
            source=source,
            output_path=settings.output_dir / params.output_name,
            prompt=params.prompt,
            style=params.style,
            image_path=Path(params.image_path) if params.image_path else None,
            video_path=Path(params.video_path) if params.video_path else None,
            frame_timestamp=params.frame_timestamp,
            text_overlay=params.text_overlay,
            text_position=params.text_position,
            text_size=params.text_size,
            text_color=params.text_color,
            text_style=params.text_style
        )

        # Callback per aggiornare progresso
        def progress_callback(progress: int):
            job.progress = progress
            db.commit()

        # Genera thumbnail
        result = service.generate(thumbnail_params, progress_callback)

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

@router.get("/styles", response_model=StyleList)
async def get_ai_styles():
    """
    Lista stili AI disponibili per generazione thumbnail

    Non richiede autenticazione.
    """
    service = ThumbnailService()
    return {
        "styles": service.AI_STYLES
    }


@router.post("/generate", response_model=ThumbnailResponse, status_code=status.HTTP_202_ACCEPTED)
async def generate_thumbnail(
    request: ThumbnailRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Genera thumbnail YouTube

    **Tre modalità di generazione:**

    1. **AI (DALL-E 3)**:
       - `source_type`: "ai"
       - `prompt`: Descrizione thumbnail (es. "Un gatto nello spazio")
       - `style`: Stile AI (usa GET /styles per lista)

    2. **Upload Immagine**:
       - `source_type`: "upload"
       - `image_path`: Path immagine caricata

    3. **Frame da Video**:
       - `source_type`: "video_frame"
       - `video_path`: Path video
       - `frame_timestamp`: Timestamp frame (secondi)

    **Parametri testo overlay** (opzionali per tutte le modalità):
    - `text_overlay`: Testo da sovrapporre
    - `text_position`: "top", "center", "bottom"
    - `text_size`: Dimensione font (default: 72)
    - `text_color`: Colore testo (default: "white")
    - `text_style`: "bold", "outline", "shadow"

    Output: Thumbnail 1280x720 (formato YouTube)

    Richiede JWT token. Elaborazione asincrona in background.
    """
    # Validazioni
    if request.source_type == "ai" and not request.prompt:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="prompt richiesto per source_type='ai'"
        )

    if request.source_type == "upload" and not request.image_path:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="image_path richiesto per source_type='upload'"
        )

    if request.source_type == "video_frame" and not request.video_path:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="video_path richiesto per source_type='video_frame'"
        )

    # Crea job
    job = create_thumbnail_job(current_user, request, db)

    # Avvia task in background
    background_tasks.add_task(process_thumbnail_task, str(job.id), request, db)

    return {
        "job_id": str(job.id),
        "status": "accepted",
        "message": "Job thumbnail avviato. Usa GET /jobs/{job_id} per monitorare progresso.",
        "progress": 0
    }


@router.post("/upload", response_model=ThumbnailResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_and_generate(
    image: UploadFile = File(..., description="Immagine per thumbnail"),
    output_name: str = Form("thumbnail.jpg"),
    text_overlay: Optional[str] = Form(None),
    text_position: str = Form("center"),
    text_size: int = Form(72),
    text_color: str = Form("white"),
    text_style: str = Form("bold"),
    background_tasks: BackgroundTasks = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Upload immagine e genera thumbnail YouTube

    Upload immagine, ridimensiona a 1280x720, opzionalmente aggiungi testo.

    Richiede JWT token. Elaborazione asincrona in background.
    """
    # Salva file upload
    image_path = settings.upload_dir / f"thumb_{current_user.id}_{image.filename}"

    with open(image_path, "wb") as f:
        content = await image.read()
        f.write(content)

    # Crea request
    request = ThumbnailRequest(
        source_type="upload",
        image_path=str(image_path),
        output_name=output_name,
        text_overlay=text_overlay,
        text_position=text_position,
        text_size=text_size,
        text_color=text_color,
        text_style=text_style
    )

    # Crea job
    job = create_thumbnail_job(current_user, request, db)

    # Avvia task in background
    background_tasks.add_task(process_thumbnail_task, str(job.id), request, db)

    return {
        "job_id": str(job.id),
        "status": "accepted",
        "message": "Immagine caricata. Job thumbnail avviato.",
        "progress": 0
    }


@router.get("/jobs/{job_id}", response_model=ThumbnailResponse)
async def get_job_status(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Ottieni status job thumbnail

    - **job_id**: ID del job

    Richiede JWT token. Puoi vedere solo i tuoi job.
    """
    job = db.query(Job).filter(
        Job.id == job_id,
        Job.user_id == current_user.id,
        Job.job_type == JobType.THUMBNAIL
    ).first()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job non trovato"
        )

    # Genera preview URL se completato
    preview_url = None
    if job.status == JobStatus.COMPLETED and job.result:
        output_path = job.result.get("output_path")
        if output_path:
            # URL relativo per servire file statico
            preview_url = f"/outputs/{Path(output_path).name}"

    return {
        "job_id": str(job.id),
        "status": job.status.value,
        "message": job.error_message or "Job in elaborazione" if job.status == JobStatus.PROCESSING else "Job completato",
        "output_path": job.result.get("output_path") if job.result else None,
        "preview_url": preview_url,
        "progress": job.progress
    }
