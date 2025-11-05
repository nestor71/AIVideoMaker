# 🎬 AIVideoMaker Professional v2.0.0

## Architettura Modulare Enterprise-Grade

**REFACTORING COMPLETO**: Da monolite a architettura modulare professionale.

---

## ✨ Novità Principali

### 🔧 **Servizi Indipendenti**
Ogni funzionalità è un servizio autonomo, testabile, riutilizzabile:

- `ChromakeyService` - Green screen processing
- `TranslationService` - Traduzione video multilingua
- `ThumbnailService` - Generazione miniature AI
- `YouTubeService` - Upload automatico YouTube

### 🚀 **Sistema AUTO (PipelineOrchestrator)**
**NOVITÀ RICHIESTA**: Orchestrazione automatica di job multipli!

```python
# Esempio Pipeline AUTO completa:
pipeline = Pipeline(
    name="Video Completo",
    steps=[
        {"job_type": "chromakey", "enabled": True, "parameters": {...}},
        {"job_type": "thumbnail", "enabled": True, "parameters": {...}},
        {"job_type": "translation", "enabled": False, "parameters": {...}},
        {"job_type": "youtube_upload", "enabled": True, "parameters": {...}}
    ]
)

# Esegue tutti gli step abilitati in sequenza
orchestrator.execute_pipeline(pipeline)
```

**Puoi attivare/disattivare ogni funzione dinamicamente!**

### 🔐 **Sicurezza Enterprise**
- Autenticazione JWT + API keys
- Rate limiting
- Validazione rigorosa input
- Password hashing (bcrypt)

### 🗄️ **Database PostgreSQL**
- Tracking job persistente
- Pipeline history
- User management
- File metadata

### 📦 **Docker + Celery**
- Deploy production-ready
- Background tasks con Celery
- Scalabilità orizzontale
- Monitoring con Flower

---

## 🏗️ Struttura Progetto

```
AIVideoMaker/
├── app/
│   ├── api/
│   │   └── routes/           # API endpoints modulari
│   ├── services/             # Business logic indipendente
│   │   ├── chromakey_service.py
│   │   ├── translation_service.py
│   │   ├── thumbnail_service.py
│   │   └── youtube_service.py
│   ├── pipelines/
│   │   └── orchestrator.py   # 🎯 Sistema AUTO
│   ├── models/               # Database models
│   │   ├── user.py
│   │   ├── job.py
│   │   └── pipeline.py
│   ├── core/
│   │   ├── config.py         # Configurazione centralizzata
│   │   ├── database.py
│   │   └── security.py
│   └── workers/              # Celery tasks
├── tests/
│   ├── unit/
│   ├── integration/
│   └── e2e/
├── docker/
│   ├── Dockerfile
│   └── docker-compose.yml
├── main.py                   # Entry point
├── requirements_new.txt
└── .env.example

BACKUP ORIGINALE:
└── backup_refactoring_20251105_124826/
```

---

## 🚀 Quick Start

### 1. Setup Ambiente

```bash
# Copia configurazione
cp .env.example .env

# Modifica .env con tue API keys
nano .env  # Configura SECRET_KEY, OPENAI_API_KEY, etc.
```

### 2. Opzione A: Docker (RACCOMANDATO)

```bash
# Avvia tutto (PostgreSQL + Redis + API + Celery)
cd docker
docker-compose up -d

# Check logs
docker-compose logs -f api

# Accedi
# API: http://localhost:8000
# Swagger UI: http://localhost:8000/docs
# Flower (Celery): http://localhost:5555
```

### 3. Opzione B: Manuale (Development)

```bash
# Installa dipendenze
pip install -r requirements_new.txt

# Avvia PostgreSQL e Redis localmente
# (o usa Docker solo per questi)

# Avvia applicazione
python main.py

# In altra terminal: Avvia Celery worker
celery -A app.workers.celery_app worker --loglevel=info
```

---

## 📖 Uso Sistema AUTO

### Esempio Completo: Video Processing Automatico

```python
from app.pipelines.orchestrator import PipelineOrchestrator
from app.models.pipeline import Pipeline, PipelineStatus
from sqlalchemy.orm import Session

# 1. Crea Pipeline
pipeline = Pipeline(
    user_id=user.id,
    name="Video Marketing Completo",
    description="Chromakey + Thumbnail + YouTube Upload",
    steps=[
        {
            "step_number": 1,
            "job_type": "chromakey",
            "enabled": True,
            "parameters": {
                "foreground_path": "uploads/cta.mp4",
                "background_path": "uploads/background.mp4",
                "start_time": 5.0,
                "audio_mode": "synced"
            }
        },
        {
            "step_number": 2,
            "job_type": "thumbnail",
            "enabled": True,
            "parameters": {
                "source_type": "ai",
                "ai_style": "cinematic",
                "ai_description": "Epic video thumbnail",
                "text": "NOVITÀ 2025!",
                "enhance_ctr": True
            }
        },
        {
            "step_number": 3,
            "job_type": "youtube_upload",
            "enabled": True,
            "parameters": {
                "title": "Il Mio Video Epico",
                "description": "Descrizione...",
                "privacy_status": "public",
                "tags": ["marketing", "video"]
            }
        }
    ],
    total_steps=3,
    input_files={
        "foreground": "uploads/cta.mp4",
        "background": "uploads/background.mp4"
    }
)

db.add(pipeline)
db.commit()

# 2. Esegui Pipeline
orchestrator = PipelineOrchestrator(db)

result = orchestrator.execute_pipeline(
    pipeline,
    progress_callback=lambda p, m: print(f"{p}%: {m}")
)

# 3. Risultato
print(f"✅ Pipeline completata!")
print(f"Video YouTube: {result['results']['youtube_upload']['url']}")
print(f"Thumbnail: {result['results']['thumbnail']['output_path']}")
```

