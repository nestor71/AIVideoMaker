# 🔒 SECURITY AUDIT - AIVideoMaker
## Problemi di Sicurezza e Come Risolverli

**Data Audit:** 2025-11-10
**Versione App:** 2.0
**Stato:** ❌ NON PRONTO PER PRODUZIONE

---

## ⚠️ VERDETTO: NON mettere online così

L'applicazione ha **buchi di sicurezza critici** che devono essere risolti PRIMA del deploy pubblico.

**Tempo stimato fix critici:** 2-3 giorni full-time
**Tempo setup infrastruttura:** 1-2 giorni
**Totale prima lancio pubblico:** ~5 giorni

---

# 🔴 PROBLEMI CRITICI (STOP PRODUZIONE)

## 1. Admin Dashboard - Solo Controllo Client-Side

### 🐛 Problema
```javascript
// templates/admin_dashboard.html riga 642
if (!user.is_admin) {
    window.location.href = '/?error=admin_required';
}
```
Un attacker può:
- Disabilitare JavaScript nel browser
- Accedere a `/admin` anche senza essere admin
- Vedere l'interfaccia admin (anche se le API falliscono)

**Gravità:** 🔴 CRITICA - Bypass controllo admin

### ✅ Soluzione

**File:** `main.py`

```python
# PRIMA (vulnerabile):
@app.get("/admin")
async def admin_dashboard(request: Request):
    return templates.TemplateResponse("admin_dashboard.html", {"request": request})

# DOPO (sicuro):
from app.core.security import require_admin
from app.models.user import User

@app.get("/admin")
async def admin_dashboard(
    request: Request,
    current_user: User = Depends(require_admin)  # ← Aggiungi questa riga
):
    """
    Admin dashboard - PROTETTA
    Solo utenti con is_admin=True possono accedere
    """
    return templates.TemplateResponse("admin_dashboard.html", {"request": request})
```

**Test:**
```bash
# Testa con user non-admin
curl -H "Authorization: Bearer <user_token>" http://localhost:8000/admin
# Dovrebbe ritornare 403 Forbidden
```

---

## 2. Rate Limiting - ZERO Protezione

### 🐛 Problema
Nessun limite alle richieste. Un attacker può:
- **Brute force password:** 10,000 tentativi login in 1 minuto
- **DoS attack:** Saturare il server con infinite richieste
- **API abuse:** Creare 1000 job chromakey simultanei → crash server

**Gravità:** 🔴 CRITICA - DoS e brute force

### ✅ Soluzione

**Step 1: Installa slowapi**
```bash
pip install slowapi
```

**Step 2: Aggiungi a requirements.txt**
```
slowapi==0.1.9
```

**Step 3: Configura in main.py**

**File:** `main.py`

```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# Dopo l'inizializzazione app
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
```

**Step 4: Applica rate limits**

**File:** `app/api/routes/auth.py`

```python
from slowapi import Limiter
from fastapi import Request

limiter = Limiter(key_func=lambda request: request.client.host)

@router.post("/login")
@limiter.limit("5/minute")  # Max 5 tentativi al minuto per IP
async def login(
    request: Request,  # ← Aggiungi questo parametro
    credentials: LoginRequest,
    db: Session = Depends(get_db)
):
    # ... resto del codice
```

**File:** `app/api/routes/admin.py`

```python
from slowapi import Limiter

limiter = Limiter(key_func=lambda request: request.client.host)

@router.get("/users")
@limiter.limit("30/minute")  # Max 30 richieste admin al minuto
async def list_all_users(
    request: Request,  # ← Aggiungi questo
    skip: int = 0,
    limit: int = 100,
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    # ... resto del codice

@router.delete("/users/{user_id}")
@limiter.limit("10/minute")  # Max 10 delete al minuto
async def delete_user(
    request: Request,  # ← Aggiungi questo
    user_id: str,
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    # ... resto del codice
```

**Rate Limits Consigliati:**
```python
# Auth
/auth/login          → 5/minute   (previene brute force)
/auth/register       → 3/hour     (previene spam account)
/auth/refresh        → 10/minute

# Admin
/admin/users         → 30/minute
/admin/users/{id}    → 60/minute
/admin/users/export  → 5/hour     (operazione pesante)

# API intensive
/chromakey/process   → 10/hour    (operazione costosa)
/video/download      → 20/hour
/seo/generate        → 15/hour
```

**Test:**
```bash
# Testa rate limit login
for i in {1..10}; do
  curl -X POST http://localhost:8000/api/v1/auth/login \
    -H "Content-Type: application/json" \
    -d '{"username":"test","password":"wrong"}'
done
# Dopo il 5° tentativo dovrebbe dare 429 Too Many Requests
```

---

## 3. CORS Aperto a Tutti

### 🐛 Problema

**File:** `main.py` (attuale)

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # ← PERICOLOSISSIMO!
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Conseguenze:**
- Qualsiasi sito web può fare richieste al tuo backend
- Attacker può creare sito malevolo che chiama le tue API
- CSRF attack possibili
- Cookie/JWT rubabili da altri domini

**Gravità:** 🔴 CRITICA - CSRF e data leak

### ✅ Soluzione

**File:** `main.py`

```python
# CORS ristretto al tuo dominio
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://tuodominio.com",          # Produzione
        "https://www.tuodominio.com",      # Produzione con www
        "http://localhost:8000",           # Sviluppo locale
        "http://localhost:3000",           # Frontend dev (se separato)
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],  # Solo metodi necessari
    allow_headers=["Authorization", "Content-Type"],          # Solo header necessari
    max_age=3600,  # Cache preflight 1 ora
)
```

**Ambiente-specifico (MEGLIO):**

**File:** `app/core/config.py`

```python
class Settings(BaseSettings):
    # ... altri settings

    cors_origins: List[str] = Field(
        default=["http://localhost:8000"],
        env="CORS_ORIGINS"
    )
```

**File:** `.env.production`
```bash
CORS_ORIGINS=["https://tuodominio.com","https://www.tuodominio.com"]
```

**File:** `.env.development`
```bash
CORS_ORIGINS=["http://localhost:8000","http://localhost:3000"]
```

**File:** `main.py`
```python
from app.core.config import settings

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,  # ← Da config
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)
```

**Test:**
```bash
# Test da origin non permesso
curl -H "Origin: https://attacker.com" \
     -H "Access-Control-Request-Method: GET" \
     http://localhost:8000/api/v1/admin/users
# Dovrebbe negare accesso (no header Access-Control-Allow-Origin)
```

