"""
Admin Audit Logger
===================
Helper per tracciare azioni amministrative.

Usage:
    from app.core.admin_audit import log_admin_action

    log_admin_action(
        db=db,
        admin_user=current_admin,
        action='user.promote_admin',
        target_type='user',
        target_id=user.id,
        target_identifier=user.username,
        details={'reason': 'CEO request'},
        request=request  # Opzionale, per IP e user agent
    )
"""

import logging
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from fastapi import Request

from app.models.admin_audit_log import AdminAuditLog
from app.models.user import User

logger = logging.getLogger(__name__)


def log_admin_action(
    db: Session,
    admin_user: User,
    action: str,
    target_type: Optional[str] = None,
    target_id: Optional[str] = None,
    target_identifier: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    request: Optional[Request] = None
):
    """
    Log azione amministrativa

    Args:
        db: Database session
        admin_user: Utente admin che esegue l'azione
        action: Tipo azione (es. 'user.delete', 'user.promote_admin')
        target_type: Tipo entità target ('user', 'system', etc.)
        target_id: ID entità target
        target_identifier: Identificatore human-readable target (username, email)
        details: Dettagli extra in JSON
        request: FastAPI Request per estrarre IP e user agent

    Example:
        ```python
        log_admin_action(
            db=db,
            admin_user=current_admin,
            action='user.delete',
            target_type='user',
            target_id=deleted_user.id,
            target_identifier=deleted_user.username,
            details={
                'deleted_resources': {'jobs': 10, 'pipelines': 5}
            },
            request=request
        )
        ```

    Actions common:
        - user.view
        - user.create
        - user.update
        - user.delete
        - user.activate / user.deactivate
        - user.promote_admin / user.demote_admin
        - subscription.update
        - system.export_users
        - system.access_stats
    """
    try:
        audit_log = AdminAuditLog(
            admin_user_id=admin_user.id,
            admin_username=admin_user.username,
            admin_email=admin_user.email,
            action=action,
            target_type=target_type,
            target_id=target_id,
            target_identifier=target_identifier,
            details=details,
            ip_address=request.client.host if request else None,
            user_agent=request.headers.get('user-agent') if request else None
        )

        db.add(audit_log)
        db.commit()

        logger.info(
            f"🔐 AUDIT: {admin_user.username} executed '{action}' "
            f"on {target_type}:{target_identifier or target_id}"
        )

    except Exception as e:
        logger.error(f"❌ Errore logging admin action: {e}")
        db.rollback()
        # Non fallire l'operazione principale se logging audit fallisce
