"""
Translation Routes
==================
Route per traduzione video con Whisper + gTTS
"""

from pathlib import Path
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel
import logging

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.config import settings
from app.core.usage_tracker import track_action
from app.models.user import User
from app.models.job import Job, JobType, JobStatus
from app.services.translation_service import TranslationService, TranslationParams

router = APIRouter()
logger = logging.getLogger(__name__)


# ==================== Pydantic Schemas ====================

class TranslationRequest(BaseModel):
    """Schema per richiesta traduzione"""
    video_path: str  # Path video da tradurre
    target_language: str  # Codice lingua target (es. "it", "en", "es")
    output_name: Optional[str] = "translated_video.mp4"

    # Parametri opzionali
    source_language: Optional[str] = None  # Auto-detect se None
    use_elevenlabs: bool = False  # Usa ElevenLabs per voce più naturale
    voice_id: Optional[str] = None  # ID voce ElevenLabs (se use_elevenlabs=True)
    subtitle_position: str = "bottom"  # "bottom", "top", "none"
    subtitle_style: Optional[dict] = None  # Stile sottotitoli personalizzato


class TranslationResponse(BaseModel):
    """Schema per risposta traduzione"""
    job_id: str
    status: str
    message: str
    output_path: Optional[str] = None
    progress: int = 0
    detected_language: Optional[str] = None


class LanguageList(BaseModel):
    """Lista lingue supportate"""
    languages: dict[str, str]


# ==================== Helper Functions ====================

def create_translation_job(
    user: User,
    params: TranslationRequest,
    db: Session
) -> Job:
    """Crea job traduzione nel database"""
    job = Job(
        user_id=user.id,
        job_type=JobType.TRANSLATION,
        status=JobStatus.PENDING,
        parameters=params.dict()
    )

    db.add(job)
    db.commit()
    db.refresh(job)

    return job


def process_translation_task(job_id: str, params: TranslationRequest, db: Session):
    """Task background per traduzione video"""
    job = db.query(Job).filter(Job.id == job_id).first()

    if not job:
        return

    try:
        # Aggiorna status
        job.status = JobStatus.PROCESSING
        job.progress = 0
        db.commit()

        # Configura servizio
        service = TranslationService(settings)

        # Prepara parametri
        translation_params = TranslationParams(
            video_path=Path(params.video_path),
            target_language=params.target_language,
            output_path=settings.output_dir / params.output_name,
            source_language=params.source_language,
            use_elevenlabs=params.use_elevenlabs,
            voice_id=params.voice_id,
            subtitle_position=params.subtitle_position,
            subtitle_style=params.subtitle_style
        )

        # Callback per aggiornare progresso
        def progress_callback(progress: int):
            job.progress = progress
            db.commit()

        # Esegui traduzione
        result = service.translate(translation_params, progress_callback)

        # Aggiorna job
        job.status = JobStatus.COMPLETED
        job.progress = 100
        job.result = result
        db.commit()

    except Exception as e:
        job.status = JobStatus.FAILED
        job.error = str(e)
        db.commit()


# ==================== Routes ====================

@router.get("/languages", response_model=LanguageList)
async def get_supported_languages():
    """
    Lista lingue supportate per traduzione

    Non richiede autenticazione.
    """
    service = TranslationService()
    return {
        "languages": service.SUPPORTED_LANGUAGES
    }


