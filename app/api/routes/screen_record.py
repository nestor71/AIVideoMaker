"""
Screen Recording Routes
=======================
Route per registrazione schermo/finestra/area
"""

from pathlib import Path
from typing import Optional, List
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, UploadFile
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.config import settings
from app.core.usage_tracker import track_action
from app.models.user import User
from app.models.job import Job, JobType, JobStatus
from app.models.scheduled_job import ScheduledJob, ScheduledJobStatus
from app.services.screen_record_service import ScreenRecordService, ScreenRecordParams
from app.services.scheduler_service import scheduler_service

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


class ScheduleRecordRequest(BaseModel):
    """Schema per schedulare registrazione futura"""
    scheduled_time: datetime = Field(..., description="Quando avviare registrazione (UTC)")
    duration_seconds: int = Field(..., ge=10, le=28800, description="Durata massima (10s - 8h)")

    # Parametri registrazione (come ScreenRecordRequest)
    output_name: Optional[str] = "scheduled_recording.mp4"
    mode: str = "fullscreen"
    window_title: Optional[str] = None
    monitor_index: Optional[int] = 0  # Indice monitor (0=primario)
    area_x: Optional[int] = None
    area_y: Optional[int] = None
    area_width: Optional[int] = None
    area_height: Optional[int] = None
    fps: int = 30
    quality: str = "high"
    record_audio: bool = True

    # NUOVI PARAMETRI per controllo avanzato
    video_source: str = "monitor"  # "monitor", "webcam", o "monitor_webcam" (PIP)
    output_format: str = "mp4"  # "mp4" o "webm"
    audio_system: bool = True  # Audio di sistema
    audio_microphone: bool = False  # Audio microfono

    # PARAMETRI WEBCAM per Picture-in-Picture
    webcam_x: Optional[int] = None  # Posizione X webcam (coordinate canvas 800x450)
    webcam_y: Optional[int] = None  # Posizione Y webcam
    webcam_width: Optional[int] = None  # Larghezza webcam
    webcam_height: Optional[int] = None  # Altezza webcam


class ScheduledJobResponse(BaseModel):
    """Schema per risposta job schedulato"""
    id: str
    scheduled_time: datetime
    duration_seconds: int
    status: str
    time_until_start: int  # Secondi mancanti
    parameters: dict
    created_at: datetime
    output_path: Optional[str] = None
    error_message: Optional[str] = None


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

        # Configura servizio con job_id per tracciamento
        service = ScreenRecordService(settings, job_id=job_id)

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


