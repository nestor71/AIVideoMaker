"""
Scheduled Job Model - Job di registrazione programmati
======================================================
Gestisce job di screen recording programmati per avvio futuro
"""

from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, JSON, Enum as SQLEnum, Boolean
from app.core.types import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum

from app.core.database import Base


class ScheduledJobStatus(str, enum.Enum):
    """Stati job schedulato"""
    SCHEDULED = "scheduled"  # In attesa di avvio
    RUNNING = "running"      # In esecuzione
    COMPLETED = "completed"  # Completato con successo
    FAILED = "failed"        # Fallito
    CANCELLED = "cancelled"  # Cancellato manualmente


class ScheduledJob(Base):
    """
    Modello per job di registrazione programmati

    Un ScheduledJob viene creato quando l'utente programma una registrazione
    per un orario futuro. Quando il momento arriva, APScheduler avvia la
    registrazione e crea un Job normale (screen_record) collegato.
    """

    __tablename__ = "scheduled_jobs"

    # Primary Key
    id = Column(UUID(), primary_key=True, default=uuid.uuid4, index=True)

    # Foreign Keys
    user_id = Column(UUID(), ForeignKey("users.id"), nullable=False, index=True)
    job_id = Column(UUID(), ForeignKey("jobs.id"), nullable=True, comment="Job creato quando parte la registrazione")

    # Scheduling info
    scheduled_time = Column(DateTime, nullable=False, index=True, comment="Quando deve partire")
    duration_seconds = Column(Integer, nullable=False, comment="Durata massima registrazione")

    # Status
    status = Column(SQLEnum(ScheduledJobStatus), default=ScheduledJobStatus.SCHEDULED, nullable=False, index=True)

    # Parametri registrazione (come ScreenRecordRequest)
    parameters = Column(JSON, nullable=False, comment="Parametri per la registrazione")

    # APScheduler job ID
    scheduler_job_id = Column(String(255), nullable=True, unique=True, comment="ID job in APScheduler")

    # Risultato/errore
    error_message = Column(String(1000), nullable=True)
    output_path = Column(String(500), nullable=True, comment="Path del video registrato")

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    started_at = Column(DateTime, nullable=True, comment="Quando è effettivamente partita")
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", backref="scheduled_jobs")
    job = relationship("Job", foreign_keys=[job_id], backref="scheduled_recording")

    def __repr__(self):
        return f"<ScheduledJob(id={self.id}, scheduled_time={self.scheduled_time}, status={self.status})>"

    @property
    def is_active(self) -> bool:
        """Verifica se è ancora schedulato o in esecuzione"""
        return self.status in (ScheduledJobStatus.SCHEDULED, ScheduledJobStatus.RUNNING)

    @property
    def can_cancel(self) -> bool:
        """Verifica se può essere cancellato"""
        return self.status == ScheduledJobStatus.SCHEDULED

    @property
    def time_until_start(self) -> int:
        """Secondi mancanti all'avvio (negativo se già passato)"""
        if self.status != ScheduledJobStatus.SCHEDULED:
            return 0
        delta = self.scheduled_time - datetime.utcnow()
        return int(delta.total_seconds())
