"""
Job Model - Gestione job elaborazione
======================================
Job per chromakey, traduzione, thumbnails, etc.
"""

from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, ForeignKey, Text, JSON, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum

from app.core.database import Base


class JobType(str, enum.Enum):
    """Tipi di job disponibili"""
    CHROMAKEY = "chromakey"
    TRANSLATION = "translation"
    THUMBNAIL = "thumbnail"
    YOUTUBE_UPLOAD = "youtube_upload"
    SCREEN_RECORD = "screen_record"
    METADATA_EXTRACTION = "metadata_extraction"  # Renamed from METADATA_GENERATION for clarity
    LOGO_OVERLAY = "logo_overlay"
    TRANSCRIPTION = "transcription"
    SEO_METADATA = "seo_metadata"


class JobStatus(str, enum.Enum):
    """Stati job"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Job(Base):
    """Modello job elaborazione video/immagini"""

    __tablename__ = "jobs"

    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    # Foreign Key
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    pipeline_id = Column(UUID(as_uuid=True), ForeignKey("pipelines.id"), nullable=True, comment="NULL se job standalone")

    # Job info
    job_type = Column(SQLEnum(JobType), nullable=False, index=True)
    status = Column(SQLEnum(JobStatus), default=JobStatus.PENDING, nullable=False, index=True)

    # Progress
    progress = Column(Integer, default=0, comment="Progresso 0-100")
    message = Column(Text, nullable=True, comment="Messaggio corrente")

    # Input/Output
    input_files = Column(JSON, nullable=True, comment="Lista file input {file_id: path}")
    output_files = Column(JSON, nullable=True, comment="Lista file output {file_id: path}")

    # Parametri job (JSON flessibile per ogni tipo)
    parameters = Column(JSON, nullable=False, default={}, comment="Parametri specifici job")

    # Risultato
    result = Column(JSON, nullable=True, comment="Risultato elaborazione")
    error = Column(Text, nullable=True, comment="Messaggio errore se failed")

    # Metriche
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    processing_time = Column(Float, nullable=True, comment="Tempo elaborazione (secondi)")

    # Timestamp
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="jobs")
    pipeline = relationship("Pipeline", back_populates="jobs")

    def __repr__(self):
        return f"<Job(id={self.id}, type={self.job_type}, status={self.status})>"

    @property
    def is_terminal(self) -> bool:
        """Verifica se job è in stato terminale (completato/fallito/cancellato)"""
        return self.status in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED)

    @property
    def is_active(self) -> bool:
        """Verifica se job è attivo (pending/processing)"""
        return self.status in (JobStatus.PENDING, JobStatus.PROCESSING)