### Attiva/Disattiva Funzioni Dinamicamente

```python
# Vuoi solo traduzione? Disattiva gli altri step!
pipeline.steps = [
    {"step_number": 1, "job_type": "translation", "enabled": True, "parameters": {...}},
    {"step_number": 2, "job_type": "chromakey", "enabled": False, "parameters": {...}},
    {"step_number": 3, "job_type": "thumbnail", "enabled": False, "parameters": {...}}
]

# Esegue SOLO la traduzione
orchestrator.execute_pipeline(pipeline)
```

---

## 🔌 API Endpoints (Da Implementare)

```
POST /api/v1/auth/register         # Registrazione utente
POST /api/v1/auth/login            # Login (JWT token)

POST /api/v1/chromakey/process     # Chromakey standalone
POST /api/v1/translation/translate # Traduzione standalone
POST /api/v1/thumbnail/generate    # Thumbnail standalone
POST /api/v1/youtube/upload        # YouTube upload standalone

POST /api/v1/pipeline/create       # Crea pipeline AUTO
POST /api/v1/pipeline/{id}/start   # Avvia pipeline
GET  /api/v1/pipeline/{id}/status  # Status pipeline
```

---

## 🧪 Testing

```bash
# Run test suite
pytest

# Con coverage
pytest --cov=app --cov-report=html

# Solo unit tests
pytest tests/unit/

# Solo integration tests
pytest tests/integration/
```

---

## 📦 Deployment Production

### Docker Swarm / Kubernetes

```bash
# Build immagine
docker build -f docker/Dockerfile -t aivideomaker:2.0.0 .

# Push registry
docker tag aivideomaker:2.0.0 your-registry/aivideomaker:2.0.0
docker push your-registry/aivideomaker:2.0.0

# Deploy
kubectl apply -f k8s/deployment.yaml
```

### Scaling Celery Workers

```bash
# Scale workers per processing pesante
docker-compose up -d --scale celery_worker=5
```

---

## 🔧 Configurazione Avanzata

### Personalizza Servizi

Ogni servizio accetta configurazione custom:

```python
from app.services.chromakey_service import ChromakeyService
from app.core.config import Settings

# Config custom
custom_config = Settings(
    ffmpeg_path="/usr/local/bin/ffmpeg",
    chromakey_blur_kernel=7
)

service = ChromakeyService(config=custom_config)
```

### Background Tasks Celery

```python
# app/workers/tasks.py
from celery import Celery

@celery.task
def process_video_async(pipeline_id: str):
    # Processing in background
    orchestrator.execute_pipeline(pipeline_id)
```

---

## 📊 Monitoring

### Prometheus Metrics

```
http://localhost:8000/metrics
```

### Celery Monitoring (Flower)

```
http://localhost:5555
```

### Logs

```bash
# Docker logs
docker-compose logs -f api

# File logs
tail -f logs/app.log
```

---

## 🆘 Troubleshooting

### Database non si connette

```bash
# Verifica PostgreSQL running
docker-compose ps postgres

# Check connessione
docker-compose exec postgres psql -U aivideomaker -d aivideomaker
```

### FFmpeg non trovato

```bash
# Installa FFmpeg
# Ubuntu/Debian:
sudo apt-get install ffmpeg

# macOS:
brew install ffmpeg

# Docker: già incluso nell'immagine
```

### OpenAI API key invalida

```bash
# Verifica .env
cat .env | grep OPENAI_API_KEY

# Testa key
python -c "from openai import OpenAI; client = OpenAI(); print(client.models.list())"
```

---

## 🔄 Migrazione da Vecchio Codice

Il codice originale è salvato in:
```
backup_refactoring_20251105_124826/
```

**Non eliminare backup!** Utile per riferimenti durante transizione.

---

## 🎯 Prossimi Step Suggeriti

1. ✅ **Testa servizi standalone**
   ```bash
   python -m pytest tests/unit/test_chromakey_service.py
   ```

2. ✅ **Implementa API routes**
   - Crea `app/api/routes/chromakey.py`
   - Crea `app/api/routes/pipeline.py`

3. ✅ **Frontend adattato**
   - Aggiorna `templates/` per nuova API
   - Integra sistema AUTO nell'interfaccia

4. ✅ **Deploy production**
   - Configura HTTPS
   - Setup CDN per static files
   - Monitoring completo

---

## 🤝 Contributing

```bash
# Format code
black app/ tests/

# Lint
flake8 app/ tests/

# Type check
mypy app/
```

---

## 📄 License

MIT License

---

## 🙏 Credits

**Refactoring completo da monolite a architettura modulare enterprise-grade.**

Ettore - Product Owner
Claude Code - Lead Developer

---

**Versione**: 2.0.0 (Professional Edition)
**Data**: 5 Novembre 2025
**Status**: ✅ Core Implementato - Ready for Integration

---

## 📞 Support

Per domande o supporto, consulta:
- 📚 `/docs` - Swagger UI interactive
- 🐛 GitHub Issues
- 📧 Email support
