"""
User Settings Model - Gestione impostazioni utente
===================================================
Salva preferenze e stato UI per ogni utente
"""

from sqlalchemy import Column, String, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.core.database import Base
from app.core.types import UUID


class UserSettings(Base):
    """Modello impostazioni utente - salva stato UI e preferenze"""

    __tablename__ = "user_settings"

    # Primary Key
    id = Column(UUID(), primary_key=True, default=uuid.uuid4, index=True)

    # Foreign Key
    user_id = Column(UUID(), ForeignKey("users.id"), nullable=False, unique=True, index=True)

    # Settings (JSON flessibile - può contenere qualsiasi cosa)
    settings = Column(
        JSON,
        nullable=False,
        default={},
        comment="Impostazioni UI e preferenze utente (JSON flessibile)"
    )

    # Timestamp
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", backref="settings")

    def __repr__(self):
        return f"<UserSettings(user_id={self.user_id})>"


# ==================== DEFAULT SETTINGS ====================

DEFAULT_SETTINGS = {
    # Current UI state
    "ui_state": {
        "current_tab": "chromakey",
        "current_subtab": None,
        "last_video_path": None,
        "last_video_name": None
    },

    # Chromakey preferences
    "chromakey": {
        "green_color": "#00ff00",
        "threshold": 30,
        "background_type": "color",
        "background_color": "#ffffff",
        "background_image": None,
        "background_video": None
    },

    # Logo Overlay preferences
    "logo": {
        "logo_path": None,
        "position": "top-right",
        "size": 15,
        "opacity": 100
    },

    # Translation preferences
    "translation": {
        "source_language": "auto",
        "target_language": "it",
        "voice_id": "21m00Tcm4TlvDq8ikWAM",
        "preserve_original_audio": False,
        "model": "eleven_multilingual_v2"
    },

    # Transcription preferences
    "transcription": {
        "language": "auto",
        "model_size": "base",
        "output_format": "srt"
    },

    # SEO Metadata preferences
    "seo_metadata": {
        "target_platform": "youtube",
        "language": "it",
        "num_hashtags": 10,
        "num_tags": 30,
        "generate_thumbnail": True,
        "thumbnail_style": "modern"
    },

    # YouTube Upload preferences
    "youtube": {
        "title": "",
        "description": "",
        "tags": "",
        "category": "22",
        "privacy": "private",
        "auto_publish": False,
        "playlist_id": None
    },

    # Video Download preferences
    "video_download": {
        "quality": "best",
        "format": "mp4",
        "audio_only": False,
        "subtitles": False
    },

    # Screen Recorder preferences
    "screen_recorder": {
        "video_quality": "high",
        "fps": 30,
        "audio_source": "system",
        "include_microphone": False
    },

    # Pipeline Orchestrator state
    "pipeline": {
        "last_source": None,
        "last_steps": [],
        "favorite_templates": []
    },

    # Thumbnail Generator preferences
    "thumbnail": {
        "style": "modern",
        "overlay_text": True,
        "font_size": 48,
        "text_color": "#ffffff",
        "text_position": "center"
    }
}
