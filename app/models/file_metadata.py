"""
File Metadata Model - Tracking file caricati
============================================
"""

from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Boolean, Float
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.core.database import Base


class FileMetadata(Base):
    """Metadata file caricati/generati"""

    __tablename__ = "file_metadata"

    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    # Foreign Key
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    # File info
    filename = Column(String, nullable=False)
    original_filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False, unique=True)
    file_size = Column(Integer, nullable=False, comment="Dimensione in bytes")
    mime_type = Column(String, nullable=False)

    # Tipo file
    file_type = Column(String, nullable=False, index=True, comment="video, image, audio, etc")

    # Hash per dedup
    file_hash = Column(String(64), nullable=True, index=True, comment="SHA256 hash")

    # Status
    is_temporary = Column(Boolean, default=False, comment="File temporaneo da eliminare")
    is_deleted = Column(Boolean, default=False)

    # Expiry
    expires_at = Column(DateTime, nullable=True, comment="Scadenza file temporanei")

    # Timestamp
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    accessed_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User")

    def __repr__(self):
        return f"<FileMetadata(id={self.id}, filename={self.filename}, type={self.file_type})>"
