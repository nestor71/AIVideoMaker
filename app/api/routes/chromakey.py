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
import subprocess
import signal
import logging

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.config import settings
from app.core.usage_tracker import track_action
from app.models.user import User
from app.models.job import Job, JobType, JobStatus
from app.services.chromakey_service import ChromakeyService, ChromakeyParams

router = APIRouter()
logger = logging.getLogger(__name__)


# ==================== Pydantic Schemas ====================

class ChromakeyRequest(BaseModel):
    """Schema per richiesta chromakey"""
    foreground_video: str  # Path o URL
    background_video: str  # Path o URL
    output_name: Optional[str] = "chromakey_output.mp4"

    # Parametri temporali
    start_time: float = 0.0
    end_time: Optional[float] = None
    audio_mode: str = "synced"  # "synced", "foreground", "background", "both", "timed", "none"

    # Parametri posizionamento e dimensioni
    position_x: int = 0  # Offset orizzontale dal centro (pixel, negativo = sinistra, positivo = destra)
    position_y: int = 0  # Offset verticale dal centro (pixel, negativo = alto, positivo = basso)
    scale: float = 1.0  # Scala foreground (0.1 = 10%, 1.0 = 100%, 2.0 = 200%)
    opacity: float = 1.0  # Opacità foreground (0.0 = trasparente, 1.0 = opaco)

    # Parametri chromakey (selezione colore)
    chroma_color: str = "green"  # "green", "blue", "custom"
    # Per chroma_color="custom", specifica range HSV personalizzato
    # Valori standard chromakey
    custom_lower_h: int = 63   # Hue min (0-180)
    custom_lower_s: int = 40   # Saturation min (0-255)
    custom_lower_v: int = 40   # Value min (0-255)
    custom_upper_h: int = 93   # Hue max (0-180)
    custom_upper_s: int = 255  # Saturation max (0-255)
    custom_upper_v: int = 255  # Value max (0-255)
    blur_kernel: int = 5       # Kernel blur maschera (3, 5, 7, 9...)


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

