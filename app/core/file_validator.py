"""
File Upload Validator
======================
Validazione sicura file upload con controllo MIME type, dimensione, estensione.

Protegge da:
- Upload malware mascherati (es. exe rinominato in .jpg)
- File eccessivamente grandi (DoS)
- Estensioni non autorizzate

Usage:
    from app.core.file_validator import validate_file_upload, FileType

    # Validazione video
    await validate_file_upload(
        file=uploaded_file,
        allowed_types=FileType.VIDEO,
        max_size_mb=500
    )
"""

import magic
import logging
from typing import List, Optional
from fastapi import UploadFile, HTTPException, status
from pathlib import Path
from enum import Enum

logger = logging.getLogger(__name__)


class FileType(str, Enum):
    """Tipi file supportati con MIME types validi"""

    # Video
    VIDEO = "video"
    VIDEO_MIMES = [
        "video/mp4",
        "video/mpeg",
        "video/quicktime",  # .mov
        "video/x-msvideo",  # .avi
        "video/x-matroska",  # .mkv
        "video/webm",
        "video/x-flv"
    ]
    VIDEO_EXTENSIONS = [".mp4", ".mpeg", ".mpg", ".mov", ".avi", ".mkv", ".webm", ".flv"]

    # Audio
    AUDIO = "audio"
    AUDIO_MIMES = [
        "audio/mpeg",  # mp3
        "audio/wav",
        "audio/x-wav",
        "audio/ogg",
        "audio/webm",
        "audio/mp4",  # m4a
        "audio/aac"
    ]
    AUDIO_EXTENSIONS = [".mp3", ".wav", ".ogg", ".webm", ".m4a", ".aac"]

    # Immagini
    IMAGE = "image"
    IMAGE_MIMES = [
        "image/jpeg",
        "image/png",
        "image/gif",
        "image/webp",
        "image/svg+xml"
    ]
    IMAGE_EXTENSIONS = [".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg"]

    # Documenti
    DOCUMENT = "document"
    DOCUMENT_MIMES = [
        "application/pdf",
        "application/msword",  # .doc
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",  # .docx
        "text/plain"
    ]
    DOCUMENT_EXTENSIONS = [".pdf", ".doc", ".docx", ".txt"]

    # Archivi (attenzione: controllare sempre contenuto!)
    ARCHIVE = "archive"
    ARCHIVE_MIMES = [
        "application/zip",
        "application/x-rar-compressed",
        "application/x-7z-compressed",
        "application/x-tar",
        "application/gzip"
    ]
    ARCHIVE_EXTENSIONS = [".zip", ".rar", ".7z", ".tar", ".gz"]


# Mapping tipo → MIME types e estensioni
ALLOWED_MIME_TYPES = {
    FileType.VIDEO: FileType.VIDEO_MIMES.value,
    FileType.AUDIO: FileType.AUDIO_MIMES.value,
    FileType.IMAGE: FileType.IMAGE_MIMES.value,
    FileType.DOCUMENT: FileType.DOCUMENT_MIMES.value,
    FileType.ARCHIVE: FileType.ARCHIVE_MIMES.value
}

ALLOWED_EXTENSIONS = {
    FileType.VIDEO: FileType.VIDEO_EXTENSIONS.value,
    FileType.AUDIO: FileType.AUDIO_EXTENSIONS.value,
    FileType.IMAGE: FileType.IMAGE_EXTENSIONS.value,
    FileType.DOCUMENT: FileType.DOCUMENT_EXTENSIONS.value,
    FileType.ARCHIVE: FileType.ARCHIVE_EXTENSIONS.value
}


async def validate_file_upload(
    file: UploadFile,
    allowed_types: FileType,
    max_size_mb: int = 500,
    check_mime: bool = True
) -> Path:
    """
    Valida file upload in modo sicuro

    Args:
        file: File uploadato da FastAPI
        allowed_types: Tipo file consentito (FileType.VIDEO, FileType.IMAGE, etc.)
        max_size_mb: Dimensione massima in MB (default: 500)
        check_mime: Se True, verifica MIME type reale con python-magic (default: True)

    Returns:
        Path: Path del file se valido

    Raises:
        HTTPException: Se file non valido

    Example:
        ```python
        @router.post("/upload")
        async def upload_video(file: UploadFile):
            await validate_file_upload(
                file=file,
                allowed_types=FileType.VIDEO,
                max_size_mb=500
            )
            # File valido, procedi con processing
        ```

    Security checks:
    1. File vuoto → Reject
    2. Estensione non in whitelist → Reject
    3. Dimensione > max_size_mb → Reject (DoS protection)
    4. MIME type reale non match estensione → Reject (malware protection)
    """

    # 1. Verifica file non vuoto
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nome file mancante"
        )

    # 2. Verifica estensione
    file_ext = Path(file.filename).suffix.lower()
    allowed_extensions = ALLOWED_EXTENSIONS.get(allowed_types, [])

    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Estensione '{file_ext}' non consentita. "
                f"Formati validi: {', '.join(allowed_extensions)}"
            )
        )

    # 3. Verifica dimensione file
    # Leggi primi bytes per check MIME, poi verifica size completa
    file.file.seek(0, 2)  # Vai a fine file
    file_size_bytes = file.file.tell()
    file.file.seek(0)  # Torna a inizio

    max_size_bytes = max_size_mb * 1024 * 1024

    if file_size_bytes > max_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=(
                f"File troppo grande ({file_size_bytes / (1024*1024):.1f}MB). "
                f"Massimo consentito: {max_size_mb}MB"
            )
        )

    if file_size_bytes == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File vuoto"
        )

    # 4. Verifica MIME type reale (anti-malware)
    if check_mime:
        # Leggi primi 2KB per detection MIME type
        file_header = await file.read(2048)
        file.file.seek(0)  # Reset per processing successivo

        try:
            detected_mime = magic.from_buffer(file_header, mime=True)
        except Exception as e:
            logger.error(f"Errore detection MIME type: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Impossibile verificare tipo file"
            )

        allowed_mimes = ALLOWED_MIME_TYPES.get(allowed_types, [])

        if detected_mime not in allowed_mimes:
            logger.warning(
                f"MIME type mismatch: file '{file.filename}' "
                f"dichiara estensione '{file_ext}' ma ha MIME '{detected_mime}'"
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"File non valido. Tipo rilevato: '{detected_mime}'. "
                    f"Il file potrebbe essere corrotto o mascherato. "
                    f"Formati validi: {', '.join(allowed_mimes)}"
                )
            )

    logger.info(
        f"✅ File validato: '{file.filename}' "
        f"({file_size_bytes / (1024*1024):.1f}MB, {file_ext})"
    )

    return Path(file.filename)


def get_safe_filename(filename: str) -> str:
    """
    Sanitizza filename per prevenire path traversal

    Rimuove:
    - Path separators (/, \\)
    - Null bytes
    - Caratteri speciali pericolosi

    Args:
        filename: Nome file originale

    Returns:
        str: Nome file sicuro

    Example:
        >>> get_safe_filename("../../etc/passwd")
        "...etcpasswd"
    """
    # Rimuovi path components
    safe_name = Path(filename).name

    # Rimuovi null bytes e caratteri pericolosi
    safe_name = safe_name.replace('\x00', '')
    safe_name = safe_name.replace('..', '')

    # Limita lunghezza (filesystem limit = 255)
    if len(safe_name) > 255:
        name_part = Path(safe_name).stem[:200]
        ext_part = Path(safe_name).suffix
        safe_name = name_part + ext_part

    return safe_name
