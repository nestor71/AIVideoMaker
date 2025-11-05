"""
Pipeline Model - Gestione pipeline automatiche
===============================================
CORE della funzionalità AUTO: orchestrazione job in sequenza.

Esempio Pipeline AUTO:
1. Upload video
2. Chromakey processing
3. Thumbnail generation
4. Translation
5. YouTube upload

Ogni step è un Job collegato alla Pipeline.
"""

from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, ForeignKey, Text, JSON, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum

from app.core.database import Base


class PipelineStatus(str, enum.Enum):
    """Stati pipeline"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


class Pipeline(Base):
    """
    Modello Pipeline - Orchestrazione automatica job

    Una pipeline esegue N job in sequenza, passando output di uno
    come input del successivo.
    """

    __tablename__ = "pipelines"

    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    # Foreign Key
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    # Pipeline info
    name = Column(String, nullable=False, comment="Nome descrittivo pipeline")
    description = Column(Text, nullable=True)

    # Status
    status = Column(SQLEnum(PipelineStatus), default=PipelineStatus.PENDING, nullable=False, index=True)

    # Configurazione steps
    steps = Column(JSON, nullable=False, comment="""
        Lista step pipeline. Formato:
        [
            {
                "step_number": 1,
                "job_type": "chromakey",
                "enabled": true,
                "parameters": {...}
            },
            {
                "step_number": 2,
                "job_type": "thumbnail",
                "enabled": true,
                "parameters": {...}
            },
            ...
        ]
    """)

    # Esecuzione
    current_step = Column(Integer, default=0, comment="Step corrente (0 = non iniziato)")
    total_steps = Column(Integer, nullable=False, comment="Totale step pipeline")

    # Progress
    progress = Column(Integer, default=0, comment="Progresso globale 0-100")
    message = Column(Text, nullable=True)

    # Input/Output globali pipeline
    input_files = Column(JSON, nullable=True, comment="File input iniziali")
    output_files = Column(JSON, nullable=True, comment="File output finali")

    # Risultato
    result = Column(JSON, nullable=True, comment="Risultato finale pipeline")
    error = Column(Text, nullable=True)

    # Opzioni
    stop_on_error = Column(Boolean, default=True, comment="Ferma pipeline al primo errore")
    auto_cleanup = Column(Boolean, default=True, comment="Elimina file intermedi a fine pipeline")

    # Metriche
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    total_processing_time = Column(Float, nullable=True, comment="Tempo totale (secondi)")

    # Timestamp
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="pipelines")
    jobs = relationship("Job", back_populates="pipeline", order_by="Job.created_at")

    def __repr__(self):
        return f"<Pipeline(id={self.id}, name={self.name}, status={self.status}, step={self.current_step}/{self.total_steps})>"

    @property
    def is_terminal(self) -> bool:
        """Verifica se pipeline è in stato terminale"""
        return self.status in (PipelineStatus.COMPLETED, PipelineStatus.FAILED, PipelineStatus.CANCELLED)

    @property
    def is_active(self) -> bool:
        """Verifica se pipeline è attiva"""
        return self.status in (PipelineStatus.PENDING, PipelineStatus.RUNNING, PipelineStatus.PAUSED)

    @property
    def enabled_steps(self) -> list:
        """Ritorna solo step abilitati"""
        return [step for step in self.steps if step.get("enabled", True)]

    @property
    def next_step(self) -> dict:
        """Ritorna prossimo step da eseguire (None se finito)"""
        enabled = self.enabled_steps
        if self.current_step < len(enabled):
            return enabled[self.current_step]
        return None
