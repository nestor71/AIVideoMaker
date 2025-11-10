"""
Refresh Token Model
===================
Modello per gestire refresh tokens persistenti.
"""

from sqlalchemy import Column, String, DateTime, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.core.database import Base


class RefreshToken(Base):
    """
    Refresh Token per session management sicura.

    Ogni utente può avere multipli refresh token attivi (per dispositivi diversi).
    """
    __tablename__ = "refresh_tokens"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Token hash (non salviamo token in chiaro!)
    token_hash = Column(String(64), unique=True, nullable=False, index=True)

    # User relationship
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    user = relationship("User", back_populates="refresh_tokens")

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    last_used_at = Column(DateTime, default=datetime.utcnow)

    # Device/client info
    device_info = Column(String(255), nullable=True)
    ip_address = Column(String(45), nullable=True)  # IPv6 support
    user_agent = Column(String(500), nullable=True)

    # Status
    is_revoked = Column(Boolean, default=False, nullable=False)
    revoked_at = Column(DateTime, nullable=True)

    def __repr__(self):
        return f"<RefreshToken user_id={self.user_id} expires_at={self.expires_at}>"

    @property
    def is_expired(self) -> bool:
        """Check se token è scaduto"""
        return datetime.utcnow() > self.expires_at

    @property
    def is_valid(self) -> bool:
        """Check se token è valido (non scaduto e non revocato)"""
        return not self.is_expired and not self.is_revoked
