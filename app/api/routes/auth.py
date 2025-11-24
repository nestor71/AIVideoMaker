"""
Authentication Routes
=====================
Route per autenticazione JWT, registrazione utenti, gestione API keys
"""

from datetime import timedelta, datetime
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import RedirectResponse, HTMLResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr, field_serializer
import httpx
import secrets
import hashlib

from app.core.database import get_db
from app.core.security import (
    create_access_token,
    verify_password,
    get_password_hash,
    get_current_user,
    generate_api_key,
    create_refresh_token,
    verify_refresh_token,
    revoke_refresh_token,
    revoke_all_user_tokens
)
from app.core.config import settings
from app.core.limiter import limiter
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
    refresh_token: str
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
@limiter.limit("5/minute")
async def register(
    request: Request,
    user_data: UserRegister,
    db: Session = Depends(get_db)
):
    """
    Registra nuovo utente

    RATE LIMIT: 5 richieste/minuto per IP

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

    # Crea nuovo utente (is_verified = False di default)
    new_user = User(
        username=user_data.username,
        email=user_data.email,
        full_name=user_data.full_name,
        hashed_password=get_password_hash(user_data.password),
        is_verified=False  # Richiede verifica email
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Genera token di verifica (JWT valido 24 ore)
    verification_token = create_access_token(
        data={"sub": str(new_user.id), "type": "email_verification"},
        expires_delta=timedelta(hours=24)
    )

    # TODO: Inviare email di verifica
    # verification_link = f"{settings.frontend_url}/verify-email?token={verification_token}"
    # await send_email(new_user.email, "Verifica Email", verification_link)

    # Per ora log in console (in produzione inviare email vera)
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"📧 Email verification token per {new_user.email}: {verification_token}")
    logger.info(f"   Link verifica: http://localhost:8000/api/v1/auth/verify-email?token={verification_token}")

    return new_user


@router.post("/login", response_model=Token)
@limiter.limit("5/minute")
async def login(
    request: Request,
    credentials: UserLogin,
    db: Session = Depends(get_db)
):
    """
    Login e generazione JWT token + Refresh Token

    RATE LIMIT: 5 richieste/minuto per IP

    - **email**: Email utente
    - **password**: Password

    Returns:
    - **access_token**: JWT valido per 1 ora
    - **refresh_token**: Token per rinnovare access_token (valido 30 giorni)
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

    # Aggiorna last_login
    user.last_login_at = datetime.utcnow()
    db.commit()

    # Crea access token (1 ora)
    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=timedelta(minutes=settings.access_token_expire_minutes)
    )

    # Crea refresh token (30 giorni)
    refresh_token = create_refresh_token(user.id, db, request)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": settings.access_token_expire_minutes * 60  # in secondi
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

    # Crea JWT token (1 ora per test - in produzione disabilitare questo endpoint!)
    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=timedelta(minutes=settings.access_token_expire_minutes)
    )

    # Crea anche refresh token
    refresh_token = create_refresh_token(user.id, db)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": settings.access_token_expire_minutes * 60  # in secondi
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


# ==================== GOOGLE OAUTH 2.0 ====================

# In-memory storage per OAuth state (production: usa Redis)
oauth_states = {}

@router.get("/google/login")
async def google_login(request: Request):
    """
    Avvia flusso Google OAuth 2.0

    **Come funziona:**
    1. Genera state random per CSRF protection
    2. Redirect utente a Google per autorizzazione
    3. Google richiama /google/callback con authorization code
    4. Scambiamo code per access token
    5. Recuperiamo dati utente da Google
    6. Creiamo/Login utente e ritorniamo JWT token

    **Configurazione necessaria:**
    - GOOGLE_CLIENT_ID in .env
    - GOOGLE_CLIENT_SECRET in .env
    - GOOGLE_REDIRECT_URI in .env (default: http://localhost:8000/api/v1/auth/google/callback)

    **Ottieni credenziali:**
    1. Vai a https://console.cloud.google.com/
    2. Crea nuovo progetto o seleziona esistente
    3. Abilita "Google+ API"
    4. Crea credenziali OAuth 2.0 Client ID
    5. Aggiungi redirect URI autorizzato
    6. Copia Client ID e Client Secret in .env
    """
    if not settings.google_client_id or not settings.google_client_secret:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=(
                "Google OAuth non configurato. "
                "Aggiungi GOOGLE_CLIENT_ID e GOOGLE_CLIENT_SECRET in .env"
            )
        )

    # Genera state random per CSRF protection
    state = secrets.token_urlsafe(32)
    oauth_states[state] = {
        "timestamp": datetime.utcnow(),
        "used": False
    }

    # Pulizia stati vecchi (> 10 minuti)
    current_time = datetime.utcnow()
    expired_states = [
        s for s, data in oauth_states.items()
        if (current_time - data["timestamp"]).seconds > 600
    ]
    for s in expired_states:
        del oauth_states[s]

    # Costruisci URL autorizzazione Google
    google_auth_url = (
        "https://accounts.google.com/o/oauth2/v2/auth?"
        f"client_id={settings.google_client_id}&"
        f"redirect_uri={settings.google_redirect_uri}&"
        "response_type=code&"
        "scope=openid%20email%20profile&"
        f"state={state}&"
        "access_type=offline&"
        "prompt=consent"
    )

    return RedirectResponse(url=google_auth_url)


