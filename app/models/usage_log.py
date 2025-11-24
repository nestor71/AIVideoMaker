"""
Usage Log Model - Tracciamento utilizzo funzionalità
====================================================
Registra ogni azione degli utenti per statistiche admin
"""

from sqlalchemy import Column, String, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.core.database import Base
from app.core.types import UUID


class UsageLog(Base):
    """Log utilizzo funzionalità applicazione"""

    __tablename__ = "usage_logs"

    # Primary Key
    id = Column(UUID(), primary_key=True, default=uuid.uuid4, index=True)

    # User reference
    user_id = Column(UUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Azione tracciata
    action_type = Column(String, nullable=False, index=True)  # 'chromakey', 'video_download', 'audio_transcribe', 'seo_analyze', 'youtube_upload', 'screen_record', 'pipeline_run'
    action_details = Column(JSON, nullable=True)  # Dettagli extra (es. video_id, duration, source, etc.)

    # Timestamp
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # IP e User Agent (opzionale, per analytics avanzato)
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)

    # Relationship
    user = relationship("User", back_populates="usage_logs")

    def __repr__(self):
        return f"<UsageLog(id={self.id}, user_id={self.user_id}, action={self.action_type}, time={self.timestamp})>"
