"""
API Routes for Output Files Management
========================================
Gestione file elaborati nella cartella outputs
"""

import os
import logging
from pathlib import Path
from typing import List, Optional
from datetime import datetime
import subprocess

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import get_current_user
from app.core.database import get_db
from app.models.user import User

router = APIRouter()
logger = logging.getLogger(__name__)


class OutputFileInfo(BaseModel):
    """Informazioni file output"""
    filename: str
    path: str
    size_bytes: int
    size_mb: float
    created_at: str
    duration_seconds: Optional[float] = None
    width: Optional[int] = None
    height: Optional[int] = None
    format: Optional[str] = None
    operation_type: Optional[str] = None  # compositor, chromakey, translation, etc.


def get_video_metadata(video_path: Path) -> dict:
    """
    Estrae metadata video usando FFprobe

    Returns:
        {
            'duration': float (secondi),
            'width': int,
            'height': int,
            'format': str
        }
    """
    try:
        # FFprobe command per ottenere metadata JSON
        cmd = [
            'ffprobe',
            '-v', 'quiet',
            '-print_format', 'json',
            '-show_format',
            '-show_streams',
            str(video_path)
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)

        if result.returncode != 0:
            logger.warning(f"FFprobe failed for {video_path}: {result.stderr}")
            return {}

        import json
        data = json.loads(result.stdout)

        # Estrai info video stream
        video_stream = None
        for stream in data.get('streams', []):
            if stream.get('codec_type') == 'video':
                video_stream = stream
                break

        metadata = {}

        # Durata
        if 'format' in data and 'duration' in data['format']:
            metadata['duration'] = float(data['format']['duration'])

        # Dimensioni
        if video_stream:
            metadata['width'] = video_stream.get('width')
            metadata['height'] = video_stream.get('height')
            metadata['format'] = video_stream.get('codec_name', 'unknown')

        return metadata

    except Exception as e:
        logger.error(f"Errore estrazione metadata {video_path}: {e}")
        return {}


def guess_operation_type(filename: str) -> str:
    """
    Deduce il tipo di operazione dal filename

    Examples:
        compositor_xxx.mp4 -> "Sovrapposizione File"
        chromakey_xxx.mp4 -> "Rimozione Sfondo"
        translated_xxx.mp4 -> "Traduzione Video"
    """
    filename_lower = filename.lower()

    if 'compositor' in filename_lower or 'composite' in filename_lower:
        return "Sovrapposizione File"
    elif 'chromakey' in filename_lower or 'chroma' in filename_lower:
        return "Rimozione Sfondo"
    elif 'translated' in filename_lower or 'translation' in filename_lower:
        return "Traduzione Video"
    elif 'thumbnail' in filename_lower:
        return "Generazione Thumbnail"
    elif 'logo' in filename_lower:
        return "Sovrapposizione Logo"
    else:
        return "Elaborazione Video"