@router.get("/google/callback")
async def google_callback(
    code: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Callback Google OAuth 2.0

    Chiamato da Google dopo che l'utente autorizza l'app.
    Scambia authorization code per access token e crea/login utente.
    """
    # Gestione errori Google
    if error:
        return HTMLResponse(
            content=f"""
            <html>
                <body>
                    <h1>⚠️ Errore Autenticazione Google</h1>
                    <p>Errore: {error}</p>
                    <p><a href="/login">Riprova</a></p>
                </body>
            </html>
            """,
            status_code=400
        )

    # Validazione parametri
    if not code or not state:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Parametri mancanti: code e state richiesti"
        )

    # Verifica state (CSRF protection)
    if state not in oauth_states:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="State non valido o scaduto. Riprova il login."
        )

    if oauth_states[state]["used"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="State già utilizzato. Possibile attacco CSRF."
        )

    # Marca state come usato
    oauth_states[state]["used"] = True

    # Scambia authorization code per access token
    async with httpx.AsyncClient() as client:
        token_response = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "redirect_uri": settings.google_redirect_uri,
                "grant_type": "authorization_code"
            }
        )

        if token_response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Errore scambio token: {token_response.text}"
            )

        token_data = token_response.json()
        access_token = token_data.get("access_token")

        if not access_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Access token non ricevuto da Google"
            )

        # Recupera dati utente da Google
        user_response = await client.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {access_token}"}
        )

        if user_response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Errore recupero dati utente da Google"
            )

        google_user = user_response.json()

    # Estrai dati Google
    google_email = google_user.get("email")
    google_name = google_user.get("name")
    google_id = google_user.get("id")

    if not google_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email non disponibile da Google"
        )

    # Cerca utente esistente per email
    user = db.query(User).filter(User.email == google_email).first()

    if user:
        # Utente esiste: login
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account disabilitato"
            )

        # Aggiorna last_login
        user.last_login_at = datetime.utcnow()
        db.commit()

    else:
        # Utente NON esiste: registrazione automatica
        # Genera username univoco da email
        base_username = google_email.split("@")[0]
        username = base_username

        # Verifica unicità username
        counter = 1
        while db.query(User).filter(User.username == username).first():
            username = f"{base_username}{counter}"
            counter += 1

        # Genera password random (non usata, login solo via Google)
        random_password = secrets.token_urlsafe(32)

        # Crea nuovo utente
        user = User(
            email=google_email,
            username=username,
            full_name=google_name,
            hashed_password=get_password_hash(random_password),
            is_verified=True,  # Email già verificata da Google
            last_login_at=datetime.utcnow()
        )

        db.add(user)
        db.commit()
        db.refresh(user)

    # Genera JWT token per l'app (1 ora)
    jwt_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=timedelta(minutes=settings.access_token_expire_minutes)
    )

    # Genera refresh token
    refresh_token_val = create_refresh_token(user.id, db)

    # FIX XSS: Escape HTML e usa JSON sicuro invece di template string
    import json
    safe_token = json.dumps(jwt_token)
    safe_refresh = json.dumps(refresh_token_val)
    safe_username = json.dumps(user.full_name or user.username)

    # Redirect a pagina con token (auto-login)
    return HTMLResponse(
        content=f"""
        <html>
            <head>
                <title>Login Completato</title>
                <script>
                    // Salva token in localStorage (JSON.parse rimuove XSS risk)
                    localStorage.setItem('auth_token', {safe_token});
                    localStorage.setItem('refresh_token', {safe_refresh});

                    // Redirect a homepage
                    window.location.href = '/';
                </script>
            </head>
            <body>
                <h1>✅ Login completato!</h1>
                <p>Benvenuto, <span id="username"></span>!</p>
                <p>Reindirizzamento in corso...</p>
                <p>Se non vieni reindirizzato, <a href="/">clicca qui</a>.</p>
                <script>
                    document.getElementById('username').textContent = {safe_username};
                </script>
            </body>
        </html>
        """,
        status_code=200
    )


# ==================== Refresh Token Management ====================

class RefreshTokenRequest(BaseModel):
    """Schema per refresh token request"""
    refresh_token: str


@router.post("/refresh", response_model=Token)
@limiter.limit("10/minute")
async def refresh_access_token(
    request: Request,
    token_data: RefreshTokenRequest,
    db: Session = Depends(get_db)
):
    """
    Rinnova access token usando refresh token

    RATE LIMIT: 10 richieste/minuto per IP

    - **refresh_token**: Refresh token valido

    Returns:
    - **access_token**: Nuovo JWT valido per 1 ora
    - **refresh_token**: Nuovo refresh token (rotation per sicurezza)
    """
    # Verifica refresh token
    user_id = verify_refresh_token(token_data.refresh_token, db)

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token invalido o scaduto"
        )

    # Trova utente
    user = db.query(User).filter(User.id == user_id).first()

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Utente non trovato o disabilitato"
        )

    # Revoca vecchio refresh token (refresh token rotation)
    revoke_refresh_token(token_data.refresh_token, db)

    # Crea nuovo access token
    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=timedelta(minutes=settings.access_token_expire_minutes)
    )

    # Crea nuovo refresh token
    new_refresh_token = create_refresh_token(user.id, db, request)

    return {
        "access_token": access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer",
        "expires_in": settings.access_token_expire_minutes * 60
    }


@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(
    token_data: RefreshTokenRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Logout: revoca refresh token corrente

    Richiede JWT token valido

    - **refresh_token**: Refresh token da revocare

    Returns:
    - Messaggio di conferma
    """
    # Revoca refresh token
    revoked = revoke_refresh_token(token_data.refresh_token, db)

    if not revoked:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Refresh token non trovato"
        )

    return {"message": "Logout effettuato con successo"}


