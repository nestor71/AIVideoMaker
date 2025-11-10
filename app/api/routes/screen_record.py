"""
Screen Recording Routes
=======================
Route per registrazione schermo/finestra/area
"""

from pathlib import Path
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.config import settings
from app.core.usage_tracker import track_action
from app.models.user import User
from app.models.job import Job, JobType, JobStatus
from app.services.screen_record_service import ScreenRecordService, ScreenRecordParams

router = APIRouter()


# ==================== Pydantic Schemas ====================

class ScreenRecordRequest(BaseModel):
    """Schema per richiesta registrazione schermo"""
    output_name: Optional[str] = "screen_recording.mp4"

    # Modalità registrazione
    mode: str = "fullscreen"  # fullscreen, window, area
    window_title: Optional[str] = None  # Se mode=window (es. "Firefox")

    # Area personalizzata (se mode=area)
    area_x: Optional[int] = None
    area_y: Optional[int] = None
    area_width: Optional[int] = None
    area_height: Optional[int] = None

    # Parametri registrazione
    duration_seconds: int = 10  # Durata registrazione (REQUIRED)
    fps: int = 30  # Frame per secondo
    quality: str = "high"  # low, medium, high, ultra
    record_audio: bool = True  # Registra audio di sistema


class ScreenRecordResponse(BaseModel):
    """Schema per risposta registrazione schermo"""
    job_id: str
    status: str
    message: str
    output_path: Optional[str] = None
    progress: int = 0
    duration_seconds: Optional[int] = None


# ==================== Helper Functions ====================

def create_screen_record_job(
    user: User,
    params: ScreenRecordRequest,
    db: Session
) -> Job:
    """Crea job registrazione schermo nel database"""
    job = Job(
        user_id=user.id,
        job_type=JobType.SCREEN_RECORD,
        status=JobStatus.PENDING,
        parameters=params.dict()
    )

    db.add(job)
    db.commit()
    db.refresh(job)

    return job


def process_screen_record_task(job_id: str, params: ScreenRecordRequest, db: Session):
    """Task background per registrazione schermo"""
    job = db.query(Job).filter(Job.id == job_id).first()

    if not job:
        return

    try:
        # Aggiorna status
        job.status = JobStatus.PROCESSING
        job.progress = 0
        db.commit()

        # Configura servizio
        service = ScreenRecordService(settings)

        # Prepara parametri
        record_params = ScreenRecordParams(
            output_path=settings.output_dir / params.output_name,
            mode=params.mode,
            window_title=params.window_title,
            area_x=params.area_x,
            area_y=params.area_y,
            area_width=params.area_width,
            area_height=params.area_height,
            duration_seconds=params.duration_seconds,
            fps=params.fps,
            quality=params.quality,
            record_audio=params.record_audio
        )

        # Callback per aggiornare progresso
        def progress_callback(progress: int, message: str):
            job.progress = progress
            db.commit()

        # Esegui registrazione
        result = service.record(record_params, progress_callback)

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

