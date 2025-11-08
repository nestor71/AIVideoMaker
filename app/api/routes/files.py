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

from fastapi import APIRouter, UploadFile, File, HTTPException, status
from pydantic import BaseModel

from app.core.config import settings

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


class FileUploadResponse(BaseModel):
    """Schema risposta upload file"""
    file_id: str
    filename: str
    path: str
    size: int
    mime_type: str


@router.post("/upload", response_model=FileUploadResponse)
async def upload_file(file: UploadFile = File(...)):
    """
    Upload generico file video o immagine

    Args:
        file: File da caricare

    Returns:
        FileUploadResponse con dettagli file

    Raises:
        413: File troppo grande
        400: Tipo MIME non supportato
        500: Errore interno
    """
    file_size = 0
    temp_file = None

    try:
        logger.info(f"📤 Inizio upload file: {file.filename}")

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
        if file.filename.startswith('recording_'):
            # Registrazione: usa nome originale
            final_filename = file.filename
            file_id = Path(file.filename).stem  # ID = nome senza estensione
        else:
            # Upload normale: usa UUID
            file_id = str(uuid.uuid4())
            file_extension = Path(file.filename).suffix.lower()
            final_filename = f"{file_id}{file_extension}"

        file_path = settings.upload_dir / final_filename

        # Se file esiste già, sovrascrivi (per registrazioni con stesso timestamp)
        if file_path.exists():
            os.unlink(file_path)

        shutil.move(temp_file.name, file_path)

        logger.info(f"✅ Upload completato: {file.filename} ({file_size / 1024 / 1024:.2f}MB) -> {final_filename}")

        return FileUploadResponse(
            file_id=file_id,
            filename=file.filename,
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
async def get_file_info(path: str):
    """
    Ottieni informazioni su un file caricato

    Args:
        path: Percorso file

    Returns:
        Informazioni file
    """
    try:
        file_path = Path(path)

        if not file_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File non trovato"
            )

        file_size = file_path.stat().st_size
        mime = magic.Magic(mime=True)
        detected_mime = mime.from_file(str(file_path))

        return {
            "filename": file_path.name,
            "path": str(file_path),
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