---

## 4. File Upload Senza Validazione

### 🐛 Problema

**File:** `app/api/routes/chromakey.py`, `logo.py`, `thumbnail.py`, etc.

Attualmente:
- Nessun limite dimensione file
- Nessuna validazione MIME type reale
- Accetta qualsiasi file (anche malware)
- Possibile path traversal

**Attacco possibile:**
```python
# Attacker carica file da 10GB → crash server (out of memory)
# Attacker carica PHP shell mascherato da .mp4
# Attacker usa path "../../../etc/passwd" per leggere file sistema
```

**Gravità:** 🔴 CRITICA - DoS e malware upload

### ✅ Soluzione

**Step 1: Installa python-magic**
```bash
pip install python-magic
sudo apt-get install libmagic1  # Linux
brew install libmagic            # macOS
```

**Step 2: Crea helper validazione**

**File:** `app/core/file_validator.py` (NUOVO)

```python
"""
File Validator - Validazione sicura file upload
==============================================
"""

from fastapi import UploadFile, HTTPException, status
from pathlib import Path
import magic
from typing import List

# Limiti
MAX_VIDEO_SIZE = 500 * 1024 * 1024   # 500MB
MAX_IMAGE_SIZE = 10 * 1024 * 1024    # 10MB
MAX_AUDIO_SIZE = 100 * 1024 * 1024   # 100MB

# MIME types permessi
ALLOWED_VIDEO_MIMES = [
    "video/mp4",
    "video/quicktime",  # .mov
    "video/x-msvideo",  # .avi
    "video/x-matroska", # .mkv
    "video/webm"
]

ALLOWED_IMAGE_MIMES = [
    "image/jpeg",
    "image/png",
    "image/gif",
    "image/webp"
]

ALLOWED_AUDIO_MIMES = [
    "audio/mpeg",       # .mp3
    "audio/wav",
    "audio/x-wav",
    "audio/ogg",
    "audio/mp4"         # .m4a
]


async def validate_video_upload(file: UploadFile) -> Path:
    """
    Valida file video upload

    Args:
        file: File uploadato

    Returns:
        Path: Path sicuro dove salvare

    Raises:
        HTTPException: Se validazione fallisce
    """
    # Check size
    content = await file.read()
    if len(content) > MAX_VIDEO_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File troppo grande. Max {MAX_VIDEO_SIZE // 1024 // 1024}MB"
        )

    # Check MIME type reale (non da header, ma da contenuto)
    mime = magic.from_buffer(content[:1024], mime=True)
    if mime not in ALLOWED_VIDEO_MIMES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tipo file non permesso. Ricevuto: {mime}. Permessi: {ALLOWED_VIDEO_MIMES}"
        )

    # Check filename sicuro (no path traversal)
    safe_filename = Path(file.filename).name  # Solo nome file, no path
    if ".." in safe_filename or "/" in safe_filename or "\\" in safe_filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename non valido"
        )

    # Ritorna content per salvare
    await file.seek(0)  # Reset stream
    return content, safe_filename


async def validate_image_upload(file: UploadFile) -> bytes:
    """Valida image upload"""
    content = await file.read()

    if len(content) > MAX_IMAGE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Immagine troppo grande. Max {MAX_IMAGE_SIZE // 1024 // 1024}MB"
        )

    mime = magic.from_buffer(content[:1024], mime=True)
    if mime not in ALLOWED_IMAGE_MIMES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tipo immagine non permesso: {mime}"
        )

    safe_filename = Path(file.filename).name
    if ".." in safe_filename or "/" in safe_filename:
        raise HTTPException(400, "Filename non valido")

    await file.seek(0)
    return content, safe_filename


async def validate_audio_upload(file: UploadFile) -> bytes:
    """Valida audio upload"""
    content = await file.read()

    if len(content) > MAX_AUDIO_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Audio troppo grande. Max {MAX_AUDIO_SIZE // 1024 // 1024}MB"
        )

    mime = magic.from_buffer(content[:1024], mime=True)
    if mime not in ALLOWED_AUDIO_MIMES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tipo audio non permesso: {mime}"
        )

    safe_filename = Path(file.filename).name
    await file.seek(0)
    return content, safe_filename
```

**Step 3: Usa validator nelle route**

**File:** `app/api/routes/chromakey.py`

```python
from app.core.file_validator import validate_video_upload

@router.post("/upload")
async def upload_and_process(
    foreground: UploadFile = File(...),
    background: UploadFile = File(...),
    # ... altri parametri
):
    # Valida PRIMA di salvare
    fg_content, fg_filename = await validate_video_upload(foreground)
    bg_content, bg_filename = await validate_video_upload(background)

    # Ora salva in modo sicuro
    fg_path = settings.upload_dir / "chromakey" / fg_filename
    bg_path = settings.upload_dir / "chromakey" / bg_filename

    fg_path.write_bytes(fg_content)
    bg_path.write_bytes(bg_content)

    # ... resto del codice
```

**Applica a TUTTE le route con upload:**
- ✅ `chromakey.py`
- ✅ `logo.py`
- ✅ `thumbnail.py`
- ✅ `screen_record.py`
- ✅ `seo_metadata.py` (se ha upload)
- ✅ `youtube.py`

**Test:**
```bash
# Test file troppo grande
dd if=/dev/zero of=large.mp4 bs=1M count=600  # 600MB
curl -F "foreground=@large.mp4" http://localhost:8000/api/v1/chromakey/upload
# Dovrebbe dare 413 Request Entity Too Large

# Test tipo file sbagliato
echo "fake video" > fake.mp4
curl -F "foreground=@fake.mp4" http://localhost:8000/api/v1/chromakey/upload
# Dovrebbe dare 400 Bad Request
```

---

## 5. HTTPS Non Forzato

### 🐛 Problema
Traffico HTTP in chiaro = password e JWT visibili sulla rete.

**Gravità:** 🔴 CRITICA - Credential theft

### ✅ Soluzione

**File:** `main.py`

```python
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from app.core.config import settings

# Forza HTTPS in produzione
if settings.environment == "production":
    app.add_middleware(HTTPSRedirectMiddleware)
```

**File:** `app/core/config.py`

```python
class Settings(BaseSettings):
    # ... altri settings

    # Security
    force_https: bool = Field(
        default=False,
        env="FORCE_HTTPS"
    )

    # Secure cookies
    secure_cookies: bool = Field(
        default=False,
        env="SECURE_COOKIES"
    )
```

