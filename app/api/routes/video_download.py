"""
Video Download Routes
=====================
API per scaricare video da YouTube, TikTok, Vimeo, Twitter, Instagram, ecc.
"""

from pathlib import Path
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel, HttpUrl
from datetime import datetime

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.config import settings
from app.models.user import User
from app.models.job import Job, JobType, JobStatus
from app.services.video_download_service import VideoDownloadService, VideoDownloadParams

router = APIRouter()


# ==================== Pydantic Schemas ====================

class VideoDownloadRequest(BaseModel):
    """Schema per richiesta download video"""
    url: str  # URL video
    output_name: Optional[str] = None  # Nome file output (opzionale)

    # Opzioni qualità
    quality: str = "best"  # "best", "worst", "720p", "1080p", "4k"
    format_preference: str = "mp4"  # "mp4", "webm", "mkv", "any"

    # Opzioni audio
    extract_audio: bool = False  # Scarica solo audio
    audio_format: str = "mp3"  # "mp3", "m4a", "wav", "opus"

    # Opzioni metadata
    embed_thumbnail: bool = True
    embed_metadata: bool = True
    embed_subtitles: bool = False

    # Limiti
    max_filesize_mb: Optional[int] = None  # Max dimensione MB


class VideoDownloadResponse(BaseModel):
    """Schema per risposta download video"""
    job_id: str
    status: str
    message: str
    url: str
    progress: int = 0


class VideoInfoRequest(BaseModel):
    """Schema per richiesta info video"""
    url: str


class VideoInfoResponse(BaseModel):
    """Schema per risposta info video"""
    title: str
    duration: int  # secondi
    uploader: str
    upload_date: str
    view_count: int
    like_count: int
    description: str
    thumbnail: str
    formats_available: int
    url: str
    extractor: str  # youtube, tiktok, vimeo, etc.


class JobStatusResponse(BaseModel):
    """Schema per stato job"""
    job_id: str
    status: str
    progress: int
    message: Optional[str] = None
    result: Optional[dict] = None
    error: Optional[str] = None
    output_path: Optional[str] = None


# ==================== Helper Functions ====================

def create_download_job(
    user: User,
    params: VideoDownloadRequest,
    db: Session
) -> Job:
    """Crea job download nel database"""
    job = Job(
        user_id=user.id,
        job_type=JobType.CHROMAKEY,  # TODO: Aggiungere JobType.VIDEO_DOWNLOAD
        status=JobStatus.PENDING,
        parameters=params.dict()
    )

    db.add(job)
    db.commit()
    db.refresh(job)

    return job


def process_download_task(job_id: str, params: VideoDownloadRequest):
    """Task background per download video"""
    from app.core.database import SessionLocal
    from uuid import UUID

    db = SessionLocal()

    try:
        # Converti job_id da stringa a UUID
        try:
            job_id_uuid = UUID(job_id)
        except (ValueError, AttributeError):
            db.close()
            return

        job = db.query(Job).filter(Job.id == job_id_uuid).first()

        if not job:
            db.close()
            return

        # Aggiorna status
        job.status = JobStatus.PROCESSING
        job.progress = 0
        job.message = "Inizio download video..."
        db.commit()

        # Determina output path
        if params.output_name:
            filename = params.output_name
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            ext = params.audio_format if params.extract_audio else params.format_preference
            filename = f"download_{timestamp}.{ext}"

        output_path = Path(settings.output_dir) / filename

        # Crea parametri download
        download_params = VideoDownloadParams(
            url=params.url,
            output_path=output_path,
            quality=params.quality,
            format_preference=params.format_preference,
            extract_audio=params.extract_audio,
            audio_format=params.audio_format,
            embed_thumbnail=params.embed_thumbnail,
            embed_metadata=params.embed_metadata,
            embed_subtitles=params.embed_subtitles,
            max_filesize=params.max_filesize_mb
        )

        # Callback progresso
        def progress_callback(progress: int, message: str) -> bool:
            job.progress = progress
            job.message = message
            db.commit()
            return True  # Continua

        # Download
        service = VideoDownloadService()
        result = service.download(download_params, progress_callback)

        # Aggiorna job
        job.status = JobStatus.COMPLETED
        job.progress = 100
        job.message = "Download completato!"
        job.result = result
        job.output_files = {"video": result['output_path']}
        db.commit()

    except Exception as e:
        job.status = JobStatus.FAILED
        job.error = str(e)
        job.message = f"Errore download: {e}"
        db.commit()
    finally:
        db.close()


# ==================== Routes ====================

@router.post("/download", response_model=VideoDownloadResponse, status_code=status.HTTP_202_ACCEPTED)
async def download_video(
    request: VideoDownloadRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Scarica video da URL (YouTube, TikTok, Vimeo, ecc.)

    **Piattaforme supportate:**
    - YouTube
    - TikTok
    - Vimeo
    - Twitter/X
    - Facebook
    - Instagram
    - Dailymotion
    - E 1000+ altri siti

    **Parametri:**
    - **url**: URL video da scaricare
    - **quality**: Qualità ("best", "worst", "720p", "1080p", "4k")
    - **format_preference**: Formato ("mp4", "webm", "mkv", "any")
    - **extract_audio**: true per scaricare solo audio
    - **audio_format**: Formato audio ("mp3", "m4a", "wav", "opus")

    **Esempi URL:**
    - https://www.youtube.com/watch?v=dQw4w9WgXcQ
    - https://vimeo.com/123456789
    - https://www.tiktok.com/@user/video/123456
    - https://twitter.com/user/status/123456

    Richiede JWT token. Download asincrono in background.
    """

    # Crea job
    job = create_download_job(current_user, request, db)

    # Avvia download in background
    background_tasks.add_task(process_download_task, str(job.id), request)

    return VideoDownloadResponse(
        job_id=str(job.id),
        status="accepted",
        message="Download avviato in background. Usa GET /jobs/{job_id} per monitorare.",
        url=request.url,
        progress=0
    )


@router.post("/info", response_model=VideoInfoResponse)
async def get_video_info(
    request: VideoInfoRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Ottieni informazioni video senza scaricarlo

    Utile per vedere titolo, durata, uploader, visualizzazioni, ecc.
    prima di scaricare.

    **Esempio:**
    ```json
    {
      "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    }
    ```

    Richiede JWT token. Risposta immediata (no background task).
    """

    try:
        service = VideoDownloadService()
        info = service.get_video_info(request.url)

        return VideoInfoResponse(**info)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Impossibile ottenere info video: {str(e)}"
        )


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
async def get_download_status(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Ottieni stato download video

    Monitora progresso download e ottieni path file quando completato.
    """
    from uuid import UUID

    # Converti job_id a UUID
    try:
        job_id_uuid = UUID(job_id)
    except (ValueError, AttributeError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Job ID non valido"
        )

    # Cerca job
    job = db.query(Job).filter(
        Job.id == job_id_uuid,
        Job.user_id == current_user.id
    ).first()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job non trovato"
        )

    # Costruisci risposta
    response = JobStatusResponse(
        job_id=str(job.id),
        status=job.status.value,
        progress=job.progress or 0,
        message=job.message,
        result=job.result,
        error=job.error
    )

    # Aggiungi output_path se completato
    if job.status == JobStatus.COMPLETED and job.output_files:
        response.output_path = job.output_files.get('video')

    return response
