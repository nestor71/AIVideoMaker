"""
Logo Overlay Routes
===================
Route per sovrapposizione logo/watermark su video
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
from app.services.logo_overlay_service import LogoOverlayService, LogoOverlayParams

router = APIRouter()


# ==================== Pydantic Schemas ====================

class LogoOverlayRequest(BaseModel):
    """Schema per richiesta overlay logo"""
    video_path: str  # Path video
    logo_path: str  # Path logo (PNG con trasparenza preferito)
    output_name: Optional[str] = "logo_output.mp4"

    # Parametri posizionamento
    position: str = "bottom-right"  # top-left, top-right, bottom-left, bottom-right, center, custom
    custom_x: Optional[int] = None  # Se position=custom
    custom_y: Optional[int] = None  # Se position=custom
    margin: int = 20  # Margine dai bordi (pixel)

    # Parametri logo
    logo_scale: float = 0.15  # Scala logo (0.0-1.0, relativo a larghezza video)
    opacity: float = 1.0  # Opacità (0.0-1.0)

    # Parametri temporali
    start_time: Optional[float] = None  # Secondi dall'inizio (None = tutto il video)
    end_time: Optional[float] = None  # Secondi dall'inizio (None = fino alla fine)

    # Parametri video
    quality: str = "high"  # low, medium, high, ultra


class LogoOverlayResponse(BaseModel):
    """Schema per risposta overlay logo"""
    job_id: str
    status: str
    message: str
    output_path: Optional[str] = None
    progress: int = 0
    error: Optional[str] = None


# ==================== Helper Functions ====================

def create_logo_job(
    user: User,
    params: LogoOverlayRequest,
    db: Session
) -> Job:
    """Crea job overlay logo nel database"""
    job = Job(
        user_id=user.id,
        job_type=JobType.LOGO_OVERLAY,
        status=JobStatus.PENDING,
        parameters=params.dict()
    )

    db.add(job)
    db.commit()
    db.refresh(job)

    return job


def process_logo_task(job_id: str, params: LogoOverlayRequest):
    """Task background per overlay logo"""
    # Crea nuova session per il background task (thread-safe)
    from app.core.database import SessionLocal
    db = SessionLocal()

    try:
        job = db.query(Job).filter(Job.id == job_id).first()

        if not job:
            db.close()
            return

        # Aggiorna status
        job.status = JobStatus.PROCESSING
        job.progress = 0
        db.commit()

        # Configura servizio
        service = LogoOverlayService(settings)

        # Prepara parametri
        logo_params = LogoOverlayParams(
            video_path=Path(params.video_path),
            logo_path=Path(params.logo_path),
            output_path=settings.output_dir / params.output_name,
            position=params.position,
            custom_x=params.custom_x,
            custom_y=params.custom_y,
            margin=params.margin,
            logo_scale=params.logo_scale,
            opacity=params.opacity,
            start_time=params.start_time,
            end_time=params.end_time
            # quality non implementato nel servizio
        )

        # Callback per aggiornare progresso
        def progress_callback(progress: int, message: str):
            job.progress = progress
            db.commit()

        # Esegui overlay
        result = service.overlay(logo_params, progress_callback)

        # Aggiorna job
        job.status = JobStatus.COMPLETED
        job.progress = 100
        job.result = result
        db.commit()

    except Exception as e:
        job.status = JobStatus.FAILED
        job.error = str(e)
        db.commit()
    finally:
        db.close()


# ==================== Routes ====================

@router.post("/overlay", response_model=LogoOverlayResponse, status_code=status.HTTP_202_ACCEPTED)
async def overlay_logo(
    request: LogoOverlayRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Sovrapponi logo/watermark su video

    - **video_path**: Path video
    - **logo_path**: Path logo (PNG con trasparenza consigliato)
    - **output_name**: Nome file output (default: logo_output.mp4)
    - **position**: Posizione logo ("top-left", "top-right", "bottom-left", "bottom-right", "center", "custom")
    - **custom_x/custom_y**: Coordinate custom se position="custom"
    - **margin**: Margine dai bordi in pixel (default: 20)
    - **logo_scale**: Scala logo relativa a larghezza video (0.0-1.0, default: 0.15)
    - **opacity**: Opacità logo (0.0-1.0, default: 1.0)
    - **start_time**: Tempo inizio overlay in secondi (None = inizio video)
    - **end_time**: Tempo fine overlay in secondi (None = fine video)
    - **quality**: Qualità output ("low", "medium", "high", "ultra")

    Posizioni disponibili:
    - **top-left**: Angolo alto sinistra
    - **top-right**: Angolo alto destra
    - **bottom-left**: Angolo basso sinistra
    - **bottom-right**: Angolo basso destra (default)
    - **center**: Centro video
    - **custom**: Posizione personalizzata (richiede custom_x e custom_y)

    Richiede JWT token. Elaborazione asincrona in background.
    """
    # Valida posizione
    if request.position not in LogoOverlayService.POSITIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Posizione non valida. Disponibili: {LogoOverlayService.POSITIONS}"
        )

    # Valida custom position
    if request.position == "custom" and (request.custom_x is None or request.custom_y is None):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Posizione 'custom' richiede custom_x e custom_y"
        )

    # Valida scale e opacity
    if not 0.0 <= request.logo_scale <= 1.0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="logo_scale deve essere tra 0.0 e 1.0"
        )

    if not 0.0 <= request.opacity <= 1.0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="opacity deve essere tra 0.0 e 1.0"
        )

    # Crea job
    job = create_logo_job(current_user, request, db)

    # Avvia task in background (session creata internamente)
    background_tasks.add_task(process_logo_task, str(job.id), request)

    return {
        "job_id": str(job.id),
        "status": "accepted",
        "message": "Job overlay logo avviato. Usa GET /jobs/{job_id} per monitorare progresso.",
        "progress": 0
    }


