"""
Chromakey Routes
================
Route per elaborazione chromakey (green screen)
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
from app.services.chromakey_service import ChromakeyService, ChromakeyParams

router = APIRouter()


# ==================== Pydantic Schemas ====================

class ChromakeyRequest(BaseModel):
    """Schema per richiesta chromakey"""
    foreground_video: str  # Path o URL
    background_video: str  # Path o URL
    output_name: Optional[str] = "chromakey_output.mp4"

    # Parametri opzionali chromakey
    start_time: float = 0.0
    end_time: Optional[float] = None
    audio_mode: str = "synced"  # "synced", "foreground", "background", "none"

    # Parametri posizionamento e dimensioni
    position_x: int = 0  # Offset orizzontale dal centro (pixel, negativo = sinistra, positivo = destra)
    position_y: int = 0  # Offset verticale dal centro (pixel, negativo = alto, positivo = basso)
    scale: float = 1.0  # Scala foreground (0.1 = 10%, 1.0 = 100%, 2.0 = 200%)
    opacity: float = 1.0  # Opacità foreground (0.0 = trasparente, 1.0 = opaco)

    # Parametri green screen
    green_threshold: int = 100
    tolerance: int = 50
    edge_blur: int = 5
    spill_reduction: float = 0.5

    # Parametri video
    fps: Optional[int] = None
    resolution: Optional[tuple[int, int]] = None
    quality: str = "high"  # "low", "medium", "high", "ultra"


class ChromakeyResponse(BaseModel):
    """Schema per risposta chromakey"""
    job_id: str
    status: str
    message: str
    output_path: Optional[str] = None
    progress: int = 0
    error: Optional[str] = None


class ChromakeyJobListItem(BaseModel):
    """Schema per singolo job nella lista"""
    job_id: str
    status: str
    progress: int
    created_at: str
    updated_at: str
    output_path: Optional[str] = None
    error: Optional[str] = None


class ChromakeyJobListResponse(BaseModel):
    """Schema per risposta lista job"""
    jobs: list[ChromakeyJobListItem]
    total: int
    page: int
    page_size: int
    has_more: bool


# ==================== Helper Functions ====================

def create_chromakey_job(
    user: User,
    params: ChromakeyRequest,
    db: Session
) -> Job:
    """Crea job chromakey nel database"""
    job = Job(
        user_id=user.id,
        job_type=JobType.CHROMAKEY,
        status=JobStatus.PENDING,
        parameters=params.dict()
    )

    db.add(job)
    db.commit()
    db.refresh(job)

    return job


def process_chromakey_task(job_id: str, params: ChromakeyRequest):
    """Task background per elaborazione chromakey"""
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
        service = ChromakeyService(settings)

        # Prepara parametri (solo quelli supportati da ChromakeyParams)
        chromakey_params = ChromakeyParams(
            foreground_path=Path(params.foreground_video),
            background_path=Path(params.background_video),
            output_path=settings.output_dir / params.output_name,
            start_time=params.start_time,
            duration=(params.end_time - params.start_time) if params.end_time else None,
            audio_mode=params.audio_mode,
            position=(params.position_x, params.position_y),
            scale=params.scale,
            opacity=params.opacity
            # Altri parametri (green_threshold, etc) non ancora implementati nel servizio
        )

        # Callback per aggiornare progresso
        def progress_callback(progress: int, message: str):
            job.progress = progress
            db.commit()
            return True  # Continue processing

        # Esegui chromakey
        result = service.process(chromakey_params, progress_callback)

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

@router.post("/process", response_model=ChromakeyResponse, status_code=status.HTTP_202_ACCEPTED)
async def process_chromakey(
    request: ChromakeyRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Elabora video con chromakey (green screen)

    - **foreground_video**: Path video con green screen
    - **background_video**: Path video sfondo
    - **output_name**: Nome file output (default: chromakey_output.mp4)
    - **audio_mode**: Modalità audio ("synced", "foreground", "background", "none")
    - **green_threshold**: Soglia verde (0-255, default: 100)
    - **tolerance**: Tolleranza colore (0-255, default: 50)
    - **edge_blur**: Blur bordi (0-20, default: 5)
    - **spill_reduction**: Riduzione spill verde (0.0-1.0, default: 0.5)
    - **quality**: Qualità output ("low", "medium", "high", "ultra")

    Richiede JWT token. Elaborazione asincrona in background.
    """
    # Crea job
    job = create_chromakey_job(current_user, request, db)

    # Avvia task in background
    # Avvia task in background (session creata internamente)
    background_tasks.add_task(process_chromakey_task, str(job.id), request)

    return {
        "job_id": str(job.id),
        "status": "accepted",
        "message": "Job chromakey avviato. Usa GET /jobs/{job_id} per monitorare progresso.",
        "progress": 0
    }


