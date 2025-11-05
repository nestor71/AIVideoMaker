# 🚀 Guida Setup AIVideoMaker v2.0 sul Tuo PC

**Versione**: 2.0.0 Professional Edition
**Data**: 5 Novembre 2025
**Branch**: `claude/project-review-improvements-011CUpkeELM78WpjRDQLfS6q`

---

## 📋 Prerequisiti

### **Obbligatori:**
- Git installato
- Python 3.11+ installato
- FFmpeg installato (per video processing)

### **Opzionali (per Docker):**
- Docker Desktop installato
- Docker Compose installato

---

## 🎯 Setup Rapido (5 Minuti)

### **STEP 1: Scarica Branch con Nuova Architettura**

Apri terminale e vai nella cartella del progetto:

```bash
# Se hai già il repository
cd /path/to/AIVideoMaker

# Scarica branch refactoring
git fetch origin
git checkout claude/project-review-improvements-011CUpkeELM78WpjRDQLfS6q
git pull origin claude/project-review-improvements-011CUpkeELM78WpjRDQLfS6q

# Verifica che sei sul branch giusto
git branch

# Dovresti vedere:
# * claude/project-review-improvements-011CUpkeELM78WpjRDQLfS6q
```

**OPPURE** se non hai il repo, clona:

```bash
git clone https://github.com/nestor71/AIVideoMaker.git
cd AIVideoMaker
git checkout claude/project-review-improvements-011CUpkeELM78WpjRDQLfS6q
```

### **STEP 2: Verifica Nuovi File**

```bash
# Verifica che ci siano i nuovi file
ls -la app/
ls -la docker/
ls main.py
ls requirements_new.txt

# Dovresti vedere:
# app/core/, app/models/, app/services/, app/pipelines/
# docker/Dockerfile, docker/docker-compose.yml
# main.py, requirements_new.txt
```

---

## 🐳 Metodo A: Docker (RACCOMANDATO - Più Semplice)

**Vantaggi**: Setup automatico, PostgreSQL + Redis inclusi, nessuna configurazione manuale.

### **1. Verifica Docker**

```bash
# Verifica che Docker sia installato
docker --version
docker-compose --version

# Se non installato:
# Windows/Mac: Installa Docker Desktop
# Linux: sudo apt-get install docker.io docker-compose
```

### **2. Configura Environment**

```bash
# Copia template configurazione
cp .env.example .env

# Modifica .env (IMPORTANTE!)
nano .env   # o usa il tuo editor preferito

# Modifica ALMENO queste righe:
# SECRET_KEY=genera_chiave_random_di_32_caratteri_minimo
# OPENAI_API_KEY=sk-...tua-chiave...  (se vuoi thumbnail AI)
```

**Genera SECRET_KEY random:**
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

### **3. Avvia con Docker**

```bash
# Vai in directory docker
cd docker

# Avvia tutti i servizi (PostgreSQL + Redis + API + Celery)
docker-compose up -d

# Aspetta 10 secondi che tutto parta
sleep 10

# Verifica che tutto sia avviato
docker-compose ps

# Dovresti vedere:
# aivideomaker_api       Running   0.0.0.0:8000->8000/tcp
# aivideomaker_db        Running   0.0.0.0:5432->5432/tcp
# aivideomaker_redis     Running   0.0.0.0:6379->6379/tcp
# aivideomaker_worker    Running
# aivideomaker_flower    Running   0.0.0.0:5555->5555/tcp
```

### **4. Test Applicazione**

Apri browser:

- **API**: http://localhost:8000
  - Dovresti vedere: `{"status": "running", "version": "2.0.0"}`

- **Swagger UI (Documentazione API)**: http://localhost:8000/docs
  - Interfaccia interattiva per testare API

- **Health Check**: http://localhost:8000/health
  - Dovresti vedere: `{"status": "healthy"}`

- **Celery Flower (Monitoring)**: http://localhost:5555
  - Dashboard tasks in background

### **5. Visualizza Logs**

```bash
# Logs applicazione
docker-compose logs -f api

# Logs database
docker-compose logs postgres

# Logs tutti i servizi
docker-compose logs -f

# Stop logs: CTRL+C
```

### **6. Stop/Restart**

```bash
# Stop tutti i servizi
docker-compose down

# Restart
docker-compose up -d

# Stop e rimuovi anche volumi (ATTENZIONE: cancella database!)
docker-compose down -v
```

---

## 💻 Metodo B: Setup Manuale (Se Non Usi Docker)

**Vantaggi**: Vedi tutto in dettaglio, debugging più facile.
**Svantaggi**: Devi installare PostgreSQL e Redis manualmente.

### **1. Installa Dipendenze Sistema**

#### **Windows:**
```powershell
# Installa Python 3.11+ da python.org
# Installa FFmpeg da ffmpeg.org

# Verifica
python --version
ffmpeg -version
```

