"""
Database Setup - PostgreSQL + SQLAlchemy
=========================================
Configurazione database con async support e session management.
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from typing import Generator
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)

# Create SQLAlchemy engine
engine = create_engine(
    settings.database_url,
    echo=settings.database_echo,
    pool_pre_ping=True,  # Verifica connessione prima di usarla
    pool_size=10,
    max_overflow=20
)

# Session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# Base class per modelli
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """
    Dependency per ottenere database session.
    Uso in FastAPI routes con Depends(get_db).

    Yields:
        Session: Database session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    Inizializza database creando tutte le tabelle.
    Chiamare all'avvio app.
    """
    try:
        # Import tutti i modelli per creare tabelle
        from app.models import (
            user, job, pipeline, api_key, file_metadata, user_settings, usage_log, admin_audit_log
        )

        logger.info("Creazione tabelle database...")
        Base.metadata.create_all(bind=engine)
        logger.info("Database inizializzato con successo!")

    except Exception as e:
        logger.error(f"Errore inizializzazione database: {e}")
        raise


def drop_db():
    """
    ATTENZIONE: Elimina tutte le tabelle.
    Solo per development/testing.
    """
    if settings.environment == "production":
        raise RuntimeError("NEVER drop database in production!")

    logger.warning("Eliminazione tutte tabelle database...")
    Base.metadata.drop_all(bind=engine)
    logger.info("Database resettato.")