@router.post("/upload", response_model=ChromakeyResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_and_process(
    foreground: UploadFile = File(..., description="Video con green screen"),
    background: UploadFile = File(..., description="Video sfondo"),
    output_name: str = Form("chromakey_output.mp4"),
    audio_mode: str = Form("synced"),
    # Parametri posizionamento e dimensioni
    position_x: int = Form(0, description="Offset orizzontale dal centro (px, negativo=sinistra, positivo=destra)"),
    position_y: int = Form(0, description="Offset verticale dal centro (px, negativo=alto, positivo=basso)"),
    scale: float = Form(1.0, description="Scala foreground (0.1=10%, 1.0=100%, 2.0=200%)"),
    opacity: float = Form(1.0, description="Opacità foreground (0.0=trasparente, 1.0=opaco)"),
    # Parametri green screen
    green_threshold: int = Form(100),
    tolerance: int = Form(50),
    edge_blur: int = Form(5),
    spill_reduction: float = Form(0.5, description="Riduzione riflessi verdi (0.0-1.0)"),
    # Parametri temporali
    start_time: float = Form(0.0, description="Inizio clip in secondi"),
    end_time: Optional[float] = Form(None, description="Fine clip in secondi (null=tutto il video)"),
    # Parametri video
    quality: str = Form("high"),
    background_tasks: BackgroundTasks = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Upload e elaborazione chromakey in un'unica chiamata

    Upload di foreground (green screen) e background, poi elabora chromakey.

    **Parametri posizionamento:**
    - position_x: Offset orizzontale (0=centro, negativo=sinistra, positivo=destra)
    - position_y: Offset verticale (0=centro, negativo=alto, positivo=basso)
    - scale: Scala del foreground (0.5=50%, 1.0=100%, 2.0=200%)
    - opacity: Opacità (0.0=trasparente, 1.0=opaco)

    **Parametri temporali:**
    - start_time: Inizio clip in secondi
    - end_time: Fine clip in secondi (null=tutto il video)

    Richiede JWT token. Elaborazione asincrona in background.
    """
    # Salva file upload
    foreground_path = settings.upload_dir / f"fg_{current_user.id}_{foreground.filename}"
    background_path = settings.upload_dir / f"bg_{current_user.id}_{background.filename}"

    # Scrivi file
    with open(foreground_path, "wb") as f:
        content = await foreground.read()
        f.write(content)

    with open(background_path, "wb") as f:
        content = await background.read()
        f.write(content)

    # Crea request con tutti i parametri
    request = ChromakeyRequest(
        foreground_video=str(foreground_path),
        background_video=str(background_path),
        output_name=output_name,
        audio_mode=audio_mode,
        position_x=position_x,
        position_y=position_y,
        scale=scale,
        opacity=opacity,
        green_threshold=green_threshold,
        tolerance=tolerance,
        edge_blur=edge_blur,
        spill_reduction=spill_reduction,
        start_time=start_time,
        end_time=end_time,
        quality=quality
    )

    # Crea job
    job = create_chromakey_job(current_user, request, db)

    # Avvia task in background
    # Avvia task in background (session creata internamente)
    background_tasks.add_task(process_chromakey_task, str(job.id), request)

    return {
        "job_id": str(job.id),
        "status": "accepted",
        "message": "File caricati. Job chromakey avviato.",
        "progress": 0
    }


@router.get("/jobs/{job_id}", response_model=ChromakeyResponse)
async def get_job_status(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Ottieni status job chromakey

    - **job_id**: ID del job

    Richiede JWT token. Puoi vedere solo i tuoi job.
    """
    job = db.query(Job).filter(
        Job.id == job_id,
        Job.user_id == current_user.id,
        Job.job_type == JobType.CHROMAKEY
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


@router.get("/jobs", response_model=ChromakeyJobListResponse)
async def list_chromakey_jobs(
    status: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Lista job chromakey dell'utente corrente

    - **status**: Filtra per status ("pending", "processing", "completed", "failed")
    - **page**: Numero pagina (default: 1)
    - **page_size**: Elementi per pagina (default: 20, max: 100)

    Richiede JWT token. Restituisce solo i job dell'utente corrente.
    """
    # Validazione page_size
    if page_size > 100:
        page_size = 100
    if page_size < 1:
        page_size = 1
    if page < 1:
        page = 1

    # Query base
    query = db.query(Job).filter(
        Job.user_id == current_user.id,
        Job.job_type == JobType.CHROMAKEY
    )

    # Filtro status
    if status:
        try:
            status_enum = JobStatus(status)
            query = query.filter(Job.status == status_enum)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Status non valido. Valori accettati: pending, processing, completed, failed"
            )

    # Count totale
    total = query.count()

    # Paginazione e ordinamento (più recenti prima)
    jobs = query.order_by(Job.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

    # Formatta risultati
    job_list = []
    for job in jobs:
        job_list.append({
            "job_id": str(job.id),
            "status": job.status.value,
            "progress": job.progress,
            "created_at": job.created_at.isoformat() if job.created_at else None,
            "updated_at": job.updated_at.isoformat() if job.updated_at else None,
            "output_path": job.result.get("output_path") if job.result else None,
            "error": job.error
        })

    return {
        "jobs": job_list,
        "total": total,
        "page": page,
        "page_size": page_size,
        "has_more": total > (page * page_size)
    }


@router.delete("/jobs/{job_id}")
async def delete_chromakey_job(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Cancella un job chromakey

    - **job_id**: ID del job da cancellare

    Richiede JWT token. Puoi cancellare solo i tuoi job.
    NOTA: Non cancella i file fisici, solo il record nel database.
    """
    job = db.query(Job).filter(
        Job.id == job_id,
        Job.user_id == current_user.id,
        Job.job_type == JobType.CHROMAKEY
    ).first()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job non trovato"
        )

    # Non permettere cancellazione job in processing
    if job.status == JobStatus.PROCESSING:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Impossibile cancellare job in elaborazione. Attendere completamento."
        )

    db.delete(job)
    db.commit()

    return {
        "message": "Job cancellato con successo",
        "job_id": str(job_id)
    }
