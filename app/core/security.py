"""
Security Module - Autenticazione e Autorizzazione
=================================================
JWT tokens, password hashing, API keys management.
"""

from datetime import datetime, timedelta
from typing import Optional, Any
from uuid import UUID
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status, Security, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, APIKeyHeader
from sqlalchemy.orm import Session
import secrets
import hashlib

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

        # Converti user_id da stringa a UUID per query SQLAlchemy
        try:
            user_id_uuid = UUID(user_id)
        except (ValueError, AttributeError):
            raise credentials_exception

    except Exception:
        raise credentials_exception

    # Import qui per evitare circular import
    from app.models.user import User

    user = db.query(User).filter(User.id == user_id_uuid).first()

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


def generate_refresh_token() -> str:
    """
    Genera refresh token sicuro (64 caratteri hex = 256 bit)

    Returns:
        str: Refresh token
    """
    return secrets.token_hex(32)


def hash_refresh_token(token: str) -> str:
    """
    Hash refresh token con SHA256 per storage sicuro nel database.

    Args:
        token: Refresh token in chiaro

    Returns:
        str: Hash SHA256 del token
    """
    return hashlib.sha256(token.encode()).hexdigest()


def create_refresh_token(
    user_id: UUID,
    db: Session,
    request: Optional[Request] = None
) -> str:
    """
    Crea nuovo refresh token per utente.

    Args:
        user_id: ID utente
        db: Database session
        request: Request FastAPI (opzionale, per metadata)

    Returns:
        str: Refresh token (da inviare al client)
    """
    from app.models.refresh_token import RefreshToken

    # Genera token
    token = generate_refresh_token()
    token_hash = hash_refresh_token(token)

    # Calcola scadenza
    expires_at = datetime.utcnow() + timedelta(days=settings.refresh_token_expire_days)

    # Metadata da request
    device_info = None
    ip_address = None
    user_agent = None

    if request:
        user_agent = request.headers.get("user-agent", "")[:500]
        # Gestisci proxy headers per IP reale
        ip_address = request.headers.get("x-forwarded-for", request.client.host if request.client else None)
        if ip_address and "," in ip_address:
            ip_address = ip_address.split(",")[0].strip()

    # Crea record database
    db_token = RefreshToken(
        token_hash=token_hash,
        user_id=user_id,
        expires_at=expires_at,
        device_info=device_info,
        ip_address=ip_address,
        user_agent=user_agent
    )

    db.add(db_token)
    db.commit()

    return token


def verify_refresh_token(token: str, db: Session) -> Optional[UUID]:
    """
    Verifica refresh token e ritorna user_id se valido.

    Args:
        token: Refresh token da verificare
        db: Database session

    Returns:
        UUID: User ID se token valido, None altrimenti
    """
    from app.models.refresh_token import RefreshToken

    token_hash = hash_refresh_token(token)

    # Query database
    db_token = db.query(RefreshToken).filter(
        RefreshToken.token_hash == token_hash
    ).first()

    if not db_token:
        return None

    # Verifica validità
    if not db_token.is_valid:
        return None

    # Aggiorna last_used_at
    db_token.last_used_at = datetime.utcnow()
    db.commit()

    return db_token.user_id


def revoke_refresh_token(token: str, db: Session) -> bool:
    """
    Revoca refresh token.

    Args:
        token: Refresh token da revocare
        db: Database session

    Returns:
        bool: True se revocato, False se non trovato
    """
    from app.models.refresh_token import RefreshToken

    token_hash = hash_refresh_token(token)

    db_token = db.query(RefreshToken).filter(
        RefreshToken.token_hash == token_hash
    ).first()

    if not db_token:
        return False

    db_token.is_revoked = True
    db_token.revoked_at = datetime.utcnow()
    db.commit()

    return True


def revoke_all_user_tokens(user_id: UUID, db: Session) -> int:
    """
    Revoca tutti i refresh token di un utente.

    Args:
        user_id: ID utente
        db: Database session

    Returns:
        int: Numero di token revocati
    """
    from app.models.refresh_token import RefreshToken

    count = db.query(RefreshToken).filter(
        RefreshToken.user_id == user_id,
        RefreshToken.is_revoked == False
    ).update({
        "is_revoked": True,
        "revoked_at": datetime.utcnow()
    })

    db.commit()
    return count