def get_chromakey_hsv_ranges(params: ChromakeyRequest):
    """
    Converte parametri colore in range HSV per chromakey

    Returns:
        tuple: (lower_hsv, upper_hsv, blur_kernel)
    """
    import numpy as np

    if params.chroma_color == "green":
        # Verde standard ottimizzato
        # Range HSV: [155-30, 155+30] = [125, 185] in scala 0-360
        # In OpenCV (0-180): [62.5, 92.5] -> arrotondiamo a [63, 93]
        lower_hsv = (63, 40, 40)   # Valori standard chromakey
        upper_hsv = (93, 255, 255)
    elif params.chroma_color == "blue":
        # Blu standard: Soglia 220, Tolleranza 50
        # Range: [170-270] in 0-360 = [85-135] in OpenCV
        lower_hsv = (85, 40, 40)
        upper_hsv = (135, 255, 255)
    elif params.chroma_color == "custom":
        # Range personalizzato
        lower_hsv = (params.custom_lower_h, params.custom_lower_s, params.custom_lower_v)
        upper_hsv = (params.custom_upper_h, params.custom_upper_s, params.custom_upper_v)
    else:
        # Default verde standard
        lower_hsv = (63, 40, 40)
        upper_hsv = (93, 255, 255)

    return lower_hsv, upper_hsv, params.blur_kernel


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

        # Ottieni range HSV in base al colore scelto
        lower_hsv, upper_hsv, blur_kernel = get_chromakey_hsv_ranges(params)

        # Prepara parametri per chromakey service
        chromakey_params = ChromakeyParams(
            foreground_path=Path(params.foreground_video),
            background_path=Path(params.background_video),
            output_path=settings.output_dir / params.output_name,
            start_time=params.start_time,
            duration=(params.end_time - params.start_time) if params.end_time else None,
            audio_mode=params.audio_mode,
            position=(params.position_x, params.position_y),
            scale=params.scale,
            opacity=params.opacity,
            lower_hsv=lower_hsv,
            upper_hsv=upper_hsv,
            blur_kernel=blur_kernel
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

    **Parametri video:**
    - **foreground_video**: Path video con green screen
    - **background_video**: Path video sfondo
    - **output_name**: Nome file output (default: chromakey_output.mp4)

    **Parametri temporali:**
    - **start_time**: Inizio sovrapposizione in secondi (default: 0.0)
    - **end_time**: Fine sovrapposizione in secondi (null = fino alla fine)

    **Parametri audio:**
    - **audio_mode**: Modalità audio (default: "synced")
      - "synced": Mix audio foreground e background sincronizzato
      - "background": Solo audio background
      - "foreground": Solo audio foreground
      - "both": Mix audio foreground e background
      - "timed": Mix con timing preciso
      - "none": Nessun audio

    **Parametri posizionamento:**
    - **position_x**: Offset orizzontale dal centro in pixel (0=centro, negativo=sinistra, positivo=destra)
    - **position_y**: Offset verticale dal centro in pixel (0=centro, negativo=alto, positivo=basso)
    - **scale**: Scala foreground (0.1=10%, 1.0=100%, 2.0=200%)
    - **opacity**: Opacità foreground (0.0=trasparente, 1.0=opaco)

    **Parametri chromakey:**
    - **chroma_color**: Colore da rimuovere (default: "green")
      - "green": Verde standard (green screen)
      - "blue": Blu standard (blue screen)
      - "custom": Range HSV personalizzato
    - **custom_lower_h/s/v**: Range HSV minimo (solo per custom)
    - **custom_upper_h/s/v**: Range HSV massimo (solo per custom)
    - **blur_kernel**: Sfocatura bordi maschera (3, 5, 7, 9)

    Richiede JWT token. Elaborazione asincrona in background.
    """
    # Crea job
    job = create_chromakey_job(current_user, request, db)

    # Avvia task in background
    # Avvia task in background (session creata internamente)
    background_tasks.add_task(process_chromakey_task, str(job.id), request)

    # Track action
    track_action(
        db=db,
        user_id=current_user.id,
        action_type='chromakey',
        action_details={
            'job_id': str(job.id),
            'audio_mode': request.audio_mode,
            'scale': request.scale,
            'opacity': request.opacity
        }
    )

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
    audio_mode: str = Form("synced", description="Modalità audio (synced, foreground, background, both, timed, none)"),
    # Parametri posizionamento e dimensioni
    position_x: int = Form(0, description="Offset orizzontale dal centro (px, negativo=sinistra, positivo=destra)"),
    position_y: int = Form(0, description="Offset verticale dal centro (px, negativo=alto, positivo=basso)"),
    scale: float = Form(1.0, description="Scala foreground (0.1=10%, 1.0=100%, 2.0=200%)"),
    opacity: float = Form(1.0, description="Opacità foreground (0.0=trasparente, 1.0=opaco)"),
    # Parametri temporali
    start_time: float = Form(0.0, description="Inizio clip in secondi"),
    end_time: Optional[float] = Form(None, description="Fine clip in secondi (null=tutto il video)"),
    # Parametri chromakey (selezione colore) - Standard
    chroma_color: str = Form("green", description="Colore chromakey (green, blue, custom)"),
    custom_lower_h: int = Form(63, description="HSV Hue min (0-180, solo per custom)"),
    custom_lower_s: int = Form(40, description="HSV Saturation min (0-255, solo per custom)"),
    custom_lower_v: int = Form(40, description="HSV Value min (0-255, solo per custom)"),
    custom_upper_h: int = Form(93, description="HSV Hue max (0-180, solo per custom)"),
    custom_upper_s: int = Form(255, description="HSV Saturation max (0-255, solo per custom)"),
    custom_upper_v: int = Form(255, description="HSV Value max (0-255, solo per custom)"),
    blur_kernel: int = Form(5, description="Kernel blur maschera (3, 5, 7, 9)"),
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
    foreground_path = settings.upload_dir / f"fg_{current_user.id}_{foreground.filename}"
    background_path = settings.upload_dir / f"bg_{current_user.id}_{background.filename}"

    # Scrivi file
    with open(foreground_path, "wb") as f:
        content = await foreground.read()
        f.write(content)

    with open(background_path, "wb") as f:
        content = await background.read()
        f.write(content)

    # Crea request con parametri supportati
    request = ChromakeyRequest(
        foreground_video=str(foreground_path),
        background_video=str(background_path),
        output_name=output_name,
        audio_mode=audio_mode,
        position_x=position_x,
        position_y=position_y,
        scale=scale,
        opacity=opacity,
        start_time=start_time,
        end_time=end_time,
        chroma_color=chroma_color,
        custom_lower_h=custom_lower_h,
        custom_lower_s=custom_lower_s,
        custom_lower_v=custom_lower_v,
        custom_upper_h=custom_upper_h,
        custom_upper_s=custom_upper_s,
        custom_upper_v=custom_upper_v,
        blur_kernel=blur_kernel
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

    # Se il job è in processing, marcalo come cancelled invece di eliminarlo
    if job.status == JobStatus.PROCESSING:
        # Killa tutti i processi FFmpeg attivi per interrompere l'elaborazione
        try:
            # Trova e killa tutti i processi ffmpeg
            result = subprocess.run(
                ['pkill', '-9', 'ffmpeg'],
                capture_output=True,
                timeout=5
            )
            print(f"FFmpeg processes killed: {result.returncode}")
        except Exception as e:
            print(f"Errore killing FFmpeg: {e}")

        job.status = JobStatus.FAILED
        job.error = "Elaborazione interrotta dall'utente"
        job.progress = 0
        db.commit()

        return {
            "message": "Elaborazione interrotta con successo",
            "job_id": str(job_id),
            "cancelled": True
        }

    # Altrimenti elimina il job completamente
    db.delete(job)
    db.commit()

    return {
        "message": "Job cancellato con successo",
        "job_id": str(job_id),
        "cancelled": False
    }
