"""
Admin Audit Log Model
======================
Tracciamento tutte le azioni amministrative per compliance e sicurezza.

Ogni azione admin viene loggata con:
- Chi (admin_user_id)
- Cosa (action)
- Quando (timestamp)
- Su chi/cosa (target_user_id, target_type, target_id)
- Da dove (ip_address)
- Dettagli (details JSON)
"""

from sqlalchemy import Column, String, DateTime, JSON, Text, ForeignKey
from datetime import datetime
import uuid

from app.core.database import Base
from app.core.types import UUID


class AdminAuditLog(Base):
    """
    Log audit azioni amministrative

    Examples:
        - Admin promuove utente a admin
        - Admin elimina utente
        - Admin modifica subscription tier
        - Admin disattiva account
        - Admin accede a dettagli utente sensibili
    """
    __tablename__ = "admin_audit_logs"

    id = Column(UUID(), primary_key=True, default=uuid.uuid4, index=True)

    # Chi ha eseguito l'azione
    admin_user_id = Column(UUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    admin_username = Column(String, nullable=False)  # Denormalizzato per sicurezza (se admin eliminato)
    admin_email = Column(String, nullable=False)  # Denormalizzato

    # Azione eseguita
    action = Column(String, nullable=False, index=True)
    """
    Tipi azione:
    - user.view: Visualizza dettagli utente
    - user.create: Crea nuovo utente
    - user.update: Modifica utente
    - user.delete: Elimina utente
    - user.activate: Attiva utente
    - user.deactivate: Disattiva utente
    - user.promote_admin: Promuove a admin
    - user.demote_admin: Rimuove privilegi admin
    - subscription.update: Modifica subscription
    - system.export_users: Export CSV utenti
    - system.access_stats: Accesso statistiche sistema
    """

    # Target dell'azione (cosa è stato modificato)
    target_type = Column(String, nullable=True, index=True)  # 'user', 'system', 'job', etc.
    target_id = Column(UUID(), nullable=True, index=True)  # ID entità target
    target_identifier = Column(String, nullable=True)  # Username/email target (denormalizzato)

    # Dettagli azione (JSON)
    details = Column(JSON, nullable=True)
    """
    Esempi:
    {
        "changes": {"is_admin": {"old": false, "new": true}},
        "reason": "Promoted to admin by CEO request"
    }
    {
        "user_id": "123",
        "deleted_resources": {"jobs": 10, "pipelines": 5}
    }
    """

    # Metadati richiesta
    ip_address = Column(String, nullable=True)
    user_agent = Column(Text, nullable=True)

    # Timestamp
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    def __repr__(self):
        return (
            f"<AdminAuditLog {self.admin_username} "
            f"{self.action} on {self.target_type}:{self.target_identifier} "
            f"at {self.timestamp}>"
        )
