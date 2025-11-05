"""
Security Module - Autenticazione e Autorizzazione
=================================================
JWT tokens, password hashing, API keys management.
"""

from datetime import datetime, timedelta
from typing import Optional, Any
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, APIKeyHeader
from sqlalchemy.orm import Session
import secrets

from app.core.config import settings
from app.core.database import get_db

# Password hashing context
# Usiamo Argon2 invece di bcrypt (più moderno, vincitore PHC 2015)
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

# Security schemes
bearer_scheme = HTTPBearer()
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica password contro hash"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    Hash password con Argon2

    Argon2 è più sicuro di bcrypt (vincitore PHC 2015) e non ha limiti di lunghezza.
    """
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Crea JWT access token

    Args:
        data: Payload del token (es: {"sub": user_id})
        expires_delta: Durata token (default da config)

    Returns:
        str: JWT token encoded
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)

    to_encode.update({"exp": expire, "iat": datetime.utcnow()})

    encoded_jwt = jwt.encode(
        to_encode,
        settings.secret_key,
        algorithm=settings.algorithm
    )

    return encoded_jwt


def decode_access_token(token: str) -> Optional[dict]:
    """
    Decodifica e valida JWT token

    Args:
        token: JWT token string

    Returns:
        dict: Payload token se valido, None altrimenti
    """
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.algorithm]
        )
        return payload
    except JWTError:
        return None


def generate_api_key() -> str:
    """
    Genera API key sicura random

    Returns:
        str: API key (32 caratteri hex)
    """
    return secrets.token_hex(32)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(bearer_scheme),
    db: Session = Depends(get_db)
) -> Any:
    """
    Dependency per ottenere utente corrente da JWT token.

    Args:
        credentials: Bearer token da header Authorization
        db: Database session

    Returns:
        User: Utente autenticato

    Raises:
        HTTPException: Se token invalido o utente non trovato
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        token = credentials.credentials
        payload = decode_access_token(token)

        if payload is None:
            raise credentials_exception

        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception

    except Exception:
        raise credentials_exception

    # Import qui per evitare circular import
    from app.models.user import User

    user = db.query(User).filter(User.id == user_id).first()

    if user is None:
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )

    return user


async def get_current_active_user(
    current_user = Depends(get_current_user)
) -> Any:
    """
    Dependency per ottenere utente attivo.

    Args:
        current_user: Utente da get_current_user

    Returns:
        User: Utente attivo

    Raises:
        HTTPException: Se utente non attivo
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    return current_user


async def verify_api_key(
    api_key: Optional[str] = Security(api_key_header),
    db: Session = Depends(get_db)
) -> Any:
    """
    Verifica API key da header X-API-Key.

    Args:
        api_key: API key da header
        db: Database session

    Returns:
        User: Utente associato alla API key

    Raises:
        HTTPException: Se API key invalida
    """
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="API key required"
        )

    # Import qui per evitare circular import
    from app.models.api_key import APIKey

    db_api_key = db.query(APIKey).filter(
        APIKey.key == api_key,
        APIKey.is_active == True
    ).first()

    if not db_api_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key"
        )

    # Aggiorna last_used
    db_api_key.last_used_at = datetime.utcnow()
    db.commit()

    return db_api_key.user


def require_admin(current_user = Depends(get_current_active_user)) -> Any:
    """
    Dependency per verificare che utente sia admin.

    Args:
        current_user: Utente corrente

    Returns:
        User: Utente admin

    Raises:
        HTTPException: Se utente non è admin
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    return current_user