@router.post("/revoke-all", status_code=status.HTTP_200_OK)
async def revoke_all_tokens(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Revoca tutti i refresh token dell'utente corrente

    Utile per:
    - Logout da tutti i dispositivi
    - Cambio password (forzare re-login ovunque)
    - Sicurezza: sospetta compromissione account

    Richiede JWT token valido

    Returns:
    - Numero di token revocati
    """
    count = revoke_all_user_tokens(current_user.id, db)

    return {
        "message": f"Revocati {count} refresh token",
        "revoked_count": count
    }


# ==================== Password Management ====================

class ForgotPasswordRequest(BaseModel):
    """Schema per richiesta reset password"""
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    """Schema per reset password"""
    token: str
    new_password: str


class ChangePasswordRequest(BaseModel):
    """Schema per cambio password (utente loggato)"""
    current_password: str
    new_password: str


@router.post("/forgot-password", status_code=status.HTTP_200_OK)
@limiter.limit("3/hour")
async def forgot_password(
    request: Request,
    data: ForgotPasswordRequest,
    db: Session = Depends(get_db)
):
    """
    Richiesta reset password

    RATE LIMIT: 3 richieste/ora per IP

    Invia email con link reset password (token valido 15 minuti)

    - **email**: Email utente

    Returns:
    - Messaggio di conferma (sempre, anche se email non esiste - per sicurezza)
    """
    # Trova utente (silently fail se non esiste - no information disclosure)
    user = db.query(User).filter(User.email == data.email).first()

    if user and user.is_active:
        # Crea reset token (JWT con scadenza 15 minuti)
        reset_token = create_access_token(
            data={"sub": str(user.id), "type": "password_reset"},
            expires_delta=timedelta(minutes=15)
        )

        # TODO: Inviare email con reset link
        # reset_link = f"{settings.frontend_url}/reset-password?token={reset_token}"
        # await send_email(user.email, "Reset Password", reset_link)

        # Per ora log in console (in produzione inviare email vera)
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"🔑 Password reset token per {user.email}: {reset_token}")
        logger.info(f"   Link reset: http://localhost:8000/reset-password?token={reset_token}")

    # SEMPRE ritorna successo (anche se email non esiste) - previene user enumeration
    return {
        "message": "Se l'email esiste, riceverai un link per reset password"
    }


@router.post("/reset-password", status_code=status.HTTP_200_OK)
@limiter.limit("5/hour")
async def reset_password(
    request: Request,
    data: ResetPasswordRequest,
    db: Session = Depends(get_db)
):
    """
    Reset password con token

    RATE LIMIT: 5 richieste/ora per IP

    - **token**: Reset token da email
    - **new_password**: Nuova password

    Returns:
    - Messaggio di conferma
    """
    # Decodifica token
    from app.core.security import decode_access_token

    payload = decode_access_token(data.token)

    if not payload or payload.get("type") != "password_reset":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token reset invalido o scaduto"
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token reset invalido"
        )

    # Trova utente
    from uuid import UUID as UUIDType
    user = db.query(User).filter(User.id == UUIDType(user_id)).first()

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Utente non trovato o disabilitato"
        )

    # Valida nuova password (lunghezza minima)
    if len(data.new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password deve essere almeno 8 caratteri"
        )

    # Aggiorna password
    user.hashed_password = get_password_hash(data.new_password)
    user.updated_at = datetime.utcnow()
    db.commit()

    # Revoca tutti i refresh token per sicurezza (forza re-login ovunque)
    revoke_all_user_tokens(user.id, db)

    return {"message": "Password aggiornata con successo"}


@router.post("/change-password", status_code=status.HTTP_200_OK)
async def change_password(
    data: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Cambio password per utente loggato

    Richiede JWT token valido

    - **current_password**: Password attuale
    - **new_password**: Nuova password

    Returns:
    - Messaggio di conferma
    """
    # Verifica password attuale
    if not verify_password(data.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password attuale non corretta"
        )

    # Valida nuova password
    if len(data.new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nuova password deve essere almeno 8 caratteri"
        )

    # Non permettere stessa password
    if verify_password(data.new_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nuova password deve essere diversa dalla precedente"
        )

    # Aggiorna password
    current_user.hashed_password = get_password_hash(data.new_password)
    current_user.updated_at = datetime.utcnow()
    db.commit()

    # Revoca tutti i refresh token eccetto quello corrente (opzionale)
    # Per semplicità revoco tutti - utente dovrà ri-loggarsi
    revoke_all_user_tokens(current_user.id, db)

    return {"message": "Password cambiata con successo. Effettua nuovamente il login."}


# ==================== Email Verification ====================

class VerifyEmailRequest(BaseModel):
    """Schema per verifica email"""
    token: str


@router.post("/verify-email", status_code=status.HTTP_200_OK)
@router.get("/verify-email", status_code=status.HTTP_200_OK)
async def verify_email(
    token: str,
    db: Session = Depends(get_db)
):
    """
    Verifica email con token

    - **token**: Token di verifica email da email

    Returns:
    - Messaggio di conferma
    """
    # Decodifica token
    from app.core.security import decode_access_token

    payload = decode_access_token(token)

    if not payload or payload.get("type") != "email_verification":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token verifica invalido o scaduto"
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token verifica invalido"
        )

    # Trova utente
    from uuid import UUID as UUIDType
    user = db.query(User).filter(User.id == UUIDType(user_id)).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Utente non trovato"
        )

    # Verifica se già verificato
    if user.is_verified:
        return {"message": "Email già verificata"}

    # Marca come verificato
    user.is_verified = True
    user.updated_at = datetime.utcnow()
    db.commit()

    return {"message": "Email verificata con successo!"}