#### **macOS:**
```bash
# Con Homebrew
brew install python@3.11 ffmpeg postgresql redis

# Avvia servizi
brew services start postgresql
brew services start redis
```

#### **Linux (Ubuntu/Debian):**
```bash
sudo apt-get update
sudo apt-get install -y python3.11 python3-pip ffmpeg postgresql redis-server

# Avvia servizi
sudo systemctl start postgresql
sudo systemctl start redis
```

### **2. Setup Database PostgreSQL**

```bash
# Crea database e utente
sudo -u postgres psql

# In psql:
CREATE DATABASE aivideomaker;
CREATE USER aivideomaker WITH PASSWORD 'password';
GRANT ALL PRIVILEGES ON DATABASE aivideomaker TO aivideomaker;
\q
```

### **3. Configura Environment**

```bash
# Torna in directory progetto
cd /path/to/AIVideoMaker

# Copia configurazione
cp .env.example .env

# Modifica .env
nano .env

# Imposta:
SECRET_KEY=genera_chiave_random_32_caratteri
DATABASE_URL=postgresql://aivideomaker:password@localhost:5432/aivideomaker
REDIS_URL=redis://localhost:6379/0
OPENAI_API_KEY=sk-...tua-chiave...  (opzionale)
```

### **4. Installa Dipendenze Python**

```bash
# Crea virtual environment (RACCOMANDATO)
python3 -m venv venv

# Attiva virtual environment
# Linux/Mac:
source venv/bin/activate
# Windows:
venv\Scripts\activate

# Installa dipendenze
pip install -r requirements_new.txt

# Se errori con alcune dipendenze, installa una alla volta:
pip install fastapi uvicorn sqlalchemy psycopg2-binary pydantic-settings
pip install pillow requests python-jose passlib
```

### **5. Avvia Applicazione**

```bash
# Avvia server
python main.py

# Dovresti vedere:
# 🚀 Avvio AIVideoMaker Professional v2.0.0
# ✅ Database ready
# ✅ Startup completato
# INFO: Uvicorn running on http://0.0.0.0:8000
```

### **6. Test Applicazione**

Apri browser:
- http://localhost:8000
- http://localhost:8000/docs
- http://localhost:8000/health

### **7. Avvia Celery Worker (Opzionale - per background tasks)**

In **ALTRO terminale**:

```bash
# Attiva venv se necessario
source venv/bin/activate

# Avvia worker
celery -A app.workers.celery_app worker --loglevel=info
```

---

## 🧪 Test Architettura

### **Test 1: Verifica Import Moduli**

```bash
python3 << 'EOF'
print("Test import moduli...")

from app.core.config import settings
print(f"✅ Config: {settings.app_name} v{settings.app_version}")

from app.models.user import User
from app.models.job import Job, JobType
from app.models.pipeline import Pipeline
print("✅ Models: User, Job, Pipeline")

from app.services.chromakey_service import ChromakeyService
from app.services.translation_service import TranslationService
from app.services.thumbnail_service import ThumbnailService
from app.services.youtube_service import YouTubeService
print("✅ Services: Chromakey, Translation, Thumbnail, YouTube")

from app.pipelines.orchestrator import PipelineOrchestrator
print("✅ PipelineOrchestrator (Sistema AUTO)")

print("\n🎉 Tutti i moduli OK!")
EOF
```

### **Test 2: Test HTTP Endpoints**

```bash
# Test root
curl http://localhost:8000/

# Test health
curl http://localhost:8000/health

# Test Swagger UI
curl -I http://localhost:8000/docs
```

### **Test 3: Test Database**

```bash
python3 << 'EOF'
from app.core.database import engine
from sqlalchemy import text

# Test connessione
with engine.connect() as conn:
    result = conn.execute(text("SELECT version()"))
    print(f"✅ PostgreSQL: {result.fetchone()[0]}")

    # Verifica tabelle create
    result = conn.execute(text("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema='public'
    """))
    tables = [row[0] for row in result]
    print(f"✅ Tabelle: {tables}")
EOF
```

---

## 🎯 Test Sistema AUTO

### **Esempio: Pipeline Completa**

Crea file `test_pipeline.py`:

