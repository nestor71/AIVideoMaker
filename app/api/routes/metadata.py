"""
Metadata Routes
===============
Route per estrazione metadati video/audio
"""

from pathlib import Path
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.config import settings
from app.models.user import User
from app.services.metadata_service import MetadataService, MetadataParams

router = APIRouter()


# ==================== Pydantic Schemas ====================

class MetadataRequest(BaseModel):
    """Schema per richiesta metadati"""
    video_path: str
    include_streams: bool = True
    include_format: bool = True


class MetadataResponse(BaseModel):
    """Schema per risposta metadati"""
    file_path: str
    file_name: str
    file_size_mb: float
    format: Optional[dict] = None
    streams: Optional[dict] = None


# ==================== Routes ====================

@router.post("/extract", response_model=dict)
async def extract_metadata(
    request: MetadataRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Estrai metadati da video/audio

    - **video_path**: Path file video/audio
    - **include_streams**: Include dettagli stream (default: true)
    - **include_format**: Include info formato (default: true)

    Restituisce:
    - Informazioni file (nome, dimensione)
    - Formato container (MP4, AVI, etc.)
    - Stream video (codec, risoluzione, FPS, bitrate)
    - Stream audio (codec, sample rate, canali)
    - Tags metadata

    Richiede JWT token.
    """
    # Valida path
    video_path = Path(request.video_path)
    if not video_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File non trovato: {request.video_path}"
        )

    # Configura servizio
    service = MetadataService(settings)

    # Prepara parametri
    params = MetadataParams(
        video_path=video_path,
        include_streams=request.include_streams,
        include_format=request.include_format
    )

    try:
        # Estrai metadati
        result = service.extract(params)
        return result

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Errore estrazione metadati: {str(e)}"
        )


@router.post("/extract-upload", response_model=dict)
async def extract_metadata_from_upload(
    file: UploadFile = File(..., description="File video/audio"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Upload file ed estrai metadati

    Richiede JWT token.
    """
    # Salva file upload
    file_path = settings.upload_dir / f"meta_{current_user.id}_{file.filename}"

    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)

    # Configura servizio
    service = MetadataService(settings)

    # Prepara parametri
    params = MetadataParams(
        video_path=file_path,
        include_streams=True,
        include_format=True
    )

    try:
        # Estrai metadati
        result = service.extract(params)
        return result

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Errore estrazione metadati: {str(e)}"
        )
    finally:
        # Cleanup file upload
        if file_path.exists():
            file_path.unlink()
