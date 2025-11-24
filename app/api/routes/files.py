"""
File Upload Routes
==================
Endpoint generici per upload file video e immagini
"""

import os
import uuid
import shutil
import tempfile
import magic
import logging
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, UploadFile, File, HTTPException, status, Depends, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.file_validator import get_safe_filename
from app.core.security import get_current_user
from app.core.database import get_db
from app.core.limiter import limiter

router = APIRouter()
logger = logging.getLogger(__name__)

# Configurazione upload
MAX_UPLOAD_SIZE = 2 * 1024 * 1024 * 1024  # 2GB
ALLOWED_VIDEO_MIMES = [
    'video/mp4',
    'video/mpeg',
    'video/quicktime',
    'video/x-msvideo',
    'video/x-matroska',
    'video/webm',
    'video/x-flv',
    'video/x-ms-wmv',
]

ALLOWED_IMAGE_MIMES = [
    'image/jpeg',
    'image/png',
    'image/gif',
    'image/webp',
    'image/bmp',
]


def validate_path_in_directory(requested_path: str, allowed_dir: Path) -> Path:
    """
    Valida che il path richiesto sia dentro la directory consentita.
    Previene path traversal attacks (../../etc/passwd).

    Args:
        requested_path: Path richiesto dall'utente
        allowed_dir: Directory consentita

    Returns:
        Path: Path assoluto validato

    Raises:
        HTTPException: Se path non valido o fuori directory consentita
    """
    try:
        # Converti a Path e risolvi symlinks/..
        requested = Path(requested_path).resolve()
        allowed = allowed_dir.resolve()

        # Verifica che il path sia dentro allowed_dir
        if not str(requested).startswith(str(allowed)):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Accesso al path non autorizzato"
            )

        return requested
    except Exception as e:
        logger.error(f"Path validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Path non valido"
        )


class FileUploadResponse(BaseModel):
    """Schema risposta upload file"""
    file_id: str
    filename: str
    path: str
    size: int
    mime_type: str


@router.post("/upload", response_model=FileUploadResponse)
@limiter.limit("10/hour")
async def upload_file(
    request: Request,
    file: UploadFile = File(...),
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Upload generico file video o immagine

    **AUTENTICAZIONE RICHIESTA**
    **RATE LIMIT**: 10 upload/ora per utente

    Args:
        request: Request FastAPI (per rate limiting)
        file: File da caricare
        current_user: Utente autenticato
        db: Database session

    Returns:
        FileUploadResponse con dettagli file

    Raises:
        401: Non autenticato
        413: File troppo grande
        400: Tipo MIME non supportato
        429: Troppi upload (rate limit)
        500: Errore interno
    """
    file_size = 0
    temp_file = None

    try:
        # Sanitizza filename per prevenire path traversal
        safe_filename = get_safe_filename(file.filename)
        logger.info(f"📤 Inizio upload file: {safe_filename}")

        # Leggi file in memoria temporanea per validazione
        temp_file = tempfile.NamedTemporaryFile(delete=False)
        chunk_size = 1024 * 1024  # 1MB chunks

        while True:
            chunk = await file.read(chunk_size)
            if not chunk:
                break
            file_size += len(chunk)

            # Check size limit
            if file_size > MAX_UPLOAD_SIZE:
                temp_file.close()
                os.unlink(temp_file.name)
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail=f"File troppo grande. Max: {MAX_UPLOAD_SIZE / 1024 / 1024:.0f}MB"
                )
            temp_file.write(chunk)

        temp_file.close()

        # Validazione MIME type
        mime = magic.Magic(mime=True)
        detected_mime = mime.from_file(temp_file.name)

        if detected_mime not in ALLOWED_VIDEO_MIMES and detected_mime not in ALLOWED_IMAGE_MIMES:
            os.unlink(temp_file.name)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Tipo MIME non supportato: {detected_mime}. Usa video o immagini."
            )

        # Salva file: se è una registrazione usa nome originale, altrimenti UUID
        if safe_filename.startswith('recording_'):
            # Registrazione: usa nome originale
            final_filename = safe_filename
            file_id = Path(safe_filename).stem  # ID = nome senza estensione
        else:
            # Upload normale: usa UUID
            file_id = str(uuid.uuid4())
            file_extension = Path(safe_filename).suffix.lower()
            final_filename = f"{file_id}{file_extension}"

        file_path = settings.upload_dir / final_filename

        # Se file esiste già, sovrascrivi (per registrazioni con stesso timestamp)
        if file_path.exists():
            os.unlink(file_path)

        shutil.move(temp_file.name, file_path)

        logger.info(f"✅ Upload completato: {safe_filename} ({file_size / 1024 / 1024:.2f}MB) -> {final_filename}")

        return FileUploadResponse(
            file_id=file_id,
            filename=safe_filename,  # Ritorna nome sanitizzato
            path=str(file_path),
            size=file_size,
            mime_type=detected_mime
        )

    except HTTPException:
        raise
    except Exception as e:
        if temp_file and os.path.exists(temp_file.name):
            os.unlink(temp_file.name)
        logger.error(f"❌ Errore upload: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Errore upload: {str(e)}"
        )


@router.get("/file-info")
async def get_file_info(
    path: str,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Ottieni informazioni su un file caricato

    **AUTENTICAZIONE RICHIESTA**
    **PATH VALIDATION**: Il path deve essere dentro la directory uploads

    Args:
        path: Percorso file (relativo o assoluto)
        current_user: Utente autenticato
        db: Database session

    Returns:
        Informazioni file

    Raises:
        401: Non autenticato
        403: Path non autorizzato (fuori uploads directory)
        404: File non trovato
    """
    try:
        # Valida che il path sia dentro la directory consentita
        validated_path = validate_path_in_directory(path, settings.upload_dir)

        if not validated_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File non trovato"
            )

        file_size = validated_path.stat().st_size
        mime = magic.Magic(mime=True)
        detected_mime = mime.from_file(str(validated_path))

        return {
            "filename": validated_path.name,
            "path": str(validated_path),
            "size": file_size,
            "mime_type": detected_mime,
            "exists": True
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Errore get_file_info: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
