"""
YouTube Routes
==============
Route per upload video su YouTube con OAuth2
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
from app.services.youtube_service import YouTubeService, YouTubeUploadParams

router = APIRouter()


# ==================== Pydantic Schemas ====================

class YouTubeUploadRequest(BaseModel):
    """Schema per richiesta upload YouTube"""
    video_path: str  # Path video da caricare
    title: str  # Titolo video (max 100 caratteri)
    description: str  # Descrizione (max 5000 caratteri)

    # Parametri opzionali
    tags: Optional[list[str]] = []  # Tags (max 500 caratteri totali)
    category_id: str = "22"  # Default: People & Blogs
    privacy_status: str = "private"  # "public", "private", "unlisted"
    thumbnail_path: Optional[str] = None  # Path thumbnail (opzionale)

    # Playlist
    playlist_id: Optional[str] = None  # Aggiungi a playlist esistente

    # Opzioni avanzate
    notify_subscribers: bool = False
    made_for_kids: bool = False


class YouTubeUploadResponse(BaseModel):
    """Schema per risposta upload YouTube"""
    job_id: str
    status: str
    message: str
    video_id: Optional[str] = None
    video_url: Optional[str] = None
    progress: int = 0


class YouTubeAuthURL(BaseModel):
    """URL per autenticazione OAuth2"""
    auth_url: str
    message: str


# ==================== Helper Functions ====================

def create_youtube_job(
    user: User,
    params: YouTubeUploadRequest,
    db: Session
) -> Job:
    """Crea job YouTube nel database"""
    job = Job(
        user_id=user.id,
        job_type=JobType.YOUTUBE_UPLOAD,
        status=JobStatus.PENDING,
        parameters=params.dict()
    )

    db.add(job)
    db.commit()
    db.refresh(job)

    return job


def process_youtube_upload_task(job_id: str, params: YouTubeUploadRequest, db: Session):
    """Task background per upload YouTube"""
    job = db.query(Job).filter(Job.id == job_id).first()

    if not job:
        return

    try:
        # Aggiorna status
        job.status = JobStatus.PROCESSING
        job.progress = 0
        db.commit()

        # Configura servizio
        service = YouTubeService(settings)

        # Prepara parametri
        upload_params = YouTubeUploadParams(
            video_path=Path(params.video_path),
            title=params.title,
            description=params.description,
            tags=params.tags,
            category_id=params.category_id,
            privacy_status=params.privacy_status,
            thumbnail_path=Path(params.thumbnail_path) if params.thumbnail_path else None,
            playlist_id=params.playlist_id,
            notify_subscribers=params.notify_subscribers,
            made_for_kids=params.made_for_kids
        )

        # Callback per aggiornare progresso
        def progress_callback(progress: int):
            job.progress = progress
            db.commit()

        # Upload video
        result = service.upload(upload_params, progress_callback)

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

@router.get("/auth", response_model=YouTubeAuthURL)
async def get_auth_url(
    current_user: User = Depends(get_current_user)
):
    """
    Ottieni URL per autenticazione YouTube OAuth2

    Passaggi:
    1. Chiama questo endpoint per ottenere auth_url
    2. Apri auth_url nel browser
    3. Autorizza l'applicazione
    4. Verrai rediretto a redirect_uri con codice
    5. Usa POST /youtube/callback con il codice

    Richiede JWT token.
    """
    service = YouTubeService(settings)
    auth_url = service.get_auth_url()

    return {
        "auth_url": auth_url,
        "message": "Apri questo URL nel browser e autorizza l'applicazione"
    }


@router.post("/callback")
async def oauth_callback(
    code: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Callback OAuth2 - Salva credenziali YouTube

    - **code**: Codice OAuth2 ottenuto dal redirect

    Dopo aver autorizzato su auth_url, YouTube ti redirige con un codice.
    Invia quel codice a questo endpoint per salvare le credenziali.

    Richiede JWT token.
    """
    service = YouTubeService(settings)

    try:
        # Scambia codice con token
        credentials = service.exchange_code_for_token(code)

        # Salva credenziali per l'utente (in produzione, salvare in database)
        # Per ora, salvare in file temporaneo per l'utente
        credentials_file = settings.temp_dir / f"youtube_credentials_{current_user.id}.json"
        with open(credentials_file, 'w') as f:
            f.write(credentials.to_json())

        return {
            "status": "success",
            "message": "Autenticazione YouTube completata. Puoi ora caricare video."
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Errore autenticazione: {str(e)}"
        )