@router.post("/translate", response_model=TranslationResponse, status_code=status.HTTP_202_ACCEPTED)
async def translate_video(
    request: TranslationRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Traduci video

    - **video_path**: Path video da tradurre
    - **target_language**: Lingua target (usa GET /languages per lista)
    - **output_name**: Nome file output (default: translated_video.mp4)
    - **source_language**: Lingua sorgente (auto-detect se omesso)
    - **use_elevenlabs**: Usa ElevenLabs per voce naturale (richiede API key)
    - **voice_id**: ID voce ElevenLabs (opzionale)
    - **subtitle_position**: Posizione sottotitoli ("bottom", "top", "none")

    Processo:
    1. Estrae audio da video
    2. Trascrive con Whisper (auto-detect lingua)
    3. Traduce testo con Google Translate
    4. Genera audio tradotto con gTTS o ElevenLabs
    5. Ricombina audio + video + sottotitoli

    Richiede JWT token. Elaborazione asincrona in background.
    """
    # Verifica lingua supportata
    service = TranslationService()
    if request.target_language not in service.SUPPORTED_LANGUAGES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Lingua {request.target_language} non supportata. Usa GET /languages per lista completa."
        )

    # Crea job
    job = create_translation_job(current_user, request, db)

    # Avvia task in background
    background_tasks.add_task(process_translation_task, str(job.id), request, db)

    # Track action
    track_action(db, current_user.id, "action", {"job_id": str(job.id)})

    return {
        "job_id": str(job.id),
        "status": "accepted",
        "message": "Job traduzione avviato. Usa GET /jobs/{job_id} per monitorare progresso.",
        "progress": 0
    }


@router.post("/upload", response_model=TranslationResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_and_translate(
    video: UploadFile = File(..., description="Video da tradurre"),
    target_language: str = Form(..., description="Codice lingua target (es. 'it', 'en')"),
    output_name: str = Form("translated_video.mp4"),
    use_elevenlabs: bool = Form(False),
    subtitle_position: str = Form("bottom"),
    background_tasks: BackgroundTasks = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Upload e traduzione video in un'unica chiamata

    Upload video, poi traduci automaticamente.

    Richiede JWT token. Elaborazione asincrona in background.
    """
    # Verifica lingua supportata
    service = TranslationService()
    if target_language not in service.SUPPORTED_LANGUAGES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Lingua {target_language} non supportata."
        )

    # 🧹 PULIZIA: Elimina tutti i file precedenti nella cartella uploads
    logger.info("🧹 Pulizia cartella uploads...")
    files_deleted = 0
    for old_file in settings.upload_dir.iterdir():
        if old_file.is_file():
            try:
                old_file.unlink()
                files_deleted += 1
            except Exception as e:
                logger.warning(f"⚠️ Impossibile eliminare {old_file}: {e}")
    logger.info(f"✅ Eliminati {files_deleted} file vecchi dalla cartella uploads")

    # Salva file upload
    video_path = settings.upload_dir / f"video_{current_user.id}_{video.filename}"

    with open(video_path, "wb") as f:
        content = await video.read()
        f.write(content)

    # Crea request
    request = TranslationRequest(
        video_path=str(video_path),
        target_language=target_language,
        output_name=output_name,
        use_elevenlabs=use_elevenlabs,
        subtitle_position=subtitle_position
    )

    # Crea job
    job = create_translation_job(current_user, request, db)

    # Avvia task in background
    background_tasks.add_task(process_translation_task, str(job.id), request, db)

    return {
        "job_id": str(job.id),
        "status": "accepted",
        "message": "Video caricato. Job traduzione avviato.",
        "progress": 0
    }


@router.get("/jobs/{job_id}", response_model=TranslationResponse)
async def get_job_status(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Ottieni status job traduzione

    - **job_id**: ID del job

    Richiede JWT token. Puoi vedere solo i tuoi job.
    """
    job = db.query(Job).filter(
        Job.id == job_id,
        Job.user_id == current_user.id,
        Job.job_type == JobType.TRANSLATION
    ).first()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job non trovato"
        )

    return {
        "job_id": str(job.id),
        "status": job.status.value,
        "message": job.error or "Job in elaborazione" if job.status == JobStatus.PROCESSING else "Job completato",
        "output_path": job.result.get("output_path") if job.result else None,
        "progress": job.progress,
        "detected_language": job.result.get("detected_language") if job.result else None
    }
