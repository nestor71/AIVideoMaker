"""
API Key Model - Gestione API keys
==================================
"""

from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.core.database import Base


class APIKey(Base):
    """Modello API key per autenticazione alternativa"""

    __tablename__ = "api_keys"

    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    # Foreign Key
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    # Key
    key = Column(String(64), unique=True, index=True, nullable=False)
    name = Column(String, nullable=False, comment="Nome descrittivo API key")
    description = Column(Text, nullable=True)

    # Status
    is_active = Column(Boolean, default=True)

    # Usage tracking
    last_used_at = Column(DateTime, nullable=True)
    usage_count = Column(Integer, default=0)

    # Timestamp
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=True, comment="Scadenza key (NULL = mai)")

    # Relationships
    user = relationship("User", back_populates="api_keys")

    def __repr__(self):
        return f"<APIKey(id={self.id}, name={self.name}, user_id={self.user_id})>"