@router.post("/upload", response_model=YouTubeUploadResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_video(
    request: YouTubeUploadRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Carica video su YouTube

    - **video_path**: Path video da caricare
    - **title**: Titolo (max 100 caratteri)
    - **description**: Descrizione (max 5000 caratteri)
    - **tags**: Lista tags (opzionale)
    - **category_id**: ID categoria YouTube (default: "22" = People & Blogs)
    - **privacy_status**: "public", "private", "unlisted" (default: "private")
    - **thumbnail_path**: Path thumbnail custom (opzionale)
    - **playlist_id**: Aggiungi a playlist (opzionale)
    - **notify_subscribers**: Notifica iscritti (default: false)
    - **made_for_kids**: Video per bambini (default: false)

    **Note**:
    - Devi prima autenticare con GET /auth e POST /callback
    - Upload asincrono in background
    - Riceverai video_id e video_url quando completato

    Richiede JWT token. Elaborazione asincrona in background.
    """
    # Verifica credenziali YouTube esistenti
    credentials_file = settings.temp_dir / f"youtube_credentials_{current_user.id}.json"
    if not credentials_file.exists():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Autenticazione YouTube richiesta. Usa GET /auth per iniziare."
        )

    # Validazioni
    if len(request.title) > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Titolo max 100 caratteri"
        )

    if len(request.description) > 5000:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Descrizione max 5000 caratteri"
        )

    # Crea job
    job = create_youtube_job(current_user, request, db)

    # Avvia task in background
    background_tasks.add_task(process_youtube_upload_task, str(job.id), request, db)

    return {
        "job_id": str(job.id),
        "status": "accepted",
        "message": "Job upload YouTube avviato. Usa GET /jobs/{job_id} per monitorare progresso.",
        "progress": 0
    }


@router.post("/upload-file", response_model=YouTubeUploadResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_file_to_youtube(
    video: UploadFile = File(..., description="Video da caricare"),
    title: str = Form(..., max_length=100),
    description: str = Form(..., max_length=5000),
    tags: Optional[str] = Form(None, description="Tags separati da virgola"),
    category_id: str = Form("22"),
    privacy_status: str = Form("private"),
    notify_subscribers: bool = Form(False),
    made_for_kids: bool = Form(False),
    thumbnail: Optional[UploadFile] = File(None, description="Thumbnail opzionale"),
    background_tasks: BackgroundTasks = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Upload file e carica su YouTube in un'unica chiamata

    Upload video (e opzionalmente thumbnail), poi carica su YouTube.

    Richiede JWT token e autenticazione YouTube. Elaborazione asincrona.
    """
    # Verifica credenziali YouTube
    credentials_file = settings.temp_dir / f"youtube_credentials_{current_user.id}.json"
    if not credentials_file.exists():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Autenticazione YouTube richiesta."
        )

    # Salva video
    video_path = settings.upload_dir / f"yt_{current_user.id}_{video.filename}"
    with open(video_path, "wb") as f:
        content = await video.read()
        f.write(content)

    # Salva thumbnail se presente
    thumbnail_path = None
    if thumbnail:
        thumbnail_path = settings.upload_dir / f"yt_thumb_{current_user.id}_{thumbnail.filename}"
        with open(thumbnail_path, "wb") as f:
            content = await thumbnail.read()
            f.write(content)

    # Parse tags
    tags_list = [tag.strip() for tag in tags.split(",")] if tags else []

    # Crea request
    request = YouTubeUploadRequest(
        video_path=str(video_path),
        title=title,
        description=description,
        tags=tags_list,
        category_id=category_id,
        privacy_status=privacy_status,
        thumbnail_path=str(thumbnail_path) if thumbnail_path else None,
        notify_subscribers=notify_subscribers,
        made_for_kids=made_for_kids
    )

    # Crea job
    job = create_youtube_job(current_user, request, db)

    # Avvia task in background
    background_tasks.add_task(process_youtube_upload_task, str(job.id), request, db)

    return {
        "job_id": str(job.id),
        "status": "accepted",
        "message": "File caricati. Job upload YouTube avviato.",
        "progress": 0
    }


@router.get("/jobs/{job_id}", response_model=YouTubeUploadResponse)
async def get_job_status(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Ottieni status job upload YouTube

    - **job_id**: ID del job

    Richiede JWT token. Puoi vedere solo i tuoi job.
    """
    job = db.query(Job).filter(
        Job.id == job_id,
        Job.user_id == current_user.id,
        Job.job_type == JobType.YOUTUBE_UPLOAD
    ).first()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job non trovato"
        )

    # Estrai video_id e costruisci URL
    video_id = None
    video_url = None
    if job.status == JobStatus.COMPLETED and job.result:
        video_id = job.result.get("video_id")
        if video_id:
            video_url = f"https://www.youtube.com/watch?v={video_id}"

    return {
        "job_id": str(job.id),
        "status": job.status.value,
        "message": job.error or "Job in elaborazione" if job.status == JobStatus.PROCESSING else "Job completato",
        "video_id": video_id,
        "video_url": video_url,
        "progress": job.progress
    }