@router.post("/jobs/{job_id}/stop")
async def stop_recording(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Ferma registrazione in corso

    Interrompe il processo FFmpeg per il job specificato.

    Richiede JWT token.
    """
    from app.services.screen_record_service import stop_recording_by_job_id

    # Verifica che il job appartenga all'utente
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

    # Verifica che il job sia in elaborazione
    if job.status != JobStatus.PROCESSING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Il job è in stato {job.status.value}, impossibile fermare"
        )

    # Ferma il processo
    success = stop_recording_by_job_id(job_id)

    if success:
        # Aggiorna job nel database
        job.status = JobStatus.FAILED
        job.error_message = "Registrazione interrotta manualmente dall'utente"
        db.commit()

        return {
            "message": "Registrazione fermata con successo",
            "job_id": job_id
        }
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Impossibile fermare la registrazione. Il processo potrebbe essere già terminato."
        )


@router.get("/active-jobs")
async def list_active_ffmpeg_jobs(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Lista job FFmpeg attivi dell'utente

    Restituisce solo i job screen_record che hanno un processo FFmpeg effettivamente
    in esecuzione (presenti in _active_recordings).

    Richiede JWT token.
    """
    from app.services.screen_record_service import get_active_recordings

    # Ottieni lista job_id con processi FFmpeg realmente attivi
    active_recording_ids = get_active_recordings()

    # Se non ci sono processi attivi, restituisci lista vuota
    if not active_recording_ids:
        return {
            "active_jobs": [],
            "count": 0
        }

    # Ottieni job dal database solo se hanno processo attivo
    active_jobs = db.query(Job).filter(
        Job.id.in_(active_recording_ids),
        Job.user_id == current_user.id,
        Job.job_type == JobType.SCREEN_RECORD
    ).all()

    # Trasforma in formato JSON-friendly
    jobs_list = []
    for job in active_jobs:
        jobs_list.append({
            "job_id": str(job.id),
            "started_at": job.created_at.isoformat() if job.created_at else None,
            "progress": job.progress,
            "output_name": job.result.get("output_name") if job.result else "recording.mp4"
        })

    return {
        "active_jobs": jobs_list,
        "count": len(jobs_list)
    }


@router.get("/monitors")
async def list_monitors(
    current_user: User = Depends(get_current_user)
):
    """
    Lista monitor disponibili con marca e modello

    Rileva i monitor connessi al sistema con informazioni su marca/modello.
    Su macOS usa system_profiler, su Windows WMI, su Linux xrandr.

    Richiede JWT token.
    """
    import platform
    import subprocess
    import re
    import json

    system = platform.system()
    monitors = []

    try:
        if system == "Darwin":  # macOS
            # Usa system_profiler per ottenere info monitor
            result = subprocess.run(
                ['system_profiler', 'SPDisplaysDataType', '-json'],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                data = json.loads(result.stdout)

                # Estrai informazioni monitor
                if 'SPDisplaysDataType' in data:
                    for gpu in data['SPDisplaysDataType']:
                        if 'spdisplays_ndrvs' in gpu:
                            for display in gpu['spdisplays_ndrvs']:
                                # Nome display (es: "DELL U2720Q")
                                name = display.get('_name', 'Monitor Sconosciuto')

                                # Risoluzione
                                resolution = display.get('_spdisplays_resolution', 'N/A')

                                # Tipo connessione
                                connection = display.get('spdisplays_connection_type', 'N/A')

                                monitors.append({
                                    'name': name,
                                    'resolution': resolution,
                                    'connection': connection,
                                    'brand': name.split()[0] if ' ' in name else 'N/A',
                                    'model': ' '.join(name.split()[1:]) if ' ' in name else name
                                })

        elif system == "Windows":
            # Usa WMIC per ottenere info monitor
            result = subprocess.run(
                ['wmic', 'desktopmonitor', 'get', 'Name,ScreenWidth,ScreenHeight', '/format:list'],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                # Parsing output WMIC
                current_monitor = {}
                for line in result.stdout.split('\n'):
                    line = line.strip()
                    if '=' in line:
                        key, value = line.split('=', 1)
                        current_monitor[key.strip()] = value.strip()
                    elif current_monitor:
                        # Fine blocco, aggiungi monitor
                        name = current_monitor.get('Name', 'Monitor Sconosciuto')
                        width = current_monitor.get('ScreenWidth', 'N/A')
                        height = current_monitor.get('ScreenHeight', 'N/A')

                        monitors.append({
                            'name': name,
                            'resolution': f"{width}x{height}" if width != 'N/A' else 'N/A',
                            'connection': 'N/A',
                            'brand': name.split()[0] if ' ' in name else 'N/A',
                            'model': ' '.join(name.split()[1:]) if ' ' in name else name
                        })
                        current_monitor = {}

        elif system == "Linux":
            # Usa xrandr per ottenere info monitor
            result = subprocess.run(
                ['xrandr', '--query'],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                # Parsing output xrandr
                for line in result.stdout.split('\n'):
                    if ' connected' in line:
                        match = re.match(r'^(\S+)\s+connected.*?(\d+x\d+)', line)
                        if match:
                            output_name = match.group(1)
                            resolution = match.group(2)

                            monitors.append({
                                'name': output_name,
                                'resolution': resolution,
                                'connection': 'N/A',
                                'brand': 'N/A',
                                'model': output_name
                            })

    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Errore rilevamento monitor: {e}")

    # Se non abbiamo rilevato monitor, restituisci monitor di default
    if not monitors:
        # Usa pyautogui per ottenere almeno la risoluzione
        import pyautogui
        width, height = pyautogui.size()
        monitors.append({
            'name': 'Monitor Primario',
            'resolution': f"{width}x{height}",
            'connection': 'N/A',
            'brand': 'N/A',
            'model': 'Monitor Primario'
        })

    # Aggiungi indice a ciascun monitor
    for i, monitor in enumerate(monitors):
        monitor['index'] = i

    return {
        'monitors': monitors,
        'count': len(monitors)
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


# ==================== Scheduled Recording Routes ====================

def execute_scheduled_recording(scheduled_job_id: str, db_session):
    """
    Funzione eseguita da APScheduler quando parte la registrazione programmata

    Args:
        scheduled_job_id: UUID del ScheduledJob
        db_session: Sessione database (passata dallo scheduler)
    """
    import logging
    logger = logging.getLogger(__name__)

    try:
        # Ottieni scheduled job
        scheduled_job = db_session.query(ScheduledJob).filter(
            ScheduledJob.id == scheduled_job_id
        ).first()

        if not scheduled_job:
            logger.error(f"ScheduledJob {scheduled_job_id} non trovato")
            return

        # Aggiorna status
        scheduled_job.status = ScheduledJobStatus.RUNNING
        scheduled_job.started_at = datetime.utcnow()
        db_session.commit()

        # Crea parametri registrazione
        params_dict = scheduled_job.parameters
        params = ScreenRecordParams(
            output_path=settings.output_dir / params_dict.get("output_name", "scheduled_recording.mp4"),
            mode=params_dict.get("mode", "fullscreen"),
            window_title=params_dict.get("window_title"),
            monitor_index=params_dict.get("monitor_index", 0),
            area_x=params_dict.get("area_x"),
            area_y=params_dict.get("area_y"),
            area_width=params_dict.get("area_width"),
            area_height=params_dict.get("area_height"),
            duration_seconds=scheduled_job.duration_seconds,
            fps=params_dict.get("fps", 30),
            quality=params_dict.get("quality", "high"),
            record_audio=params_dict.get("record_audio", True),
            # NUOVI PARAMETRI
            video_source=params_dict.get("video_source", "monitor"),
            output_format=params_dict.get("output_format", "mp4"),
            audio_system=params_dict.get("audio_system", True),
            audio_microphone=params_dict.get("audio_microphone", False),
            # PARAMETRI WEBCAM per PIP
            webcam_x=params_dict.get("webcam_x"),
            webcam_y=params_dict.get("webcam_y"),
            webcam_width=params_dict.get("webcam_width"),
            webcam_height=params_dict.get("webcam_height")
        )

        # Callback progresso
        def progress_callback(progress: int, message: str):
            pass  # Opzionale: aggiorna progresso in DB

        # Esegui registrazione con job_id per tracciamento
        service = ScreenRecordService(settings, job_id=scheduled_job_id)
        result = service.record(params, progress_callback)

        # Aggiorna job
        scheduled_job.status = ScheduledJobStatus.COMPLETED
        scheduled_job.completed_at = datetime.utcnow()
        scheduled_job.output_path = result.get("output_path")
        db_session.commit()

        logger.info(f"Registrazione schedulata {scheduled_job_id} completata: {result['output_path']}")

    except Exception as e:
        logger.error(f"Errore registrazione schedulata {scheduled_job_id}: {e}")
        if scheduled_job:
            scheduled_job.status = ScheduledJobStatus.FAILED
            scheduled_job.error_message = str(e)
            scheduled_job.completed_at = datetime.utcnow()
            db_session.commit()


@router.post("/schedule", response_model=ScheduledJobResponse, status_code=status.HTTP_201_CREATED)
async def schedule_recording(
    request: ScheduleRecordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Programma registrazione schermo per orario futuro

    - **scheduled_time**: Quando avviare (formato ISO 8601 UTC, es: 2025-01-16T14:30:00Z)
    - **duration_seconds**: Durata massima (10s - 8h)
    - Parametri registrazione: come /record

    La registrazione partirà automaticamente all'orario specificato.
    Il server FastAPI DEVE essere in esecuzione a quell'orario.

    Richiede JWT token.
    """
    # Valida orario futuro
    now_utc = datetime.now(timezone.utc)
    if request.scheduled_time <= now_utc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="scheduled_time deve essere nel futuro"
        )

    # Valida modalità
    if request.mode not in ScreenRecordService.MODES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Modalità non valida. Disponibili: {ScreenRecordService.MODES}"
        )

    # Valida parametri mode-specific
    if request.mode == "window" and not request.window_title:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Modalità 'window' richiede window_title"
        )

    if request.mode == "area":
        if any(p is None for p in [request.area_x, request.area_y, request.area_width, request.area_height]):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Modalità 'area' richiede area_x, area_y, area_width, area_height"
            )

    if request.mode == "custom":
        # Custom può avere solo monitor_index o anche area personalizzata
        if request.area_x is not None:
            # Se specifica area, tutti i parametri devono essere presenti
            if any(p is None for p in [request.area_y, request.area_width, request.area_height]):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Modalità 'custom' con area richiede area_x, area_y, area_width, area_height"
                )

    # Crea ScheduledJob
    scheduled_job = ScheduledJob(
        user_id=current_user.id,
        scheduled_time=request.scheduled_time,
        duration_seconds=request.duration_seconds,
        status=ScheduledJobStatus.SCHEDULED,
        parameters=request.dict(exclude={"scheduled_time", "duration_seconds"})
    )

    db.add(scheduled_job)
    db.commit()
    db.refresh(scheduled_job)

    # Schedula in APScheduler
    try:
        scheduler_job_id = scheduler_service.schedule_job(
            job_id=str(scheduled_job.id),
            func=execute_scheduled_recording,
            run_date=request.scheduled_time,
            scheduled_job_id=str(scheduled_job.id),
            db_session=db
        )

        scheduled_job.scheduler_job_id = scheduler_job_id
        db.commit()

    except Exception as e:
        # Rollback se scheduling fallisce
        db.delete(scheduled_job)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Impossibile schedulare job: {str(e)}"
        )

    return ScheduledJobResponse(
        id=str(scheduled_job.id),
        scheduled_time=scheduled_job.scheduled_time,
        duration_seconds=scheduled_job.duration_seconds,
        status=scheduled_job.status.value,
        time_until_start=scheduled_job.time_until_start,
        parameters=scheduled_job.parameters,
        created_at=scheduled_job.created_at,
        output_path=None,
        error_message=None
    )


@router.get("/scheduled", response_model=List[ScheduledJobResponse])
async def list_scheduled_recordings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Lista tutte le registrazioni programmate dell'utente

    Include sia job in attesa che completati/falliti.

    Richiede JWT token.
    """
    jobs = db.query(ScheduledJob).filter(
        ScheduledJob.user_id == current_user.id
    ).order_by(ScheduledJob.scheduled_time.desc()).all()

    return [
        ScheduledJobResponse(
            id=str(job.id),
            scheduled_time=job.scheduled_time,
            duration_seconds=job.duration_seconds,
            status=job.status.value,
            time_until_start=job.time_until_start,
            parameters=job.parameters,
            created_at=job.created_at,
            output_path=job.output_path,
            error_message=job.error_message
        )
        for job in jobs
    ]


@router.get("/scheduled/{job_id}", response_model=ScheduledJobResponse)
async def get_scheduled_recording(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Ottieni dettagli registrazione schedulata

    Richiede JWT token.
    """
    job = db.query(ScheduledJob).filter(
        ScheduledJob.id == job_id,
        ScheduledJob.user_id == current_user.id
    ).first()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job schedulato non trovato"
        )

    return ScheduledJobResponse(
        id=str(job.id),
        scheduled_time=job.scheduled_time,
        duration_seconds=job.duration_seconds,
        status=job.status.value,
        time_until_start=job.time_until_start,
        parameters=job.parameters,
        created_at=job.created_at,
        output_path=job.output_path,
        error_message=job.error_message
    )


@router.delete("/scheduled/{job_id}")
async def cancel_scheduled_recording(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Cancella registrazione schedulata (solo se non ancora partita)

    Richiede JWT token.
    """
    job = db.query(ScheduledJob).filter(
        ScheduledJob.id == job_id,
        ScheduledJob.user_id == current_user.id
    ).first()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job schedulato non trovato"
        )

    if not job.can_cancel:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Impossibile cancellare job in stato {job.status.value}"
        )

    # Rimuovi da APScheduler
    if job.scheduler_job_id:
        scheduler_service.cancel_job(job.scheduler_job_id)

    # Aggiorna status
    job.status = ScheduledJobStatus.CANCELLED
    db.commit()

    return {
        "message": "Registrazione schedulata cancellata",
        "job_id": str(job.id)
    }


@router.post("/scheduled/{job_id}/stop")
async def stop_scheduled_recording(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Ferma registrazione schedulata in esecuzione

    Interrompe il processo FFmpeg per la registrazione schedulata.

    Richiede JWT token.
    """
    from app.services.screen_record_service import stop_recording_by_job_id

    # Verifica che il job appartenga all'utente
    job = db.query(ScheduledJob).filter(
        ScheduledJob.id == job_id,
        ScheduledJob.user_id == current_user.id
    ).first()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job schedulato non trovato"
        )

    # Verifica che il job sia in esecuzione
    if job.status != ScheduledJobStatus.RUNNING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Il job è in stato {job.status.value}, impossibile fermare"
        )

    # Ferma il processo
    success = stop_recording_by_job_id(job_id)

    if success:
        # Aggiorna job nel database
        job.status = ScheduledJobStatus.FAILED
        job.error_message = "Registrazione interrotta manualmente dall'utente"
        job.completed_at = datetime.utcnow()
        db.commit()

        return {
            "message": "Registrazione fermata con successo",
            "job_id": job_id
        }
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Impossibile fermare la registrazione. Il processo potrebbe essere già terminato."
        )


@router.delete("/scheduled/{job_id}/delete")
async def delete_scheduled_recording(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Elimina definitivamente una registrazione schedulata (qualsiasi stato)

    Richiede JWT token.
    """
    job = db.query(ScheduledJob).filter(
        ScheduledJob.id == job_id,
        ScheduledJob.user_id == current_user.id
    ).first()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job schedulato non trovato"
        )

    # Se è ancora scheduled, rimuovi da APScheduler
    if job.status == ScheduledJobStatus.SCHEDULED and job.scheduler_job_id:
        scheduler_service.cancel_job(job.scheduler_job_id)

    # Elimina dal database
    db.delete(job)
    db.commit()

    return {
        "message": "Registrazione eliminata",
        "job_id": str(job_id)
    }


@router.delete("/scheduled/delete-all")
async def delete_all_scheduled_recordings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Elimina TUTTE le registrazioni schedulate dell'utente (qualsiasi stato)

    Richiede JWT token.
    """
    jobs = db.query(ScheduledJob).filter(
        ScheduledJob.user_id == current_user.id
    ).all()

    count = len(jobs)

    if count == 0:
        return {
            "message": "Nessuna registrazione da eliminare",
            "count": 0
        }

    # Rimuovi da APScheduler quelli ancora scheduled
    for job in jobs:
        if job.status == ScheduledJobStatus.SCHEDULED and job.scheduler_job_id:
            scheduler_service.cancel_job(job.scheduler_job_id)

    # Elimina tutti dal database
    for job in jobs:
        db.delete(job)

    db.commit()

    return {
        "message": f"{count} registrazioni eliminate",
        "count": count
    }


# ==================== Browser Recordings Routes ====================

@router.post("/browser-recordings/upload")
async def upload_browser_recording(
    file: UploadFile,
    current_user: User = Depends(get_current_user)
):
    """
    Salva una registrazione fatta dal browser sul server

    Il frontend invia il blob WebM come multipart/form-data
    """
    import subprocess
    import logging
    logger = logging.getLogger(__name__)

    # Crea cartella user-specific
    user_recordings_dir = settings.output_dir / "screen_recordings" / str(current_user.id)
    user_recordings_dir.mkdir(parents=True, exist_ok=True)

    # Genera nome file univoco
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    safe_filename = f"recording_{timestamp}.webm"
    temp_filename = f"temp_{safe_filename}"

    temp_path = user_recordings_dir / temp_filename
    file_path = user_recordings_dir / safe_filename

    # Leggi e salva file temporaneo
    content = await file.read()
    with open(temp_path, "wb") as f:
        f.write(content)

    # Ripara il file WebM con ffmpeg per assicurare metadata corretti
    try:
        result = subprocess.run([
            settings.ffmpeg_path,
            '-i', str(temp_path),
            '-c', 'copy',  # Copia stream senza ricodificare
            '-y',
            str(file_path)
        ], capture_output=True, text=True, timeout=30)

        if result.returncode == 0:
            # Rimozione file temporaneo
            temp_path.unlink()
            logger.info(f"File WebM riparato con successo: {safe_filename}")
        else:
            # Se fallisce, usa il file originale
            temp_path.rename(file_path)
            logger.warning(f"Impossibile riparare WebM, uso file originale: {result.stderr}")

    except Exception as e:
        # Se ffmpeg fallisce, usa il file originale
        if temp_path.exists():
            temp_path.rename(file_path)
        logger.error(f"Errore riparazione WebM: {e}")

    return {
        "filename": safe_filename,
        "path": str(file_path),
        "size": len(content)
    }


@router.get("/browser-recordings")
async def list_browser_recordings(
    current_user: User = Depends(get_current_user)
):
    """
    Lista tutte le registrazioni browser salvate dell'utente
    """
    import os
    import subprocess
    import json

    user_recordings_dir = settings.output_dir / "screen_recordings" / str(current_user.id)

    if not user_recordings_dir.exists():
        return {"recordings": []}

    recordings = []
    for file_path in sorted(user_recordings_dir.glob("*.webm"), key=os.path.getmtime, reverse=True):
        stat = file_path.stat()

        # Ottieni durata video con ffprobe
        duration = None
        try:
            result = subprocess.run([
                settings.ffprobe_path,
                '-v', 'error',
                '-show_entries', 'format=duration',
                '-of', 'default=noprint_wrappers=1:nokey=1',
                str(file_path)
            ], capture_output=True, text=True, timeout=5)

            if result.returncode == 0 and result.stdout.strip():
                try:
                    duration = float(result.stdout.strip())
                except ValueError:
                    # Se non riesce a parsare, prova metodo alternativo
                    pass

            # Se duration è ancora None o 0, prova metodo alternativo con streams
            if not duration or duration == 0:
                result2 = subprocess.run([
                    settings.ffprobe_path,
                    '-v', 'quiet',
                    '-print_format', 'json',
                    '-show_format',
                    '-show_streams',
                    str(file_path)
                ], capture_output=True, text=True, timeout=5)

                if result2.returncode == 0:
                    data = json.loads(result2.stdout)
                    # Prova prima da format
                    if 'format' in data and 'duration' in data['format']:
                        duration = float(data['format']['duration'])
                    # Se ancora None, calcola da streams
                    elif 'streams' in data and len(data['streams']) > 0:
                        for stream in data['streams']:
                            if 'duration' in stream:
                                duration = float(stream['duration'])
                                break
        except Exception as e:
            # Se ffprobe fallisce, continua senza durata
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Impossibile ottenere durata per {file_path.name}: {e}")
            pass

        recordings.append({
            "filename": file_path.name,
            "size": stat.st_size,
            "duration": duration,  # Durata in secondi (può essere None se fallisce)
            "created_at": datetime.fromtimestamp(stat.st_ctime).isoformat(),
            "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat()
        })

    return {"recordings": recordings}


@router.delete("/browser-recordings/{filename}")
async def delete_browser_recording(
    filename: str,
    current_user: User = Depends(get_current_user)
):
    """
    Elimina una registrazione browser salvata
    """
    import os

    # Valida filename (security: no path traversal)
    if "/" in filename or "\\" in filename or ".." in filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nome file non valido"
        )

    user_recordings_dir = settings.output_dir / "screen_recordings" / str(current_user.id)
    file_path = user_recordings_dir / filename

    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Registrazione non trovata"
        )

    # Elimina file
    file_path.unlink()

    return {"message": "Registrazione eliminata", "filename": filename}


@router.delete("/browser-recordings")
async def delete_all_browser_recordings(
    current_user: User = Depends(get_current_user)
):
    """
    Elimina tutte le registrazioni browser salvate dell'utente
    """
    import shutil

    user_recordings_dir = settings.output_dir / "screen_recordings" / str(current_user.id)

    if not user_recordings_dir.exists():
        return {"message": "Nessuna registrazione da eliminare", "count": 0}

    # Conta file
    count = len(list(user_recordings_dir.glob("*.webm")))

    # Elimina tutta la cartella
    shutil.rmtree(user_recordings_dir)

    return {"message": f"{count} registrazioni eliminate", "count": count}


@router.get("/browser-recordings/{filename}/stream")
async def stream_browser_recording(
    filename: str,
    current_user: User = Depends(get_current_user)
):
    """
    Serve il file video per streaming/download
    """
    from fastapi.responses import FileResponse

    # Valida filename (security: no path traversal)
    if "/" in filename or "\\" in filename or ".." in filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nome file non valido"
        )

    user_recordings_dir = settings.output_dir / "screen_recordings" / str(current_user.id)
    file_path = user_recordings_dir / filename

    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Registrazione non trovata"
        )

    return FileResponse(
        path=str(file_path),
        media_type="video/webm",
        filename=filename
    )
