#!/usr/bin/env python3
"""
Database Migration - Aggiungi campi subscription a User
========================================================
Esegui questo script DOPO aver aggiornato il modello User

Usage:
    python migrate_db_subscription.py
"""

from app.core.database import SessionLocal, engine
from app.models.user import User
from sqlalchemy import text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate():
    """Applica migration per campi subscription"""
    db = SessionLocal()

    try:
        logger.info("=" * 60)
        logger.info("🔄 Avvio migration database...")
        logger.info("=" * 60)

        # Check se le colonne esistono già
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'users'
                AND column_name IN ('subscription_start', 'subscription_end', 'subscription_tier', 'total_spent')
            """))

            existing_columns = [row[0] for row in result]

            if len(existing_columns) == 4:
                logger.info("✅ Colonne subscription già esistenti. Nessuna migration necessaria.")
                return

            logger.info(f"📋 Colonne esistenti trovate: {existing_columns}")
            logger.info("🔧 Creo colonne mancanti...")

            # Crea tabelle da modelli (include nuove colonne)
            from app.core.database import Base
            from app.models import user, job, pipeline, api_key, file_metadata, user_settings, usage_log

            Base.metadata.create_all(bind=engine)

            logger.info("✅ Migration completata!")
            logger.info("")
            logger.info("📊 Verifica tabelle create:")
            logger.info(f"   - users (con campi subscription)")
            logger.info(f"   - usage_logs (nuova tabella per tracking)")
            logger.info("")
            logger.info("🎉 Database aggiornato con successo!")

    except Exception as e:
        logger.error(f"❌ Errore durante migration: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    migrate()