**File:** `.env.production`
```bash
ENVIRONMENT=production
FORCE_HTTPS=true
SECURE_COOKIES=true
```

**Inoltre, configura Nginx:**

**File:** `/etc/nginx/sites-available/aivideomaker`

```nginx
# Redirect HTTP → HTTPS
server {
    listen 80;
    server_name tuodominio.com www.tuodominio.com;
    return 301 https://$server_name$request_uri;
}

# HTTPS
server {
    listen 443 ssl http2;
    server_name tuodominio.com www.tuodominio.com;

    # SSL certificato (Let's Encrypt)
    ssl_certificate /etc/letsencrypt/live/tuodominio.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/tuodominio.com/privkey.pem;

    # SSL security headers
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # Proxy a FastAPI
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

**Setup SSL certificato:**
```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d tuodominio.com -d www.tuodominio.com
sudo systemctl reload nginx
```

---

## 6. Secrets in .env Non Protetto

### 🐛 Problema
Se `.env` è committato in git, le tue API keys sono pubbliche su GitHub.

**Gravità:** 🔴 CRITICA - API keys leak

### ✅ Soluzione

**Step 1: Verifica .gitignore**

```bash
cat .gitignore | grep .env
```

Se NON c'è `.env`, AGGIUNGILO:

**File:** `.gitignore`

```
# Environment variables
.env
.env.*
!.env.example

# Secrets
*.key
*.pem
credentials*.json
youtube_credentials_*.json

# Database
*.db
*.sqlite

