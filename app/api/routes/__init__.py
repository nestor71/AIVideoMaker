"""
API Routes
==========
Tutti i router API dell'applicazione
"""

from app.api.routes import (
    auth,
    admin,
    chromakey,
    compositor,
    translation,
    thumbnail,
    youtube,
    pipeline,
    metadata,
    logo,
    transcription,
    screen_record,
    seo_metadata,
    video_download,
    user_settings,
    outputs,
    files
)

__all__ = [
    "auth",
    "admin",
    "chromakey",
    "compositor",
    "translation",
    "thumbnail",
    "youtube",
    "pipeline",
    "metadata",
    "logo",
    "transcription",
    "screen_record",
    "seo_metadata",
    "video_download",
    "user_settings",
    "outputs",
    "files"
]
