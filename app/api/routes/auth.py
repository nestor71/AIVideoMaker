"""
Authentication Routes
=====================
Route per autenticazione JWT, registrazione utenti, gestione API keys
"""

from datetime import timedelta
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr, field_serializer

from app.core.database import get_db
from app.core.security import (
    create_access_token,
    verify_password,
    get_password_hash,
    get_current_user,
    generate_api_key
)
from app.core.config import settings
from app.models.user import User
from app.models.api_key import APIKey

router = APIRouter()
security = HTTPBearer()


# ==================== Pydantic Schemas ====================

class UserRegister(BaseModel):
    """Schema per registrazione utente"""
    username: str
    email: EmailStr
    password: str
    full_name: Optional[str] = None


class UserLogin(BaseModel):
    """Schema per login"""
    email: EmailStr
    password: str


class Token(BaseModel):
    """Schema per token JWT"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class UserResponse(BaseModel):
    """Schema per risposta utente"""
    id: UUID
    username: str
    email: str
    full_name: Optional[str]
    is_active: bool
    is_admin: bool

    @field_serializer('id')
    def serialize_id(self, value: UUID) -> str:
        """Serializza UUID come stringa per JSON"""
        return str(value)

    class Config:
        from_attributes = True


class APIKeyResponse(BaseModel):
    """Schema per risposta API key"""
    id: UUID
    name: str
    key: str
    is_active: bool
    created_at: str

    @field_serializer('id')
    def serialize_id(self, value: UUID) -> str:
        """Serializza UUID come stringa per JSON"""
        return str(value)

    class Config:
        from_attributes = True


class APIKeyCreate(BaseModel):
    """Schema per creazione API key"""
    name: str


# ==================== Routes ====================

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserRegister, db: Session = Depends(get_db)):
    """
    Registra nuovo utente

    - **username**: Username univoco
    - **email**: Email univoca
    - **password**: Password (verrà hashata)
    - **full_name**: Nome completo opzionale
    """
    # Verifica se username o email già esistono
    existing_user = db.query(User).filter(
        (User.username == user_data.username) | (User.email == user_data.email)
    ).first()

    if existing_user:
        if existing_user.username == user_data.username:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username già in uso"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email già in uso"
            )

    # Crea nuovo utente
    new_user = User(
        username=user_data.username,
        email=user_data.email,
        full_name=user_data.full_name,
        hashed_password=get_password_hash(user_data.password)
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user


@router.post("/login", response_model=Token)
async def login(credentials: UserLogin, db: Session = Depends(get_db)):
    """
    Login e generazione JWT token

    - **email**: Email utente
    - **password**: Password

    Returns JWT token valido per 30 giorni
    """
    # Trova utente
    user = db.query(User).filter(User.email == credentials.email).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenziali non valide"
        )

    # Verifica password
    if not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenziali non valide"
        )

    # Verifica utente attivo
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Utente disabilitato"
        )

    # Crea JWT token
    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=timedelta(days=30)
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": 30 * 24 * 60 * 60  # 30 giorni in secondi
    }


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """
    Ottieni informazioni utente corrente

    Richiede JWT token nell'header Authorization: Bearer <token>
    """
    return current_user


@router.post("/quick-token", response_model=Token)
async def quick_token(
    email: str,
    db: Session = Depends(get_db)
):
    """
    🚀 TESTING RAPIDO: Genera token immediato per testing

    **SOLO PER DEVELOPMENT!**

    Genera un token JWT immediatamente per l'utente specificato,
    senza richiedere password. Perfetto per testing rapido in Swagger.

    **Come usare:**
    1. Registra un utente normale (se non esiste)
    2. Chiama questo endpoint con l'email dell'utente
    3. Copia il token
    4. Usa "Authorize" in Swagger e incolla il token
    5. Il token dura 30 giorni - salvalo per riutilizzarlo!

    **Esempio:**
    - email: ettore@test.com

    **Tip:** Salva il token in un file di testo sul desktop.
    Quando riavvii il server o ricarichi Swagger, ri-incolla lo stesso token!

    ⚠️ Disabilitare in produzione!
    """
    # Trova utente
    user = db.query(User).filter(User.email == email).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Utente con email '{email}' non trovato. Registrati prima con /register"
        )

    # Verifica utente attivo
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Utente disabilitato"
        )

    # Crea JWT token (30 giorni)
    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=timedelta(days=30)
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": 30 * 24 * 60 * 60  # 30 giorni in secondi
    }


@router.post("/api-keys", response_model=APIKeyResponse, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    key_data: APIKeyCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Crea nuova API key per l'utente corrente

    - **name**: Nome identificativo per l'API key

    Richiede JWT token
    """
    # Genera API key
    api_key_value = generate_api_key()

    # Crea record database
    api_key = APIKey(
        user_id=current_user.id,
        name=key_data.name,
        key=api_key_value
    )

    db.add(api_key)
    db.commit()
    db.refresh(api_key)

    return api_key


@router.get("/api-keys", response_model=list[APIKeyResponse])
async def list_api_keys(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Lista tutte le API keys dell'utente corrente

    Richiede JWT token
    """
    api_keys = db.query(APIKey).filter(APIKey.user_id == current_user.id).all()

    return [
        {
            "id": key.id,  # field_serializer lo converte a str
            "name": key.name,
            "key": key.key[:8] + "..." + key.key[-4:],  # Mostra solo parte della key
            "is_active": key.is_active,
            "created_at": key.created_at.isoformat()
        }
        for key in api_keys
    ]


@router.delete("/api-keys/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_api_key(
    key_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Elimina API key

    - **key_id**: ID dell'API key da eliminare

    Richiede JWT token. Puoi eliminare solo le tue API keys.
    """
    api_key = db.query(APIKey).filter(
        APIKey.id == key_id,
        APIKey.user_id == current_user.id
    ).first()

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key non trovata"
        )

    db.delete(api_key)
    db.commit()

    return None
