"""
Demo User Setup
===============
Setup automatico utente demo per development mode.

In development mode, crea automaticamente un utente demo
con credenziali predefinite per permettere testing immediato
senza necessità di registrazione manuale.

In production mode, questo modulo è disabilitato.
"""

import logging
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import get_password_hash
from app.models.user import User

logger = logging.getLogger(__name__)

# Credenziali demo (SOLO per development)
DEMO_EMAIL = "demo@aivideomaker.local"
DEMO_PASSWORD = "demo123"  # Password debole OK in dev
DEMO_USERNAME = "demo"


def setup_demo_user(db: Session) -> bool:
    """
    Setup utente demo per development.

    Crea automaticamente utente demo se:
    1. Environment è development
    2. Utente demo non esiste già

    Args:
        db: Database session

    Returns:
        bool: True se utente demo creato/verificato, False altrimenti
    """
    # Solo in development mode
    if settings.environment == "production":
        logger.info("Production mode: demo user setup disabilitato")
        return False

    try:
        # Verifica se utente demo esiste già
        existing_user = db.query(User).filter(User.email == DEMO_EMAIL).first()

        if existing_user:
            logger.info(f"✅ Utente demo già esistente: {DEMO_EMAIL}")

            # Verifica che sia attivo e admin
            if not existing_user.is_active:
                existing_user.is_active = True
                db.commit()
                logger.info("   → Utente demo riattivato")

            if not existing_user.is_admin:
                existing_user.is_admin = True
                db.commit()
                logger.info("   → Utente demo promosso ad admin")

            return True

        # Crea nuovo utente demo
        logger.info(f"📝 Creazione utente demo: {DEMO_EMAIL}")

        demo_user = User(
            email=DEMO_EMAIL,
            username=DEMO_USERNAME,
            hashed_password=get_password_hash(DEMO_PASSWORD),
            is_active=True,
            is_admin=True,  # Admin per accesso completo in dev
            email_verified=True  # Pre-verificato
        )

        db.add(demo_user)
        db.commit()
        db.refresh(demo_user)

        logger.info("=" * 60)
        logger.info("✅ UTENTE DEMO CREATO CON SUCCESSO")
        logger.info("=" * 60)
        logger.info(f"   Email:    {DEMO_EMAIL}")
        logger.info(f"   Password: {DEMO_PASSWORD}")
        logger.info(f"   Admin:    Sì")
        logger.info("=" * 60)
        logger.info("⚠️  ATTENZIONE: Disabilita demo user in production!")
        logger.info("=" * 60)

        return True

    except Exception as e:
        logger.error(f"❌ Errore setup utente demo: {e}")
        db.rollback()
        return False


def get_demo_credentials() -> dict:
    """
    Ritorna credenziali demo per auto-login.

    Returns:
        dict: Credenziali demo se in development, None altrimenti
    """
    if settings.environment == "production":
        return None

    return {
        "email": DEMO_EMAIL,
        "password": DEMO_PASSWORD,
        "username": DEMO_USERNAME
    }
