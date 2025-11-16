"""
File Service
============
Servizio per gestione file: cleanup, validazione, tracking
"""

import os
import logging
from pathlib import Path
from typing import Set, List, Optional
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.pipeline import Pipeline

logger = logging.getLogger(__name__)


def extract_files_from_pipeline(pipeline: Pipeline) -> Set[str]:
    """
    Estrae tutti i file necessari dalla pipeline

    Args:
        pipeline: Pipeline da analizzare

    Returns:
        Set di path assoluti dei file necessari
    """
    necessary_files = set()

    # Analizza tutti gli step della pipeline
    for step in pipeline.steps:
        if not step.get("enabled", True):
            continue

        parameters = step.get("parameters", {})

        # Lista di parametri comuni che contengono path a file
        file_params = [
            "foreground_video", "background_video", "video_path",
            "image_path", "logo_path", "input_video", "source_video",
            "video", "image", "audio_path", "subtitle_path"
        ]

        for param in file_params:
            if param in parameters:
                file_value = parameters[param]

                # Salta riferimenti speciali (@previous, @step1, etc.)
                if isinstance(file_value, str) and file_value.startswith("@"):
                    continue

                # Se è un path, aggiungilo al set
                if isinstance(file_value, str):
                    file_path = Path(file_value)

                    # Se è un path relativo, considera solo se è nella cartella upload
                    if not file_path.is_absolute():
                        file_path = settings.upload_dir / file_value

                    # Aggiungi solo se il file è nella cartella upload
                    try:
                        if file_path.exists() and str(file_path.resolve()).startswith(str(settings.upload_dir.resolve())):
                            necessary_files.add(str(file_path.resolve()))
                    except Exception as e:
                        logger.warning(f"Errore validazione path {file_path}: {e}")
                        continue

    return necessary_files


def cleanup_upload_folder(pipeline: Pipeline, db: Session) -> dict:
    """
    Pulisce la cartella upload mantenendo solo i file necessari per la pipeline corrente

    Args:
        pipeline: Pipeline da eseguire
        db: Database session

    Returns:
        Dict con statistiche cleanup: {
            "deleted_count": int,
            "deleted_files": List[str],
            "kept_count": int,
            "kept_files": List[str],
            "total_freed_bytes": int
        }
    """
    try:
        upload_dir = settings.upload_dir.resolve()

        # Verifica che la directory esista
        if not upload_dir.exists():
            logger.warning(f"Cartella upload non esiste: {upload_dir}")
            return {
                "deleted_count": 0,
                "deleted_files": [],
                "kept_count": 0,
                "kept_files": [],
                "total_freed_bytes": 0
            }

        # Estrai file necessari per questa pipeline
        necessary_files = extract_files_from_pipeline(pipeline)

        logger.info(f"🔍 Cleanup upload folder: {len(necessary_files)} file necessari per pipeline '{pipeline.name}'")

        # Scansiona la cartella upload
        deleted_files = []
        kept_files = []
        total_freed_bytes = 0

        for file_path in upload_dir.iterdir():
            # Salta directory
            if file_path.is_dir():
                continue

            absolute_path = str(file_path.resolve())

            # Se il file è necessario, mantienilo
            if absolute_path in necessary_files:
                kept_files.append(file_path.name)
                logger.debug(f"  ✓ Mantenuto: {file_path.name}")
            else:
                # File non necessario, elimina
                try:
                    file_size = file_path.stat().st_size
                    os.remove(file_path)
                    deleted_files.append(file_path.name)
                    total_freed_bytes += file_size
                    logger.info(f"  🗑️  Eliminato: {file_path.name} ({file_size / 1024 / 1024:.2f}MB)")
                except Exception as e:
                    logger.error(f"  ❌ Errore eliminazione {file_path.name}: {e}")

        result = {
            "deleted_count": len(deleted_files),
            "deleted_files": deleted_files,
            "kept_count": len(kept_files),
            "kept_files": kept_files,
            "total_freed_bytes": total_freed_bytes
        }

        logger.info(
            f"✅ Cleanup completato: {result['deleted_count']} file eliminati "
            f"({total_freed_bytes / 1024 / 1024:.2f}MB liberati), "
            f"{result['kept_count']} file mantenuti"
        )

        return result

    except Exception as e:
        logger.error(f"❌ Errore durante cleanup upload folder: {e}")
        return {
            "deleted_count": 0,
            "deleted_files": [],
            "kept_count": 0,
            "kept_files": [],
            "total_freed_bytes": 0,
            "error": str(e)
        }


def cleanup_all_upload_folder() -> dict:
    """
    Pulisce COMPLETAMENTE la cartella upload (elimina tutti i file)

    ⚠️ ATTENZIONE: Questa funzione elimina TUTTI i file nella cartella upload.
    Da usare solo per pulizia manuale completa.

    Returns:
        Dict con statistiche cleanup
    """
    try:
        upload_dir = settings.upload_dir.resolve()

        if not upload_dir.exists():
            return {
                "deleted_count": 0,
                "deleted_files": [],
                "total_freed_bytes": 0
            }

        deleted_files = []
        total_freed_bytes = 0

        for file_path in upload_dir.iterdir():
            if file_path.is_dir():
                continue

            try:
                file_size = file_path.stat().st_size
                os.remove(file_path)
                deleted_files.append(file_path.name)
                total_freed_bytes += file_size
                logger.info(f"  🗑️  Eliminato: {file_path.name}")
            except Exception as e:
                logger.error(f"  ❌ Errore eliminazione {file_path.name}: {e}")

        logger.info(
            f"✅ Cleanup completo: {len(deleted_files)} file eliminati "
            f"({total_freed_bytes / 1024 / 1024:.2f}MB liberati)"
        )

        return {
            "deleted_count": len(deleted_files),
            "deleted_files": deleted_files,
            "total_freed_bytes": total_freed_bytes
        }

    except Exception as e:
        logger.error(f"❌ Errore durante cleanup completo: {e}")
        return {
            "deleted_count": 0,
            "deleted_files": [],
            "total_freed_bytes": 0,
            "error": str(e)
        }