@router.post("/record", response_model=ScreenRecordResponse, status_code=status.HTTP_202_ACCEPTED)
async def record_screen(
    request: ScreenRecordRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Registra schermo/finestra/area

    - **output_name**: Nome file output (default: screen_recording.mp4)
    - **mode**: Modalità ("fullscreen", "window", "area")
    - **window_title**: Titolo finestra se mode=window (es. "Firefox", "Chrome")
    - **area_x/area_y/area_width/area_height**: Coordinate area se mode=area
    - **duration_seconds**: Durata registrazione in secondi (REQUIRED)
    - **fps**: Frame rate (default: 30)
    - **quality**: Qualità output ("low", "medium", "high", "ultra")
    - **record_audio**: Registra audio sistema (default: True)

    Modalità disponibili:
    - **fullscreen**: Registra tutto lo schermo
    - **window**: Registra finestra specifica (richiede window_title)
    - **area**: Registra area personalizzata (richiede area_x, area_y, area_width, area_height)

    Qualità:
    - **low**: CRF 28, preset ultrafast (file piccolo, qualità base)
    - **medium**: CRF 23, preset fast (bilanciato)
    - **high**: CRF 18, preset medium (qualità alta, default)
    - **ultra**: CRF 15, preset slow (qualità massima, file grande)

    Platform support:
    - **Linux**: X11 (Xorg), richiede ffmpeg con x11grab
    - **macOS**: AVFoundation
    - **Windows**: GDI/DirectShow

    IMPORTANTE: La registrazione inizia immediatamente e dura esattamente duration_seconds.
    Non è possibile fermare manualmente la registrazione una volta avviata.

    Richiede JWT token. Elaborazione asincrona in background.
    """
    # Valida modalità
    if request.mode not in ScreenRecordService.MODES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Modalità non valida. Disponibili: {ScreenRecordService.MODES}"
        )

    # Valida window mode
    if request.mode == "window" and not request.window_title:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Modalità 'window' richiede window_title"
        )

    # Valida area mode
    if request.mode == "area":
        if any(p is None for p in [request.area_x, request.area_y, request.area_width, request.area_height]):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Modalità 'area' richiede area_x, area_y, area_width, area_height"
            )

    # Valida duration
    if request.duration_seconds <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="duration_seconds deve essere maggiore di 0"
        )

    if request.duration_seconds > 3600:  # Max 1 ora
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="duration_seconds non può superare 3600 (1 ora)"
        )

    # Valida FPS
    if not 1 <= request.fps <= 120:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="fps deve essere tra 1 e 120"
        )

    # Valida quality
    if request.quality not in ScreenRecordService.QUALITY_PRESETS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Qualità non valida. Disponibili: {list(ScreenRecordService.QUALITY_PRESETS.keys())}"
        )

    # Crea job
    job = create_screen_record_job(current_user, request, db)

    # Avvia task in background
    background_tasks.add_task(process_screen_record_task, str(job.id), request, db)

    return {
        "job_id": str(job.id),
        "status": "accepted",
        "message": f"Registrazione schermo avviata ({request.duration_seconds}s). Usa GET /jobs/{{job_id}} per monitorare progresso.",
        "progress": 0,
        "duration_seconds": request.duration_seconds
    }


@router.get("/jobs/{job_id}", response_model=ScreenRecordResponse)
async def get_job_status(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Ottieni status job registrazione schermo

    - **job_id**: ID del job

    Richiede JWT token. Puoi vedere solo i tuoi job.
    """
    job = db.query(Job).filter(
        Job.id == job_id,
        Job.user_id == current_user.id,
        Job.job_type == JobType.SCREEN_RECORD
    ).first()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job non trovato"
        )

    # Recupera duration dai parametri
    duration = job.parameters.get("duration_seconds") if job.parameters else None

    return {
        "job_id": str(job.id),
        "status": job.status.value,
        "message": job.error_message or "Registrazione in corso..." if job.status == JobStatus.PROCESSING else "Registrazione completata",
        "output_path": job.result.get("output_path") if job.result else None,
        "progress": job.progress,
        "duration_seconds": duration
    }


@router.get("/windows")
async def list_windows(
    current_user: User = Depends(get_current_user)
):
    """
    Lista finestre disponibili per registrazione

    Utile per ottenere i titoli delle finestre da usare con mode=window.

    Richiede JWT token.

    Platform support:
    - **Linux**: wmctrl (deve essere installato: apt install wmctrl)
    - **macOS**: PyGetWindow o AppleScript
    - **Windows**: PyGetWindow

    Se il sistema non supporta il listing, ritorna lista vuota.
    """
    try:
        service = ScreenRecordService(settings)
        windows = service.list_available_windows()

        return {
            "windows": windows,
            "count": len(windows)
        }
    except Exception as e:
        return {
            "windows": [],
            "count": 0,
            "message": f"Impossibile listare finestre: {str(e)}"
        }
