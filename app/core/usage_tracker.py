"""
Usage Tracker - Helper per tracciare azioni utente
==================================================
Funzioni utility per registrare usage logs in modo semplice
"""

from sqlalchemy.orm import Session
from fastapi import Request
from typing import Optional, Dict, Any
from uuid import UUID

from app.models.usage_log import UsageLog


def track_action(
    db: Session,
    user_id: UUID,
    action_type: str,
    action_details: Optional[Dict[str, Any]] = None,
    request: Optional[Request] = None
):
    """
    Traccia un'azione utente nel database.

    Args:
        db: Database session
        user_id: ID dell'utente che compie l'azione
        action_type: Tipo azione ('chromakey', 'video_download', 'audio_transcribe', etc.)
        action_details: Dettagli extra (opzionale, JSON)
        request: FastAPI Request per estrarre IP e user agent (opzionale)

    Tipi azione supportati:
        - chromakey: Applicazione chromakey
        - video_download: Download video da URL
        - audio_transcribe: Trascrizione audio
        - seo_analyze: Analisi SEO video
        - youtube_upload: Upload su YouTube
        - screen_record: Registrazione schermo
        - pipeline_run: Esecuzione pipeline
        - translation: Traduzione video
        - metadata_generate: Generazione metadata

    Example:
        ```python
        from app.core.usage_tracker import track_action

        # Traccia chromakey
        track_action(
            db=db,
            user_id=current_user.id,
            action_type='chromakey',
            action_details={'video_id': video_id, 'duration': 120},
            request=request
        )
        ```
    """
    try:
        log = UsageLog(
            user_id=user_id,
            action_type=action_type,
            action_details=action_details,
            ip_address=request.client.host if request else None,
            user_agent=request.headers.get('user-agent') if request else None
        )

        db.add(log)
        db.commit()

    except Exception as e:
        # Non vogliamo che il tracking blocchi l'operazione principale
        # Logga errore ma non propagare
        import logging
        logging.error(f"Errore tracking action '{action_type}' per user {user_id}: {e}")
        db.rollback()
