"""
API Routes for Multi-Layer Video Compositor
"""

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends, BackgroundTasks
from fastapi.responses import FileResponse
from typing import List, Optional
import logging
import json
import uuid
from pathlib import Path
from datetime import datetime
import subprocess

from app.core.security import get_current_user
from app.services.compositor_service import compositor_service
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter()

# Job storage (in-memory per ora, TODO: usare Redis o DB)
jobs = {}

class CompositorJob:
    """Job di compositing"""
    def __init__(self, job_id: str, user_id: int):
        self.job_id = job_id
        self.user_id = user_id
        self.status = 'pending'  # pending, processing, completed, failed
        self.progress = 0
        self.message = ''
        self.output_path = None
        self.error = None
        self.created_at = datetime.now()


async def process_compositor_job(
    job_id: str,
    main_video_path: str,
    layers_data: List[dict]
):
    """Background task per processare compositing"""
    job = jobs.get(job_id)
    if not job:
        logger.error(f"Job {job_id} non trovato")
        return

    try:
        job.status = 'processing'
        job.progress = 10
        job.message = 'Inizializzazione compositor...'

        logger.info(f"🎬 Avvio job compositor {job_id}")
        logger.info(f"   Main video: {main_video_path}")
        logger.info(f"   Layers: {len(layers_data)}")

        job.progress = 30
        job.message = 'Analisi video principale...'

        # Processa composizione
        result = await compositor_service.process_composition(
            main_video_path=main_video_path,
            layers=layers_data
        )

        job.progress = 90
        job.message = 'Finalizzazione...'

        # Salva risultato
        job.output_path = result['output_path']
        job.status = 'completed'
        job.progress = 100
        job.message = 'Completato!'

        logger.info(f"✅ Job {job_id} completato: {result['output_path']}")

    except Exception as e:
        logger.error(f"❌ Errore job {job_id}: {e}")
        job.status = 'failed'
        job.error = str(e)
        job.message = f'Errore: {str(e)}'


