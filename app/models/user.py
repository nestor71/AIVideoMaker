"""
User Model - Gestione utenti
=============================
"""

from sqlalchemy import Column, String, Boolean, DateTime, Numeric
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.core.database import Base
from app.core.types import UUID


class User(Base):
    """Modello utente applicazione"""

    __tablename__ = "users"

    # Primary Key
    id = Column(UUID(), primary_key=True, default=uuid.uuid4, index=True)

    # Credenziali
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)

    # Info utente
    full_name = Column(String, nullable=True)

    # Permessi
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    is_verified = Column(Boolean, default=False)

    # Timestamp
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    last_login_at = Column(DateTime, nullable=True)

    # Subscription (per future subscription system)
    subscription_start = Column(DateTime, nullable=True)
    subscription_end = Column(DateTime, nullable=True)
    subscription_tier = Column(String, default='free', nullable=False)  # 'free', 'basic', 'pro', 'enterprise'
    total_spent = Column(Numeric(10, 2), default=0.00, nullable=False)  # Importo totale speso in EUR

    # Relationships
    api_keys = relationship("APIKey", back_populates="user", cascade="all, delete-orphan")
    jobs = relationship("Job", back_populates="user", cascade="all, delete-orphan")
    pipelines = relationship("Pipeline", back_populates="user", cascade="all, delete-orphan")
    usage_logs = relationship("UsageLog", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(id={self.id}, email={self.email}, username={self.username})>"
