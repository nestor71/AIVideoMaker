"""
Transcription Routes
====================
Route per trascrizione audio/video con Whisper
"""

from pathlib import Path
from typing import Optional, List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.config import settings
from app.core.usage_tracker import track_action
from app.models.user import User
from app.models.job import Job, JobType, JobStatus
from app.services.transcription_service import TranscriptionService, TranscriptionParams

router = APIRouter()


# ==================== Pydantic Schemas ====================

class TranscriptionRequest(BaseModel):
    """Schema per richiesta trascrizione"""
    media_path: str
    output_name: Optional[str] = "transcription.json"
    model_size: str = "base"  # tiny, base, small, medium, large
    language: Optional[str] = None  # None = auto-detect
    export_formats: Optional[List[str]] = ["json"]  # json, srt, vtt, txt


class TranscriptionResponse(BaseModel):
    """Schema per risposta trascrizione"""
    job_id: str
    status: str
    message: str
    output_path: Optional[str] = None
    progress: int = 0


# ==================== Helper Functions ====================

def create_transcription_job(
    user: User,
    params: TranscriptionRequest,
    db: Session
) -> Job:
    """Crea job trascrizione nel database"""
    job = Job(
        user_id=user.id,
        job_type=JobType.TRANSCRIPTION,
        status=JobStatus.PENDING,
        parameters=params.dict()
    )

    db.add(job)
    db.commit()
    db.refresh(job)

    return job


def process_transcription_task(job_id: str, params: TranscriptionRequest, db: Session):
    """Task background per trascrizione"""
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
        service = TranscriptionService(settings)

        # Prepara parametri
        transcription_params = TranscriptionParams(
            media_path=Path(params.media_path),
            output_path=settings.output_dir / params.output_name,
            model_size=params.model_size,
            language=params.language,
            export_formats=params.export_formats
        )

        # Callback per aggiornare progresso
        def progress_callback(progress: int, message: str):
            job.progress = progress
            db.commit()

        # Esegui trascrizione
        result = service.transcribe(transcription_params, progress_callback)

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

@router.post("/transcribe", response_model=TranscriptionResponse, status_code=status.HTTP_202_ACCEPTED)
async def transcribe_media(
    request: TranscriptionRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Trascrivi audio/video con Whisper

    - **media_path**: Path file video/audio
    - **output_name**: Nome file output (default: transcription.json)
    - **model_size**: Modello Whisper ("tiny", "base", "small", "medium", "large")
    - **language**: Codice lingua (None = auto-detect)
    - **export_formats**: Formati export ["json", "srt", "vtt", "txt"]

    Modelli Whisper:
    - tiny: Veloce, meno preciso (~1GB RAM)
    - base: Bilanciato (~1GB RAM) - **RACCOMANDATO**
    - small: Buona precisione (~2GB RAM)
    - medium: Alta precisione (~5GB RAM)
    - large: Massima precisione (~10GB RAM)

    Export formati:
    - json: Testo + timestamps segmenti
    - srt: Sottotitoli SubRip
    - vtt: Sottotitoli WebVTT
    - txt: Solo testo

    Richiede JWT token. Elaborazione asincrona in background.
    """
    # Valida model
    if request.model_size not in TranscriptionService.AVAILABLE_MODELS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Modello non valido. Disponibili: {TranscriptionService.AVAILABLE_MODELS}"
        )

    # Crea job
    job = create_transcription_job(current_user, request, db)

    # Avvia task in background
    background_tasks.add_task(process_transcription_task, str(job.id), request, db)

    # Track action
    track_action(db, current_user.id, "action", {"job_id": str(job.id)})

    return {
        "job_id": str(job.id),
        "status": "accepted",
        "message": "Job trascrizione avviato. Usa GET /jobs/{job_id} per monitorare progresso.",
        "progress": 0
    }


@router.post("/upload", response_model=TranscriptionResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_and_transcribe(
    file: UploadFile = File(..., description="File video/audio"),
    model_size: str = Form("base"),
    language: Optional[str] = Form(None),
    export_formats: str = Form("json,srt"),  # Comma-separated
    background_tasks: BackgroundTasks = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Upload file e trascrivi

    Richiede JWT token. Elaborazione asincrona in background.
    """
    # Salva file upload
    file_path = settings.upload_dir / f"transcribe_{current_user.id}_{file.filename}"

    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)

    # Parse export_formats
    formats = [fmt.strip() for fmt in export_formats.split(",")]

    # Crea request
    request = TranscriptionRequest(
        media_path=str(file_path),
        output_name=f"transcription_{file.stem}.json",
        model_size=model_size,
        language=language,
        export_formats=formats
    )

    # Crea job
    job = create_transcription_job(current_user, request, db)

    # Avvia task in background
    background_tasks.add_task(process_transcription_task, str(job.id), request, db)

    return {
        "job_id": str(job.id),
        "status": "accepted",
        "message": "File caricato. Job trascrizione avviato.",
        "progress": 0
    }


@router.get("/jobs/{job_id}", response_model=TranscriptionResponse)
async def get_job_status(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Ottieni status job trascrizione

    - **job_id**: ID del job

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
        Job.job_type == JobType.TRANSCRIPTION
    ).first()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job non trovato"
        )

    return {
        "job_id": str(job.id),
        "status": job.status.value,
        "message": job.error_message or "Job in elaborazione" if job.status == JobStatus.PROCESSING else "Job completato",
        "output_path": job.result.get("output_path") if job.result else None,
        "progress": job.progress
    }
