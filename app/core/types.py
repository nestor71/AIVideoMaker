"""
Custom SQLAlchemy Types
========================
Tipi personalizzati compatibili con tutti i database.
"""

from sqlalchemy import TypeDecorator, CHAR
from sqlalchemy.dialects.postgresql import UUID as pgUUID
import uuid


class UUID(TypeDecorator):
    """
    UUID type che funziona sia con PostgreSQL che SQLite.

    - PostgreSQL: usa UUID nativo
    - SQLite: usa CHAR(36) con conversione automatica
    """

    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(pgUUID(as_uuid=True))
        else:
            return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        elif dialect.name == 'postgresql':
            return str(value)
        else:
            if isinstance(value, uuid.UUID):
                return str(value)
            else:
                return str(uuid.UUID(value))

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        else:
            if isinstance(value, uuid.UUID):
                return value
            else:
                return uuid.UUID(value)