@router.post("/upload", response_model=LogoOverlayResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_and_overlay(
    video: UploadFile = File(..., description="Video su cui applicare logo"),
    logo: UploadFile = File(..., description="Logo/watermark (PNG consigliato)"),
    output_name: str = Form("logo_output.mp4"),
    position: str = Form("bottom-right"),
    margin: int = Form(20),
    logo_scale: float = Form(0.15),
    opacity: float = Form(1.0),
    quality: str = Form("high"),
    background_tasks: BackgroundTasks = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Upload video e logo, poi applica overlay

    Upload di video e logo in un'unica chiamata, poi elabora overlay.

    Richiede JWT token. Elaborazione asincrona in background.
    """
    # Salva file upload
    video_path = settings.upload_dir / f"video_{current_user.id}_{video.filename}"
    logo_path = settings.upload_dir / f"logo_{current_user.id}_{logo.filename}"

    # Scrivi video
    with open(video_path, "wb") as f:
        content = await video.read()
        f.write(content)

    # Scrivi logo
    with open(logo_path, "wb") as f:
        content = await logo.read()
        f.write(content)

    # Crea request
    request = LogoOverlayRequest(
        video_path=str(video_path),
        logo_path=str(logo_path),
        output_name=output_name,
        position=position,
        margin=margin,
        logo_scale=logo_scale,
        opacity=opacity,
        quality=quality
    )

    # Crea job
    job = create_logo_job(current_user, request, db)

    # Avvia task in background (session creata internamente)
    background_tasks.add_task(process_logo_task, str(job.id), request)

    return {
        "job_id": str(job.id),
        "status": "accepted",
        "message": "File caricati. Job overlay logo avviato.",
        "progress": 0
    }


@router.get("/jobs/{job_id}", response_model=LogoOverlayResponse)
async def get_job_status(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Ottieni status job overlay logo

    - **job_id**: ID del job

    Richiede JWT token. Puoi vedere solo i tuoi job.
    """
    job = db.query(Job).filter(
        Job.id == job_id,
        Job.user_id == current_user.id,
        Job.job_type == JobType.LOGO_OVERLAY
    ).first()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job non trovato"
        )

    return {
        "job_id": str(job.id),
        "status": job.status.value,
        "message": job.error if job.status == JobStatus.FAILED else ("Job in elaborazione" if job.status == JobStatus.PROCESSING else "Job completato"),
        "output_path": job.result.get("output_path") if job.result else None,
        "progress": job.progress,
        "error": job.error
    }