```python
from app.core.database import SessionLocal
from app.models.user import User
from app.models.pipeline import Pipeline, PipelineStatus
from app.pipelines.orchestrator import PipelineOrchestrator
from app.core.security import get_password_hash
import uuid

# Crea database session
db = SessionLocal()

# Crea utente test
user = User(
    id=uuid.uuid4(),
    email="ettore@test.com",
    username="ettore",
    hashed_password=get_password_hash("password123"),
    full_name="Ettore",
    is_active=True
)
db.add(user)
db.commit()

# Crea pipeline AUTO
pipeline = Pipeline(
    id=uuid.uuid4(),
    user_id=user.id,
    name="Test Pipeline AUTO",
    description="Chromakey + Thumbnail + YouTube",
    steps=[
        {
            "step_number": 1,
            "job_type": "chromakey",
            "enabled": True,  # ✅ ATTIVO
            "parameters": {
                "start_time": 5.0,
                "audio_mode": "synced"
            }
        },
        {
            "step_number": 2,
            "job_type": "thumbnail",
            "enabled": True,  # ✅ ATTIVO
            "parameters": {
                "source_type": "ai",
                "ai_style": "cinematic"
            }
        },
        {
            "step_number": 3,
            "job_type": "translation",
            "enabled": False,  # ❌ DISATTIVATO
            "parameters": {
                "target_language": "en"
            }
        },
        {
            "step_number": 4,
            "job_type": "youtube_upload",
            "enabled": True,  # ✅ ATTIVO
            "parameters": {
                "title": "Test Video",
                "privacy_status": "private"
            }
        }
    ],
    total_steps=4,
    input_files={
        "foreground": "uploads/test_cta.mp4",
        "background": "uploads/test_bg.mp4"
    }
)

db.add(pipeline)
db.commit()

print(f"✅ Pipeline creata: {pipeline.id}")
print(f"   Nome: {pipeline.name}")
print(f"   Step totali: {pipeline.total_steps}")
print(f"   Step attivi: {len(pipeline.enabled_steps)}")
print()

# Mostra configurazione
for step in pipeline.steps:
    status = "✅" if step["enabled"] else "❌"
    print(f"   {status} Step {step['step_number']}: {step['job_type']}")

# Per eseguire la pipeline (quando hai i file):
# orchestrator = PipelineOrchestrator(db)
# result = orchestrator.execute_pipeline(pipeline)

db.close()
```

Esegui:
```bash
python test_pipeline.py
```

---

## ⚠️ Troubleshooting

### **Errore: "ModuleNotFoundError"**

```bash
# Verifica che sei nel venv
which python3

# Reinstalla dipendenze
pip install -r requirements_new.txt
```

### **Errore: "Database connection refused"**

```bash
# Verifica PostgreSQL running
# Linux:
sudo systemctl status postgresql

# Mac:
brew services list

# Docker:
docker-compose ps postgres
```

### **Errore: "Redis connection refused"**

```bash
# Verifica Redis running
# Linux:
sudo systemctl status redis

# Mac:
brew services list

# Docker:
docker-compose ps redis
```

### **Errore: "FFmpeg not found"**

```bash
# Installa FFmpeg
# Ubuntu/Debian:
sudo apt-get install ffmpeg

# macOS:
brew install ffmpeg

# Windows:
# Scarica da ffmpeg.org e aggiungi al PATH

# Verifica installazione
ffmpeg -version
```

### **Errore: "SECRET_KEY validation failed"**

```bash
# Genera SECRET_KEY valida
python3 -c "import secrets; print(secrets.token_hex(32))"

# Copia output in .env:
SECRET_KEY=<output_comando_sopra>
```

---

## 📚 Documentazione Completa

- **README_NEW_ARCHITECTURE.md** - Guida completa architettura
- **requirements_new.txt** - Dipendenze Python
- **docker/docker-compose.yml** - Configurazione Docker
- **.env.example** - Template configurazione

---

## 🆘 Supporto

Se hai problemi:

1. **Verifica logs**:
   - Docker: `docker-compose logs -f api`
   - Manuale: guarda output terminale

2. **Verifica configurazione**:
   ```bash
   cat .env
   ```

3. **Test connessioni**:
   ```bash
   # Test PostgreSQL
   psql -h localhost -U aivideomaker -d aivideomaker

   # Test Redis
   redis-cli ping
   ```

4. **Problemi? Contattami!**

---

## ✅ Checklist Setup

- [ ] Git branch scaricato: `claude/project-review-improvements-011CUpkeELM78WpjRDQLfS6q`
- [ ] File `.env` configurato (SECRET_KEY, DATABASE_URL, etc.)
- [ ] Dipendenze installate: `pip install -r requirements_new.txt`
- [ ] PostgreSQL + Redis running
- [ ] Applicazione avviata: `python main.py`
- [ ] Test endpoints: http://localhost:8000/health → `{"status": "healthy"}`
- [ ] Swagger UI accessibile: http://localhost:8000/docs

---

## 🎯 Prossimi Step Dopo Test

Quando tutto funziona, dimmi:
- ✅ Tutto OK, procedi con API routes
- ✅ Tutto OK, procedi con frontend
- ❌ Ho un problema: [descrivi]

---

**Buon test Ettore!** 🚀

Se hai dubbi durante il setup, fammi sapere esattamente a che punto sei e ti aiuto!