@router.post("/upload")
async def upload_compositor_files(
    background_tasks: BackgroundTasks,
    main_video: UploadFile = File(..., description="Video principale"),
    layer_files: List[UploadFile] = File(default=[], description="File layer (video, immagini, audio)"),
    layers_config: str = Form(..., description="Configurazione layer (JSON)"),
    current_user: User = Depends(get_current_user)
):
    """
    Upload file e avvia compositing multi-layer

    Args:
        main_video: Video base
        layer_files: Lista di file da sovrapporre
        layers_config: JSON con configurazione layer, esempio:
        [
            {
                "type": "video",
                "filename": "overlay.mp4",
                "posX": 0,
                "posY": 0,
                "scale": 30,
                "opacity": 1.0,
                "chromakey": true,
                "threshold": 100,
                "tolerance": 50,
                "startTime": 0
            }
        ]

    Returns:
        {
            "job_id": "uuid",
            "status": "accepted",
            "message": "Job avviato"
        }
    """

    try:
        # Parse layers config
        try:
            layers_data = json.loads(layers_config)
        except json.JSONDecodeError as e:
            raise HTTPException(status_code=400, detail=f"layers_config JSON invalido: {e}")

        # Crea job ID
        job_id = str(uuid.uuid4())

        # Upload directory
        upload_dir = Path("uploads")
        upload_dir.mkdir(exist_ok=True)

        # Salva video principale
        main_video_filename = f"main_{job_id}_{main_video.filename}"
        main_video_path = upload_dir / main_video_filename

        with open(main_video_path, "wb") as f:
            content = await main_video.read()
            f.write(content)

        logger.info(f"📹 Video principale salvato: {main_video_path} ({len(content)} bytes)")

        # Salva layer files e mappa a layers_data
        layer_paths = {}
        for layer_file in layer_files:
            layer_filename = f"layer_{job_id}_{layer_file.filename}"
            layer_path = upload_dir / layer_filename

            with open(layer_path, "wb") as f:
                content = await layer_file.read()
                f.write(content)

            layer_paths[layer_file.filename] = str(layer_path)
            logger.info(f"   Layer salvato: {layer_path} ({len(content)} bytes)")

        # Aggiungi path ai layers_data
        for layer in layers_data:
            filename = layer.get('filename')
            if filename and filename in layer_paths:
                layer['path'] = layer_paths[filename]
            else:
                logger.warning(f"⚠️ Layer filename '{filename}' non trovato negli upload")

        # Crea job
        job = CompositorJob(job_id=job_id, user_id=current_user.id)
        jobs[job_id] = job

        # Avvia processing in background
        background_tasks.add_task(
            process_compositor_job,
            job_id=job_id,
            main_video_path=str(main_video_path),
            layers_data=layers_data
        )

        logger.info(f"✅ Job compositor {job_id} creato e avviato")

        return {
            "job_id": job_id,
            "status": "accepted",
            "message": "File caricati. Job compositor avviato.",
            "layers_count": len(layers_data)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Errore upload compositor: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/jobs/{job_id}")
async def get_compositor_job_status(
    job_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Ottieni stato job compositor

    Returns:
        {
            "job_id": "uuid",
            "status": "processing|completed|failed",
            "progress": 0-100,
            "message": "...",
            "output_path": "/path/to/output.mp4" (se completed)
        }
    """

    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job non trovato")

    # Verifica ownership
    if job.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Non autorizzato")

    response = {
        "job_id": job.job_id,
        "status": job.status,
        "progress": job.progress,
        "message": job.message
    }

    if job.output_path:
        response["output_path"] = job.output_path

    if job.error:
        response["error"] = job.error

    return response


@router.get("/download/{job_id}")
async def download_compositor_result(
    job_id: str,
    current_user: User = Depends(get_current_user)
):
    """Download video compositor risultante"""

    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job non trovato")

    # Verifica ownership
    if job.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Non autorizzato")

    if job.status != 'completed':
        raise HTTPException(status_code=400, detail=f"Job non completato (status: {job.status})")

    if not job.output_path or not Path(job.output_path).exists():
        raise HTTPException(status_code=404, detail="File output non trovato")

    return FileResponse(
        path=job.output_path,
        media_type="video/mp4",
        filename=Path(job.output_path).name
    )


@router.delete("/jobs/{job_id}")
async def cancel_compositor_job(
    job_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Cancella/interrompe job compositor

    Se il job è in processing, lo interrompe terminando FFmpeg.
    Altrimenti lo rimuove dalla lista.
    """

    logger.info(f"🛑 Richiesta cancellazione job: {job_id}")
    logger.info(f"   User ID: {current_user.id}")
    logger.info(f"   Job in memoria: {len(jobs)}")

    job = jobs.get(job_id)
    if not job:
        logger.error(f"❌ Job {job_id} non trovato in memoria")
        logger.info(f"   Job disponibili: {list(jobs.keys())}")
        raise HTTPException(status_code=404, detail="Job non trovato")

    # Verifica ownership
    if job.user_id != current_user.id:
        logger.error(f"❌ Utente {current_user.id} non autorizzato per job di utente {job.user_id}")
        raise HTTPException(status_code=403, detail="Non autorizzato")

    logger.info(f"   Job trovato - Status: {job.status}")

    # Se il job è in processing, killa FFmpeg e marca come failed
    if job.status == 'processing':
        logger.info("   🔪 Job in processing - killing FFmpeg...")
        # Killa tutti i processi FFmpeg attivi per interrompere l'elaborazione
        try:
            result = subprocess.run(
                ['pkill', '-9', 'ffmpeg'],
                capture_output=True,
                timeout=5
            )
            logger.info(f"   ✅ FFmpeg processes killed: returncode={result.returncode}")
            if result.stdout:
                logger.info(f"   stdout: {result.stdout.decode()}")
            if result.stderr:
                logger.info(f"   stderr: {result.stderr.decode()}")
        except Exception as e:
            logger.error(f"   ❌ Errore killing FFmpeg: {e}")

        # Elimina file output parziale se esiste
        if job.output_path and Path(job.output_path).exists():
            try:
                Path(job.output_path).unlink()
                logger.info(f"   🗑️ File output parziale eliminato: {job.output_path}")
            except Exception as e:
                logger.error(f"   ❌ Errore eliminazione file output: {e}")

        # Elimina anche eventuali file parziali nella directory output
        # (file creati negli ultimi 5 minuti con pattern compositor_*)
        try:
            import time
            output_dir = Path("output")
            if output_dir.exists():
                current_time = time.time()
                for file_path in output_dir.glob("compositor_*.mp4"):
                    # Controlla se il file è stato creato negli ultimi 5 minuti
                    if current_time - file_path.stat().st_mtime < 300:  # 5 minuti
                        try:
                            file_path.unlink()
                            logger.info(f"   🗑️ File parziale eliminato: {file_path}")
                        except Exception as e:
                            logger.error(f"   ❌ Errore eliminazione {file_path}: {e}")
        except Exception as e:
            logger.error(f"   ❌ Errore pulizia directory output: {e}")

        job.status = 'failed'
        job.error = "Elaborazione interrotta dall'utente"
        job.progress = 0
        job.message = "Interrotto"

        logger.info(f"✅ Job {job_id} marcato come failed")

        return {
            "message": "Elaborazione interrotta con successo",
            "job_id": job_id,
            "cancelled": True
        }

    # Altrimenti rimuovi il job
    logger.info(f"   Job status '{job.status}' - rimozione dalla memoria")
    del jobs[job_id]

    logger.info(f"✅ Job {job_id} eliminato")

    return {
        "message": "Job eliminato con successo",
        "job_id": job_id
    }