@router.get("/list", response_model=List[OutputFileInfo])
async def list_output_files(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Elenca tutti i file nella cartella outputs con metadata dettagliati

    Returns:
        Lista di OutputFileInfo con:
        - filename: nome file
        - size_mb: dimensione in MB
        - created_at: data creazione
        - duration_seconds: durata video
        - width, height: risoluzione
        - format: codec video
        - operation_type: tipo operazione eseguita
    """
    try:
        output_dir = settings.output_dir

        if not output_dir.exists():
            return []

        files_info = []

        # Scansiona tutti i file nella cartella outputs
        for file_path in output_dir.iterdir():
            if not file_path.is_file():
                continue

            # Skip file nascosti
            if file_path.name.startswith('.'):
                continue

            # Ottieni info base
            stat = file_path.stat()
            size_bytes = stat.st_size
            size_mb = size_bytes / (1024 * 1024)
            created_at = datetime.fromtimestamp(stat.st_ctime).isoformat()

            # Deduce tipo operazione
            operation_type = guess_operation_type(file_path.name)

            # Estrai metadata video (solo per file video)
            metadata = {}
            if file_path.suffix.lower() in ['.mp4', '.avi', '.mov', '.mkv', '.webm']:
                metadata = get_video_metadata(file_path)

            files_info.append(OutputFileInfo(
                filename=file_path.name,
                path=str(file_path),
                size_bytes=size_bytes,
                size_mb=round(size_mb, 2),
                created_at=created_at,
                duration_seconds=metadata.get('duration'),
                width=metadata.get('width'),
                height=metadata.get('height'),
                format=metadata.get('format'),
                operation_type=operation_type
            ))

        # Ordina per data creazione (più recenti prima)
        files_info.sort(key=lambda x: x.created_at, reverse=True)

        logger.info(f"📁 Lista outputs per user {current_user.id}: {len(files_info)} file trovati")

        return files_info

    except Exception as e:
        logger.error(f"Errore lista outputs: {e}")
        raise HTTPException(status_code=500, detail=f"Errore lettura file outputs: {str(e)}")


@router.delete("/delete/{filename}")
async def delete_output_file(
    filename: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Elimina un singolo file dalla cartella outputs

    Args:
        filename: Nome del file da eliminare

    Returns:
        {"message": "File eliminato", "filename": "..."}
    """
    try:
        # Validazione: previeni path traversal
        if '..' in filename or '/' in filename or '\\' in filename:
            raise HTTPException(status_code=400, detail="Nome file non valido")

        file_path = settings.output_dir / filename

        # Verifica che esista
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="File non trovato")

        # Verifica che sia dentro output_dir (security check)
        if not str(file_path.resolve()).startswith(str(settings.output_dir.resolve())):
            raise HTTPException(status_code=403, detail="Accesso negato")

        # Elimina file
        file_path.unlink()

        logger.info(f"🗑️ File eliminato da user {current_user.id}: {filename}")

        return {
            "message": "File eliminato con successo",
            "filename": filename
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Errore eliminazione file {filename}: {e}")
        raise HTTPException(status_code=500, detail=f"Errore eliminazione file: {str(e)}")


@router.delete("/delete-all")
async def delete_all_output_files(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Elimina TUTTI i file dalla cartella outputs

    Returns:
        {"message": "...", "deleted_count": N}
    """
    try:
        output_dir = settings.output_dir

        if not output_dir.exists():
            return {
                "message": "Nessun file da eliminare",
                "deleted_count": 0
            }

        deleted_count = 0

        # Elimina tutti i file
        for file_path in output_dir.iterdir():
            if file_path.is_file():
                try:
                    file_path.unlink()
                    deleted_count += 1
                except Exception as e:
                    logger.warning(f"⚠️ Impossibile eliminare {file_path}: {e}")

        logger.info(f"🗑️ Eliminati {deleted_count} file da user {current_user.id}")

        return {
            "message": f"{deleted_count} file eliminati con successo",
            "deleted_count": deleted_count
        }

    except Exception as e:
        logger.error(f"Errore eliminazione tutti i file: {e}")
        raise HTTPException(status_code=500, detail=f"Errore eliminazione file: {str(e)}")


@router.get("/download/{filename}")
async def download_output_file(
    filename: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Download file dalla cartella outputs

    Args:
        filename: Nome del file da scaricare
    """
    try:
        # Validazione: previeni path traversal
        if '..' in filename or '/' in filename or '\\' in filename:
            raise HTTPException(status_code=400, detail="Nome file non valido")

        file_path = settings.output_dir / filename

        # Verifica che esista
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="File non trovato")

        # Verifica che sia dentro output_dir (security check)
        if not str(file_path.resolve()).startswith(str(settings.output_dir.resolve())):
            raise HTTPException(status_code=403, detail="Accesso negato")

        logger.info(f"📥 Download file da user {current_user.id}: {filename}")

        return FileResponse(
            path=str(file_path),
            media_type="video/mp4",
            filename=filename
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Errore download file {filename}: {e}")
        raise HTTPException(status_code=500, detail=f"Errore download: {str(e)}")