@router.post("/resend-verification", status_code=status.HTTP_200_OK)
@limiter.limit("3/hour")
async def resend_verification_email(
    request: Request,
    data: ForgotPasswordRequest,  # Riusa stesso schema (ha email)
    db: Session = Depends(get_db)
):
    """
    Ri-invia email di verifica

    RATE LIMIT: 3 richieste/ora per IP

    - **email**: Email utente

    Returns:
    - Messaggio di conferma (sempre, anche se email non esiste)
    """
    # Trova utente
    user = db.query(User).filter(User.email == data.email).first()

    if user and user.is_active and not user.is_verified:
        # Genera nuovo token
        verification_token = create_access_token(
            data={"sub": str(user.id), "type": "email_verification"},
            expires_delta=timedelta(hours=24)
        )

        # TODO: Inviare email
        # await send_email(user.email, "Verifica Email", verification_link)

        # Per ora log
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"📧 Re-invio verification per {user.email}: {verification_token}")
        logger.info(f"   Link: http://localhost:8000/api/v1/auth/verify-email?token={verification_token}")

    # SEMPRE ritorna successo - previene user enumeration
    return {"message": "Se l'email esiste e non è verificata, riceverai un nuovo link"}


# ==================== CSRF Token ====================

@router.get("/csrf-token", status_code=status.HTTP_200_OK)
async def get_csrf_token():
    """
    Genera nuovo CSRF token

    Usare questo token nell'header X-CSRF-Token per richieste POST/PUT/DELETE/PATCH

    Returns:
    - CSRF token
    """
    from app.core.csrf import generate_csrf_token

    token = generate_csrf_token()

    return {
        "csrf_token": token,
        "usage": "Invia questo token nell'header: X-CSRF-Token: <token>"
    }
