"""
API Routes
==========
Tutti i router API dell'applicazione
"""

from app.api.routes import (
    auth,
    admin,
    chromakey,
    translation,
    thumbnail,
    youtube,
    pipeline,
    metadata,
    logo,
    transcription,
    seo_metadata,
    video_download,
    user_settings,
    files
)

__all__ = [
    "auth",
    "admin",
    "chromakey",
    "translation",
    "thumbnail",
    "youtube",
    "pipeline",
    "metadata",
    "logo",
    "transcription",
    "seo_metadata",
    "video_download",
    "user_settings",
    "files"
]