# Uploads temporanei
uploads/*
!uploads/.gitkeep

# Logs
*.log
logs/

# Cache
__pycache__/
*.pyc
.pytest_cache/
```

**Step 2: Rimuovi .env da git se già committato**

```bash
# ATTENZIONE: Questo comando rimuove file da git history
git rm --cached .env
git commit -m "Remove .env from git"

# Se già pushato pubblicamente, ROTATE tutte le API keys!
```

**Step 3: Crea .env.example (template)**

**File:** `.env.example`

```bash
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/dbname

# Security
SECRET_KEY=your-secret-key-here-generate-with-openssl
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60

# Environment
ENVIRONMENT=development

# CORS
CORS_ORIGINS=["http://localhost:8000"]

# API Keys (ottenere da providers)
OPENAI_API_KEY=sk-...
ELEVENLABS_API_KEY=...
YOUTUBE_CLIENT_ID=...
YOUTUBE_CLIENT_SECRET=...

# Email
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your@email.com
SMTP_PASSWORD=your-app-password

# Stripe (per subscription)
STRIPE_SECRET_KEY=sk_test_...
STRIPE_PUBLISHABLE_KEY=pk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
```

**Step 4: Genera SECRET_KEY sicuro**

```bash
# Genera nuovo secret key
openssl rand -hex 32

# Output esempio:
# a8f5f167f44f4964e6c998dee827110c3f1e6e1e5e7b5c7a8f5f167f44f4964

# Metti in .env:
SECRET_KEY=a8f5f167f44f4964e6c998dee827110c3f1e6e1e5e7b5c7a8f5f167f44f4964
```

**Step 5: Produzione - USA Secrets Manager**

NON usare `.env` in produzione. Usa:

**Opzione A: Environment variables nel server**
```bash
# /etc/systemd/system/aivideomaker.service
[Service]
Environment="DATABASE_URL=postgresql://..."
Environment="SECRET_KEY=..."
Environment="OPENAI_API_KEY=..."
```

**Opzione B: AWS Secrets Manager**
```python
import boto3

def get_secret(secret_name):
    client = boto3.client('secretsmanager', region_name='eu-west-1')
    response = client.get_secret_value(SecretId=secret_name)
    return response['SecretString']

# In config.py
DATABASE_URL = get_secret('prod/database_url')
```

**Opzione C: HashiCorp Vault**
```python
import hvac

client = hvac.Client(url='https://vault.tuodominio.com', token=os.getenv('VAULT_TOKEN'))
secrets = client.secrets.kv.v2.read_secret_version(path='aivideomaker/prod')
DATABASE_URL = secrets['data']['data']['database_url']
```

---

## 7. Nessun Audit Log Azioni Admin

### 🐛 Problema
Se un admin:
- Elimina 100 utenti
- Cambia password di altri admin
- Modifica subscription di utenti

**Non c'è traccia di CHI l'ha fatto.**

**Gravità:** 🟡 MEDIA - Ma importante per compliance

### ✅ Soluzione

**Step 1: Crea modello AdminAuditLog**

**File:** `app/models/admin_audit_log.py` (NUOVO)

```python
"""
Admin Audit Log Model
====================
Traccia tutte le azioni admin per compliance e sicurezza
"""

from sqlalchemy import Column, String, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.core.database import Base
from app.core.types import UUID


class AdminAuditLog(Base):
    """Log azioni amministrative"""

    __tablename__ = "admin_audit_logs"

    # Primary Key
    id = Column(UUID(), primary_key=True, default=uuid.uuid4, index=True)

    # Admin che ha fatto l'azione
    admin_id = Column(UUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

    # Azione compiuta
    action = Column(String, nullable=False, index=True)  # "delete_user", "edit_user", "export_csv", etc.

    # Risorsa target (es: user_id modificato/eliminato)
    target_type = Column(String, nullable=True)  # "user", "settings", etc.
    target_id = Column(UUID(), nullable=True)

    # Dettagli azione (JSON)
    details = Column(JSON, nullable=True)  # Es: {"old_email": "x", "new_email": "y"}

    # Request info
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)

    # Timestamp
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationship
    admin = relationship("User", foreign_keys=[admin_id])

    def __repr__(self):
        return f"<AdminAuditLog(action={self.action}, admin_id={self.admin_id}, target={self.target_type}:{self.target_id})>"
```

**Step 2: Aggiungi a __init__.py**

**File:** `app/models/__init__.py`

```python
from app.models.admin_audit_log import AdminAuditLog

__all__ = [
    # ... altri
    "AdminAuditLog",
]
```

**Step 3: Update database init**

**File:** `app/core/database.py`

```python
def init_db():
    try:
        from app.models import (
            user, job, pipeline, api_key, file_metadata, user_settings, usage_log,
            admin_audit_log  # ← Aggiungi questo
        )

        Base.metadata.create_all(bind=engine)
```

**Step 4: Crea helper per logging**

**File:** `app/core/admin_audit.py` (NUOVO)

```python
"""
Admin Audit Helper
==================
Helper per tracciare azioni admin
"""

from sqlalchemy.orm import Session
from fastapi import Request
from typing import Optional, Dict, Any
from uuid import UUID

from app.models.admin_audit_log import AdminAuditLog


def log_admin_action(
    db: Session,
    admin_id: UUID,
    action: str,
    target_type: Optional[str] = None,
    target_id: Optional[UUID] = None,
    details: Optional[Dict[str, Any]] = None,
    request: Optional[Request] = None
):
    """
    Traccia azione admin

    Args:
        db: Database session
        admin_id: ID admin che compie l'azione
        action: Tipo azione ("delete_user", "edit_user", etc.)
        target_type: Tipo risorsa ("user", "settings", etc.)
        target_id: ID risorsa modificata
        details: Dettagli extra (dict)
        request: FastAPI Request (per IP/user agent)

    Example:
        ```python
        log_admin_action(
            db=db,
            admin_id=admin_user.id,
            action="delete_user",
            target_type="user",
            target_id=user_to_delete.id,
            details={"username": user.username, "reason": "spam"},
            request=request
        )
        ```
    """
    try:
        log = AdminAuditLog(
            admin_id=admin_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            details=details,
            ip_address=request.client.host if request else None,
            user_agent=request.headers.get('user-agent') if request else None
        )

        db.add(log)
        db.commit()

    except Exception as e:
        import logging
        logging.error(f"Errore log admin action '{action}': {e}")
        db.rollback()
```

**Step 5: Usa in tutte le route admin**

**File:** `app/api/routes/admin.py`

```python
from app.core.admin_audit import log_admin_action

@router.patch("/users/{user_id}")
async def update_user(
    user_id: str,
    update_data: UserUpdateRequest,
    request: Request,  # ← Aggiungi questo
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.id == user_id).first()

    # Salva old values per audit
    old_values = {
        "email": user.email,
        "is_active": user.is_active,
        "is_admin": user.is_admin,
        "subscription_tier": user.subscription_tier
    }

    # Update user...
    if update_data.email:
        user.email = update_data.email
    # ... altri update

    db.commit()

    # LOG AUDIT
    log_admin_action(
        db=db,
        admin_id=admin_user.id,
        action="edit_user",
        target_type="user",
        target_id=user.id,
        details={
            "old_values": old_values,
            "new_values": update_data.dict(exclude_unset=True)
        },
        request=request
    )

    return await get_user_details(str(user.id), admin_user, db)


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    request: Request,  # ← Aggiungi questo
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.id == user_id).first()

    # ... validazioni

    # Salva info prima di eliminare
    user_info = {
        "username": user.username,
        "email": user.email,
        "created_at": str(user.created_at),
        "total_spent": float(user.total_spent) if user.total_spent else 0
    }

    db.delete(user)
    db.commit()

    # LOG AUDIT
    log_admin_action(
        db=db,
        admin_id=admin_user.id,
        action="delete_user",
        target_type="user",
        target_id=UUID(user_id),
        details=user_info,
        request=request
    )

    return {"success": True, "message": f"Utente eliminato"}


@router.get("/users/export/csv")
async def export_users_csv(
    request: Request,  # ← Aggiungi questo
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    # ... export logic

    # LOG AUDIT
    log_admin_action(
        db=db,
        admin_id=admin_user.id,
        action="export_users_csv",
        details={"user_count": len(users)},
        request=request
    )

    return StreamingResponse(...)
```

**Step 6: Aggiungi endpoint visualizzazione audit logs**

**File:** `app/api/routes/admin.py`

```python
@router.get("/audit-logs")
async def get_audit_logs(
    skip: int = 0,
    limit: int = 100,
    action: Optional[str] = None,
    admin_id: Optional[str] = None,
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Ottieni audit logs azioni admin

    **Richiede privilegi admin.**

    Returns:
        Lista audit logs con filtri
    """
    query = db.query(AdminAuditLog)

    if action:
        query = query.filter(AdminAuditLog.action == action)

    if admin_id:
        query = query.filter(AdminAuditLog.admin_id == admin_id)

    logs = query.order_by(AdminAuditLog.timestamp.desc()).offset(skip).limit(limit).all()

    return [
        {
            "id": str(log.id),
            "admin_id": str(log.admin_id),
            "admin_username": log.admin.username if log.admin else "Deleted Admin",
            "action": log.action,
            "target_type": log.target_type,
            "target_id": str(log.target_id) if log.target_id else None,
            "details": log.details,
            "ip_address": log.ip_address,
            "timestamp": log.timestamp.isoformat()
        }
        for log in logs
    ]
```

**Step 7: Mostra audit logs in dashboard**

Aggiungi sezione "Audit Logs" nella dashboard admin per visualizzare chi ha fatto cosa.

**Migration database:**
```bash
python migrate_db_subscription.py  # Ri-eseguire per creare tabella admin_audit_logs
```

---

## 8. Session Timeout Troppo Lungo

### 🐛 Problema
JWT token probabilmente scade dopo 30 giorni → se rubato, attacker ha 30 giorni di accesso.

**Gravità:** 🟡 MEDIA

### ✅ Soluzione

**File:** `app/core/config.py`

```python
class Settings(BaseSettings):
    # Token expiration
    access_token_expire_minutes: int = Field(
        default=60,  # 1 ora per users normali
        env="ACCESS_TOKEN_EXPIRE_MINUTES"
    )

    admin_token_expire_minutes: int = Field(
        default=15,  # 15 minuti per admin
        env="ADMIN_TOKEN_EXPIRE_MINUTES"
    )

    refresh_token_expire_days: int = Field(
        default=7,  # 7 giorni per refresh token
        env="REFRESH_TOKEN_EXPIRE_DAYS"
    )
```

**File:** `app/core/security.py`

```python
def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None,
    is_admin: bool = False  # ← Aggiungi questo
) -> str:
    """
    Crea JWT access token

    Args:
        data: Payload (es: {"sub": user_id})
        expires_delta: Durata custom (opzionale)
        is_admin: Se True, usa timeout admin più corto
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        # Timeout diverso per admin
        minutes = settings.admin_token_expire_minutes if is_admin else settings.access_token_expire_minutes
        expire = datetime.utcnow() + timedelta(minutes=minutes)

    to_encode.update({"exp": expire, "iat": datetime.utcnow()})

    encoded_jwt = jwt.encode(
        to_encode,
        settings.secret_key,
        algorithm=settings.algorithm
    )

    return encoded_jwt
```

**File:** `app/api/routes/auth.py`

```python
@router.post("/login")
async def login(credentials: LoginRequest, db: Session = Depends(get_db)):
    # ... autenticazione

    # Crea token con timeout appropriato
    access_token = create_access_token(
        data={"sub": str(user.id)},
        is_admin=user.is_admin  # ← Timeout più corto per admin
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": settings.admin_token_expire_minutes * 60 if user.is_admin else settings.access_token_expire_minutes * 60
    }
```

**File:** `.env`

```bash
# Token expiration (minuti)
ACCESS_TOKEN_EXPIRE_MINUTES=60      # 1 ora user normali
ADMIN_TOKEN_EXPIRE_MINUTES=15       # 15 minuti admin
REFRESH_TOKEN_EXPIRE_DAYS=7         # 7 giorni refresh token
```

**Implementa Refresh Token:**

Aggiungi endpoint `/auth/refresh` che permette di rinnovare token senza re-login:

**File:** `app/api/routes/auth.py`

```python
@router.post("/refresh")
async def refresh_token(
    refresh_token: str,
    db: Session = Depends(get_db)
):
    """
    Rinnova access token usando refresh token

    Permette di ottenere nuovo access token senza re-login
    """
    # Valida refresh token
    payload = decode_access_token(refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(401, "Refresh token non valido")

    user_id = payload.get("sub")
    user = db.query(User).filter(User.id == user_id).first()

    if not user or not user.is_active:
        raise HTTPException(401, "Utente non valido")

    # Genera nuovo access token
    new_access_token = create_access_token(
        data={"sub": str(user.id)},
        is_admin=user.is_admin
    )

    return {
        "access_token": new_access_token,
        "token_type": "bearer"
    }
```

---

## 9. SQL Injection - Verifica Query

### 🐛 Problema
Se usi string concatenation nei query invece di parametri bindati, SQL injection possibile.

**Gravità:** 🔴 CRITICA (se presente)

### ✅ Soluzione

**SEMPRE usa SQLAlchemy ORM o parametri bindati.**

**❌ SBAGLIATO (vulnerabile):**
```python
# NEVER DO THIS
query = f"SELECT * FROM users WHERE email = '{email}'"
db.execute(query)
```

**✅ CORRETTO (sicuro):**
```python
# Usa SQLAlchemy ORM
user = db.query(User).filter(User.email == email).first()

# OPPURE parametri bindati
from sqlalchemy import text
query = text("SELECT * FROM users WHERE email = :email")
db.execute(query, {"email": email})
```

**Audit completo:**

```bash
# Cerca string concatenation in query
grep -r "execute.*f\"" app/
grep -r "execute.*%" app/
grep -r "execute.*+" app/

# Se trova match, FIX IMMEDIATAMENTE
```

**Tool automatico:**
```bash
pip install bandit
bandit -r app/ -f html -o security_report.html

# Controlla report per SQL injection warnings
```

---

# 🟡 PROBLEMI MEDI (Fix Pre-Lancio)

## 10. Path Traversal in File Operations

### 🐛 Problema

```python
# Vulnerabile
video_path = Path(request.video_path)  # User passa "../../etc/passwd"
with open(video_path) as f:
    data = f.read()  # ← Legge file di sistema!
```

**Gravità:** 🟡 MEDIA

### ✅ Soluzione

**Sempre valida che path sia dentro directory permessa:**

**File:** `app/core/path_validator.py` (NUOVO)

```python
"""
Path Validator - Previene path traversal attacks
================================================
"""

from pathlib import Path
from fastapi import HTTPException, status
from app.core.config import settings


def validate_path_in_directory(file_path: str, allowed_dir: Path) -> Path:
    """
    Valida che path sia dentro directory permessa

    Previene path traversal attacks come "../../etc/passwd"

    Args:
        file_path: Path da validare (da user input)
        allowed_dir: Directory permessa

    Returns:
        Path: Path sicuro e risolto

    Raises:
        HTTPException: Se path esce da directory permessa

    Example:
        ```python
        safe_path = validate_path_in_directory(
            file_path=request.video_path,
            allowed_dir=settings.upload_dir
        )
        ```
    """
    # Risolvi path assoluto
    resolved_path = Path(file_path).resolve()
    allowed_dir_resolved = allowed_dir.resolve()

    # Check se path è dentro directory permessa
    try:
        resolved_path.relative_to(allowed_dir_resolved)
    except ValueError:
        # Path è fuori dalla directory permessa
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Path non valido. Deve essere dentro {allowed_dir}"
        )

    # Check esistenza
    if not resolved_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File non trovato: {resolved_path.name}"
        )

    return resolved_path
```

**Usa in TUTTE le route che leggono file:**

**File:** `app/api/routes/chromakey.py`

```python
from app.core.path_validator import validate_path_in_directory

@router.post("/process")
async def process_chromakey(request: ChromakeyRequest, ...):
    # Valida path PRIMA di usarli
    fg_path = validate_path_in_directory(request.foreground_video, settings.upload_dir)
    bg_path = validate_path_in_directory(request.background_video, settings.upload_dir)

    # Ora safe da usare
    service = ChromakeyService()
    result = service.process(fg_path, bg_path)
```

**Applica a:**
- ✅ chromakey.py
- ✅ video_download.py
- ✅ seo_metadata.py
- ✅ logo.py
- ✅ thumbnail.py
- ✅ translation.py
- ✅ transcription.py

---

## 11. Database Backup - ZERO

### 🐛 Problema
Se database si corrompe o server crasha, **perdi tutti i dati**.

**Gravità:** 🟡 MEDIA - Ma catastrofico se succede

### ✅ Soluzione

**Setup backup automatico giornaliero**

**File:** `/home/appuser/backup_db.sh` (NUOVO)

```bash
#!/bin/bash

# Database Backup Script
# Esegue backup giornaliero PostgreSQL con retention 30 giorni

# Config
DB_NAME="aivideomaker"
DB_USER="dbuser"
BACKUP_DIR="/backup/database"
DATE=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=30

# Crea directory backup
mkdir -p $BACKUP_DIR

# Backup database
echo "$(date): Inizio backup database..."
pg_dump -U $DB_USER $DB_NAME | gzip > $BACKUP_DIR/backup_${DATE}.sql.gz

# Check successo
if [ $? -eq 0 ]; then
    echo "$(date): Backup completato: backup_${DATE}.sql.gz"
else
    echo "$(date): ERRORE backup database!" >&2
    exit 1
fi

# Elimina backup vecchi (retention 30 giorni)
find $BACKUP_DIR -name "backup_*.sql.gz" -mtime +$RETENTION_DAYS -delete
echo "$(date): Cleanup backup vecchi completato"

# Opzionale: Upload su S3/B2 per off-site backup
# aws s3 cp $BACKUP_DIR/backup_${DATE}.sql.gz s3://mybucket/backups/

exit 0
```

**Rendi eseguibile:**
```bash
chmod +x /home/appuser/backup_db.sh
```

**Setup cron job:**

```bash
# Apri crontab
crontab -e

# Aggiungi backup giornaliero alle 2 AM
0 2 * * * /home/appuser/backup_db.sh >> /var/log/db_backup.log 2>&1

# Backup settimanale (domenica 3 AM) su storage esterno
0 3 * * 0 /home/appuser/backup_db_weekly.sh
```

**Test backup:**
```bash
# Esegui manualmente
./backup_db.sh

# Verifica file creato
ls -lh /backup/database/

# Test restore
gunzip < backup_20251110_020000.sql.gz | psql -U dbuser aivideomaker
```

**Off-site backup (IMPORTANTE):**

Server può prendere fuoco → backup locale persi. Usa:

**Opzione A: AWS S3**
```bash
pip install awscli
aws configure

# In backup_db.sh aggiungi:
aws s3 cp $BACKUP_DIR/backup_${DATE}.sql.gz s3://tuobucket/backups/
```

**Opzione B: Backblaze B2**
```bash
pip install b2sdk
b2 authorize-account $KEY_ID $APPLICATION_KEY

# In backup script:
b2 upload-file tuobucket $BACKUP_DIR/backup_${DATE}.sql.gz backups/backup_${DATE}.sql.gz
```

**Opzione C: rsync su server remoto**
```bash
rsync -avz /backup/database/ user@backup-server:/backups/aivideomaker/
```

---

## 12. Nessun Monitoring

### 🐛 Problema
Se app crasha in produzione, non lo sai finché users non si lamentano.

**Gravità:** 🟡 MEDIA

### ✅ Soluzione

**Setup Sentry per error tracking**

**Step 1: Registra su Sentry.io**
```
https://sentry.io → Sign Up → Create Project → Python/FastAPI
```

**Step 2: Installa SDK**
```bash
pip install sentry-sdk[fastapi]
```

**File:** `requirements.txt`
```
sentry-sdk[fastapi]==1.40.0
```

**Step 3: Configura**

**File:** `app/core/config.py`

```python
class Settings(BaseSettings):
    # Monitoring
    sentry_dsn: Optional[str] = Field(default=None, env="SENTRY_DSN")
    sentry_environment: str = Field(default="development", env="SENTRY_ENVIRONMENT")
    sentry_traces_sample_rate: float = Field(default=0.1, env="SENTRY_TRACES_SAMPLE_RATE")  # 10% requests
```

**File:** `main.py`

```python
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from app.core.config import settings

# Setup Sentry PRIMA di creare app
if settings.sentry_dsn:
    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.sentry_environment,
        traces_sample_rate=settings.sentry_traces_sample_rate,
        integrations=[
            FastApiIntegration(transaction_style="endpoint"),
            SqlalchemyIntegration(),
        ],
        # Capture user info per debugging
        send_default_pii=True,

        # Release tracking
        release=settings.app_version,

        # Performance monitoring
        profiles_sample_rate=0.1,  # 10% profiling
    )

app = FastAPI(...)
```

**File:** `.env.production`
```bash
SENTRY_DSN=https://xxxxx@yyyyy.ingest.sentry.io/zzzzz
SENTRY_ENVIRONMENT=production
SENTRY_TRACES_SAMPLE_RATE=0.1
```

**Step 4: Capture custom errors**

```python
import sentry_sdk

try:
    # Operazione critica
    result = process_video(video_path)
except Exception as e:
    # Log in Sentry con context
    sentry_sdk.capture_exception(e)
    sentry_sdk.set_context("video", {
        "path": video_path,
        "user_id": user_id,
        "job_id": job_id
    })
    raise
```

**Step 5: Setup Alerts**

In Sentry dashboard:
- Alert se > 10 errors/minuto
- Alert se > 50% error rate
- Alert su specific error types (DatabaseError, etc.)
- Notifiche su Slack/Email

**Uptime Monitoring:**

**Opzione A: UptimeRobot (free)**
```
https://uptimerobot.com
→ Add Monitor
→ URL: https://tuodominio.com/health
→ Interval: 5 minuti
→ Alert: Email quando down > 2 minuti
```

**Opzione B: Healthchecks.io**
```bash
# In backup script
curl -fsS -m 10 --retry 5 https://hc-ping.com/your-uuid-here
```

**Logging aggregato:**

**Opzione: Papertrail**
```bash
# Invia logs a Papertrail
echo "*.* @logs.papertrailapp.com:12345" >> /etc/rsyslog.conf
service rsyslog restart
```

---

# 📋 CHECKLIST COMPLETA PRE-PRODUZIONE

## Security

```
[ ] Admin route protetta server-side (require_admin in main.py)
[ ] Rate limiting implementato (slowapi su login, admin, API intensive)
[ ] CORS ristretto al tuo dominio (no "*")
[ ] File upload validation (size + MIME type reale con python-magic)
[ ] HTTPS forzato (HTTPSRedirectMiddleware + Nginx)
[ ] .env in .gitignore + secrets ruotati se già committati
[ ] Admin audit log implementato
[ ] Session timeout ridotto (15min admin, 1h user)
[ ] SQL injection audit (no string concatenation, solo ORM/parametri)
[ ] Path traversal protection (validate_path_in_directory)
[ ] CSRF protection (SameSite cookies)
[ ] Security headers (X-Frame-Options, CSP, etc.)
```

## Infrastructure

```
[ ] VPS configurato (ufw firewall, solo porte 22/80/443)
[ ] Nginx + SSL certificato (Let's Encrypt certbot)
[ ] Database backup automatico (cron daily + off-site S3/B2)
[ ] Monitoring setup (Sentry + UptimeRobot)
[ ] Logging aggregato (Papertrail o CloudWatch)
[ ] Docker deployment (docker-compose.yml)
[ ] Environment variables secure (no .env in prod, usa secrets manager)
[ ] Systemd service per auto-restart
[ ] Log rotation configurato
[ ] Disk space monitoring (alert se > 80%)
```

## Application

```
[ ] Refresh token implementato (rinnovo senza re-login)
[ ] Email verification attivo (no login senza verifica email)
[ ] Password reset funzionante
[ ] Admin audit logs visibili in dashboard
[ ] Error pages personalizzate (404, 500, etc.)
[ ] Rate limit response chiaro (429 con Retry-After header)
[ ] API documentation aggiornata (/docs)
[ ] Health check endpoint (/health)
```

## Compliance

```
[ ] Privacy Policy pubblicata
[ ] Terms of Service pubblicati
[ ] Cookie consent banner (se GDPR/EU)
[ ] Data export user (GDPR compliance)
[ ] Data deletion user (GDPR right to erasure)
[ ] Email notifications per data breach
```

## Performance

```
[ ] CDN per static files (Cloudflare)
[ ] Database indexes su colonne cercate frequentemente
[ ] Redis cache per session (opzionale)
[ ] Connection pooling database configurato
[ ] Upload size limits configurati
[ ] Request timeout configurato (60s max)
```

## Testing

```
[ ] Test rate limiting (curl loop)
[ ] Test file upload limits (file > 500MB)
[ ] Test CORS (curl da origin diverso)
[ ] Test admin route protection (senza token)
[ ] Test path traversal (input con ../)
[ ] Test SQL injection (sqlmap scan)
[ ] Load test (k6 o locust)
[ ] Backup restore test (disaster recovery)
```

---

# 🚀 DEPLOYMENT SICURO - STEP BY STEP

## Fase 1: Preparazione Server (1-2 ore)

```bash
# 1. Crea VPS (DigitalOcean/Linode/Hetzner)
# Ubuntu 22.04 LTS, 4GB RAM, 2 CPU

# 2. Primo accesso + hardening
ssh root@tuoip

# Update sistema
apt update && apt upgrade -y

# Crea user non-root
adduser appuser
usermod -aG sudo appuser
rsync --archive --chown=appuser:appuser ~/.ssh /home/appuser

# Disabilita root login
nano /etc/ssh/sshd_config
# PermitRootLogin no
# PasswordAuthentication no
systemctl restart sshd

# Setup firewall
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw enable

# Logout e riconnetti come appuser
exit
ssh appuser@tuoip
```

## Fase 2: Installa Dipendenze (30 min)

```bash
# Python 3.11
sudo apt install -y python3.11 python3.11-venv python3-pip

# PostgreSQL
sudo apt install -y postgresql postgresql-contrib
sudo -u postgres psql
CREATE DATABASE aivideomaker;
CREATE USER dbuser WITH PASSWORD 'strong_password_here';
GRANT ALL PRIVILEGES ON DATABASE aivideomaker TO dbuser;
\q

# Nginx
sudo apt install -y nginx

# Certbot (SSL)
sudo apt install -y certbot python3-certbot-nginx

# Docker (opzionale ma consigliato)
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker appuser

# Redis (per session cache)
sudo apt install -y redis-server
```

## Fase 3: Deploy Applicazione (1 ora)

```bash
# Clone repo
cd /home/appuser
git clone https://github.com/tuousername/AIVideoMaker.git
cd AIVideoMaker

# Checkout branch produzione
git checkout main  # o production branch

# Create venv
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Create directories
mkdir -p uploads logs backups

# Setup environment variables
nano .env.production
# (Copia contenuto .env.example e compila con valori reali)

# Generate secret key
openssl rand -hex 32
# Copia output in .env.production → SECRET_KEY=...

# Run database migrations
python migrate_db_subscription.py

# Test app locale
uvicorn main:app --host 127.0.0.1 --port 8000

# Se funziona, CTRL+C e procedi
```

## Fase 4: Setup Nginx + SSL (30 min)

```bash
# Config Nginx
sudo nano /etc/nginx/sites-available/aivideomaker

# Copia questa config:
```

```nginx
# File: /etc/nginx/sites-available/aivideomaker

server {
    listen 80;
    server_name tuodominio.com www.tuodominio.com;

    # Certbot challenge
    location /.well-known/acme-challenge/ {
        root /var/www/html;
    }

    # Redirect HTTP → HTTPS (dopo SSL setup)
    location / {
        return 301 https://$server_name$request_uri;
    }
}

server {
    listen 443 ssl http2;
    server_name tuodominio.com www.tuodominio.com;

    # SSL certificates (dopo certbot)
    ssl_certificate /etc/letsencrypt/live/tuodominio.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/tuodominio.com/privkey.pem;

    # SSL config sicura
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers on;
    ssl_ciphers ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-AES256-GCM-SHA384;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # Upload size limit
    client_max_body_size 500M;

    # Proxy to FastAPI
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
    }

    # Static files (opzionale)
    location /static/ {
        alias /home/appuser/AIVideoMaker/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

```bash
# Attiva config
sudo ln -s /etc/nginx/sites-available/aivideomaker /etc/nginx/sites-enabled/
sudo rm /etc/nginx/sites-enabled/default  # Rimuovi default
sudo nginx -t  # Test config

# Setup SSL certificato
sudo certbot --nginx -d tuodominio.com -d www.tuodominio.com

# Reload Nginx
sudo systemctl reload nginx
```

## Fase 5: Systemd Service (30 min)

```bash
# Create service file
sudo nano /etc/systemd/system/aivideomaker.service
```

```ini
[Unit]
Description=AIVideoMaker FastAPI Application
After=network.target postgresql.service

[Service]
Type=simple
User=appuser
Group=appuser
WorkingDirectory=/home/appuser/AIVideoMaker
Environment="PATH=/home/appuser/AIVideoMaker/venv/bin"
EnvironmentFile=/home/appuser/AIVideoMaker/.env.production
ExecStart=/home/appuser/AIVideoMaker/venv/bin/uvicorn main:app --host 127.0.0.1 --port 8000 --workers 4

# Restart automatico
Restart=always
RestartSec=5

# Limiti risorse
LimitNOFILE=65535
LimitNPROC=4096

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=aivideomaker

[Install]
WantedBy=multi-user.target
```

```bash
# Attiva service
sudo systemctl daemon-reload
sudo systemctl enable aivideomaker
sudo systemctl start aivideomaker

# Check status
sudo systemctl status aivideomaker

# View logs
sudo journalctl -u aivideomaker -f
```

## Fase 6: Monitoring + Backup (30 min)

```bash
# Setup Sentry (già fatto in app)
# Aggiungi SENTRY_DSN in .env.production

# Setup backup script
nano /home/appuser/backup_db.sh
# (Copia contenuto dal capitolo 11)

chmod +x /home/appuser/backup_db.sh

# Test backup
./backup_db.sh

# Setup cron
crontab -e
# Aggiungi:
0 2 * * * /home/appuser/backup_db.sh >> /var/log/db_backup.log 2>&1

# Setup UptimeRobot
# Vai su https://uptimerobot.com
# Add Monitor → URL → https://tuodominio.com/health → Interval 5min
```

## Fase 7: Test Finale

```bash
# Test endpoint pubblico
curl https://tuodominio.com/health
# Dovrebbe ritornare: {"status":"healthy",...}

# Test HTTPS
curl -I https://tuodominio.com
# Dovrebbe mostrare: HTTP/2 200

# Test rate limiting
for i in {1..10}; do curl https://tuodominio.com/api/v1/auth/login -X POST; done
# Dopo 5 richieste dovrebbe dare 429

# Test admin protection
curl https://tuodominio.com/admin
# Dovrebbe redirect a /login

# Load test (opzionale)
pip install locust
locust -f tests/load_test.py --host=https://tuodominio.com
```

---

# 💰 COSTI MENSILI STIMATI

## Setup Minimo (Per Iniziare)

| Servizio | Opzione | Costo/Mese |
|----------|---------|------------|
| **VPS** | DigitalOcean Droplet 4GB | €24 |
| **Database** | DigitalOcean Managed PostgreSQL 1GB | €15 |
| **Storage** | DigitalOcean Spaces 250GB | €5 |
| **CDN** | Cloudflare Free | €0 |
| **SSL** | Let's Encrypt | €0 |
| **Monitoring** | Sentry Developer (50k events) | €0 |
| **Uptime** | UptimeRobot Free | €0 |
| **Email** | Gmail SMTP | €0 |
| **Dominio** | .com (annuale / 12) | €1 |
| **TOTALE** | | **€45/mese** |

## Setup Scalato (Più Utenti)

| Servizio | Opzione | Costo/Mese |
|----------|---------|------------|
| **VPS** | DigitalOcean Droplet 8GB | €48 |
| **Database** | DigitalOcean Managed PostgreSQL 4GB | €60 |
| **Storage** | DigitalOcean Spaces 1TB | €20 |
| **CDN** | Cloudflare Pro | €20 |
| **Monitoring** | Sentry Team (100k events) | €26 |
| **Email** | SendGrid Essentials 50k/mese | €15 |
| **Backup** | Backblaze B2 500GB | €3 |
| **TOTALE** | | **€192/mese** |

## Alternative Budget

**VPS più economico:**
- Hetzner CX21 (2 vCPU, 4GB) → €5.83/mese
- Contabo VPS S (4 vCPU, 8GB) → €6.99/mese

**Database self-hosted:**
- PostgreSQL su stesso VPS → €0 (risparmi €15)
- Richiede backup manuale + più manutenzione

**Total Budget Minimo:** ~€15/mese (Hetzner VPS + Cloudflare + Sentry free)

---

# ⏱️ TIMELINE IMPLEMENTAZIONE

## Scenario A: Fix Critici Solo (Deploy Demo)

**Tempo:** 3-4 ore

```
[ ] 1h - Admin route protection + rate limiting
[ ] 1h - CORS fix + HTTPS redirect
[ ] 30min - File upload validation
[ ] 30min - Path traversal protection
[ ] 30min - Deploy su server test
```

**Risultato:** App funzionante ma NO production-ready. OK per demo privata.

## Scenario B: Production-Ready Completo

**Tempo:** 4-5 giorni full-time

```
Giorno 1 (8h): Security Fixes
[ ] 2h - Rate limiting (slowapi) su tutte le route
[ ] 2h - File upload validation (python-magic)
[ ] 2h - Admin audit log completo
[ ] 1h - Path traversal protection
[ ] 1h - Session timeout + refresh token

Giorno 2 (8h): Infrastructure
[ ] 2h - VPS setup + hardening
[ ] 2h - Nginx + SSL certificato
[ ] 2h - Database setup + backup script
[ ] 2h - Systemd service + monitoring

Giorno 3 (8h): Testing + Monitoring
[ ] 3h - Security testing (rate limit, CORS, injection)
[ ] 2h - Sentry setup + error tracking
[ ] 2h - Load testing
[ ] 1h - Backup restore test

Giorno 4 (8h): Compliance + Polish
[ ] 3h - Privacy policy + Terms + Cookie banner
[ ] 2h - Email notifications setup
[ ] 2h - Admin dashboard audit logs UI
[ ] 1h - Documentation

Giorno 5 (4h): Launch
[ ] 2h - Final testing + DNS setup
[ ] 1h - Monitoring dashboards
[ ] 1h - Announcement + first users
```

---

# 🆘 SUPPORTO

## Se hai problemi durante implementazione:

1. **Security issues:** Apri issue su GitHub (non pubblicare secrets)
2. **Deploy problems:** Check logs con `journalctl -u aivideomaker -f`
3. **Database errors:** Check connessione con `psql -U dbuser -d aivideomaker`
4. **Nginx errors:** Check con `sudo nginx -t` e `sudo tail -f /var/log/nginx/error.log`

## Resources utili:

- **FastAPI Security:** https://fastapi.tiangolo.com/tutorial/security/
- **OWASP Top 10:** https://owasp.org/www-project-top-ten/
- **Let's Encrypt:** https://certbot.eff.org/
- **Sentry Docs:** https://docs.sentry.io/platforms/python/guides/fastapi/

---

# 📞 CONCLUSIONE

**Domanda originale:** "Posso metterla online?"

**Risposta definitiva:** NO, non ora. Ma con 4-5 giorni di lavoro SÌ.

**Priorità immediata (se vuoi demo domani):**
1. Admin route protection (30min)
2. Rate limiting login (1h)
3. CORS fix (15min)
4. Deploy su Render.com (30min)

**Totale demo veloce:** 2-3 ore

**Ma per produzione vera:** Segui checklist completa (4-5 giorni).

---

**Vuoi che ti aiuti a implementare i fix critici adesso?**

Posso iniziare dal più importante e procedere in ordine di priorità.
