# GUIDA TEST SISTEMA - Step by Step

**Come testare tutte le funzionalità del sistema AIVideoMaker**

---

## 🚀 PASSO 1: AVVIA IL SERVER

```bash
cd /home/user/AIVideoMaker
python main.py
```

**Output atteso:**
```
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

Il server sarà disponibile su: **http://localhost:8000**

---

## 📚 PASSO 2: APRI SWAGGER UI (INTERFACCIA TEST)

Apri il browser e vai a:
```
http://localhost:8000/docs
```

Vedrai l'interfaccia interattiva Swagger con tutte le API disponibili divise per categoria:
- Authentication
- Chromakey
- Translation
- Thumbnail
- YouTube
- **Logo Overlay** ✅
- **Transcription** ✅ (NUOVO)
- **SEO Metadata AI** ✅ (NUOVO)
- Metadata
- Pipeline

---

## 🔐 PASSO 3: AUTENTICAZIONE

### 3.1 Registra un Utente

1. Espandi `POST /api/v1/auth/register`
2. Clicca "Try it out"
3. Inserisci dati:
```json
{
  "username": "ettore",
  "password": "test1234"
}
```
4. Clicca "Execute"

**Response atteso:** `201 Created`

### 3.2 Login

1. Espandi `POST /api/v1/auth/login`
2. Clicca "Try it out"
3. Inserisci credenziali (form OAuth2):
   - username: `ettore`
   - password: `test1234`
4. Clicca "Execute"

**Response atteso:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

### 3.3 Autorizza Swagger

1. Clicca il pulsante **"Authorize"** in alto a destra (icona lucchetto)
2. Inserisci:
   - username: `ettore`
   - password: `test1234`
3. Clicca "Authorize"
4. Chiudi il popup

**Ora tutte le chiamate API useranno automaticamente il token JWT!** 🔓

---

## 🎬 PASSO 4: TEST API STANDALONE

### Test 1: Logo Overlay (API Standalone)

**4.1 Upload File per Logo Overlay**

1. Espandi `POST /api/v1/logo/upload`
2. Clicca "Try it out"
3. Upload file:
   - `video_file`: Scegli un video MP4 (o usa `/tmp/test_media/video_test.mp4`)
   - `logo_file`: Scegli un'immagine PNG/JPG (o usa `/tmp/test_media/logo_test.png`)
4. Parametri:
```json
{
  "position": "bottom-right",
  "margin": 20,
  "logo_scale": 0.15,
  "opacity": 1.0,
  "quality": "high"
}
```
5. Clicca "Execute"

**Response atteso:**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "processing",
  "message": "Job avviato in background"
}
```

**4.2 Monitora Status Job**

1. Copia il `job_id` dalla response
2. Espandi `GET /api/v1/logo/jobs/{job_id}`
3. Clicca "Try it out"
4. Incolla il `job_id`
5. Clicca "Execute"
6. Ripeti ogni 5 secondi finché `status` diventa `"completed"`

**Response finale atteso:**
```json
{
  "job_id": "...",
  "status": "completed",
  "progress": 100,
  "result": {
    "output_path": "/path/to/output_with_logo.mp4",
    "duration_seconds": 10.5,
    "success": true
  }
}
```

✅ **Logo overlay funziona!**

---

### Test 2: Metadata Extraction

1. Espandi `POST /api/v1/metadata/upload`
2. Upload un video
3. Parametri:
```json
{
  "include_streams": true,
  "include_format": true,
  "include_chapters": false
}
```
4. Execute

**Response atteso:** Metadata completi del video (codec, bitrate, risoluzione, ecc.)

---

### Test 3: Transcription (se hai Whisper installato)

**NOTA:** Se Whisper non è installato, l'API risponderà con errore chiaro.

1. Espandi `POST /api/v1/transcription/upload`
2. Upload un video con audio
3. Parametri:
```json
{
  "model_size": "base",
  "language": "it",
  "task": "transcribe",
  "export_formats": ["json", "srt"],
  "word_timestamps": false
}
```
4. Execute
5. Monitora con `GET /api/v1/transcription/jobs/{job_id}`

**Se Whisper non installato:**
```json
{
  "detail": "Whisper non installato. Installa con: pip install openai-whisper"
}
```

**Se Whisper installato:** Ricevi trascrizione completa in JSON/SRT

---

### Test 4: SEO Metadata AI (se hai Whisper installato)

1. Espandi `POST /api/v1/seo/upload`
2. Upload un video
3. Parametri:
```json
{
  "num_hashtags": 10,
  "num_tags": 30,
  "language": "it",
  "generate_thumbnail": true,
  "thumbnail_style": "modern",
  "target_platform": "youtube"
}
```
4. Execute
5. Monitora con `GET /api/v1/seo/jobs/{job_id}`

**Response atteso:** Title, description, hashtags, tags ottimizzati SEO + thumbnail AI

---

## 🔄 PASSO 5: TEST PIPELINE (WORKFLOW COMPLETO)

### 5.1 Crea Pipeline Multi-Step

1. Espandi `POST /api/v1/pipeline/create`
2. Clicca "Try it out"
3. Inserisci configurazione pipeline:

```json
{
  "name": "Pipeline Test Completa",
  "description": "Test di tutti i servizi disponibili",
  "stop_on_error": true,
  "input_files": {
    "video": "/tmp/test_media/video_test.mp4",
    "logo": "/tmp/test_media/logo_test.png"
  },
  "steps": [
    {
      "step_number": 1,
      "job_type": "logo_overlay",
      "enabled": true,
      "parameters": {
        "video_path": "@input",
        "logo_path": "@input",
        "position": "bottom-right",
        "logo_scale": 0.15,
        "opacity": 1.0
      }
    },
    {
      "step_number": 2,
      "job_type": "metadata_extraction",
      "enabled": true,
      "parameters": {
        "video_path": "@previous",
        "include_streams": true,
        "include_format": true
      }
    },
    {
      "step_number": 3,
      "job_type": "thumbnail",
      "enabled": true,
      "parameters": {
        "source_type": "frame",
        "video_path": "@previous",
        "frame_timestamp": 5.0,
        "text": "Test Thumbnail",
        "enhance_ctr": true
      }
    }
  ]
}
```

4. Clicca "Execute"

**Response atteso:**
```json
{
  "pipeline_id": "abc-123-def-456",
  "status": "created",
  "total_steps": 3,
  "enabled_steps": 3
}
```

### 5.2 Esegui Pipeline

1. Copia il `pipeline_id`
2. Espandi `POST /api/v1/pipeline/{pipeline_id}/execute`
3. Incolla il `pipeline_id`
4. Clicca "Execute"

**Response atteso:**
```json
{
  "message": "Pipeline avviata in background",
  "pipeline_id": "abc-123-def-456"
}
```

### 5.3 Monitora Esecuzione Pipeline

1. Espandi `GET /api/v1/pipeline/{pipeline_id}`
2. Incolla il `pipeline_id`
3. Clicca "Execute"
4. Ripeti ogni 5 secondi

**Output durante esecuzione:**
```json
{
  "id": "abc-123-def-456",
  "name": "Pipeline Test Completa",
  "status": "running",
  "current_step": 2,
  "total_steps": 3,
  "message": "Esecuzione metadata_extraction...",
  "progress": 66
}
```

**Output finale:**
```json
{
  "status": "completed",
  "current_step": 3,
  "total_steps": 3,
  "message": "Pipeline completata con successo!",
  "result": {
    "logo_overlay": { "success": true, "output_path": "..." },
    "metadata_extraction": { "success": true, "metadata": {...} },
    "thumbnail": { "success": true, "output_path": "..." }
  },
  "output_files": {
    "video": "/path/to/video_with_logo.mp4",
    "thumbnail": "/path/to/thumbnail.jpg",
    "metadata": {...}
  }
}
```

✅ **Pipeline completa funziona!**

---

## 📋 PASSO 6: VERIFICA TUTTI I SERVIZI

### Checklist Test Servizi

Testa ogni servizio individualmente:

- [ ] **Chromakey** - `POST /api/v1/chromakey/upload`
  - Upload foreground (green screen) + background
  - Verifica output con sfondo sostituito

- [ ] **Translation** - `POST /api/v1/translation/upload`
  - Upload video con audio
  - Seleziona lingua target (es: `en`, `es`, `fr`)
  - Verifica video tradotto

- [ ] **Thumbnail** - `POST /api/v1/thumbnail/generate`
  - Test mode "frame" (estrai da video)
  - Test mode "ai" (genera con AI)
  - Test mode "upload" (upload immagine + overlay testo)

- [ ] **YouTube Upload** - `POST /api/v1/youtube/upload-files`
  - **NOTA:** Richiede OAuth2 credentials YouTube configurato
  - Se non configurato, API risponderà con errore chiaro

- [ ] **Logo Overlay** - `POST /api/v1/logo/upload` ✅
  - Già testato sopra

- [ ] **Transcription** - `POST /api/v1/transcription/upload` ✅
  - Già testato sopra

- [ ] **Metadata** - `POST /api/v1/metadata/upload` ✅
  - Già testato sopra

- [ ] **SEO Metadata** - `POST /api/v1/seo/upload` ✅
  - Già testato sopra

---

## 🧪 PASSO 7: TEST DA TERMINALE (ALTERNATIVO)

Se preferisci testare via `curl` invece di Swagger:

### Login e ottieni token
```bash
# Login
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=ettore&password=test1234"

# Salva il token
export TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

### Test Logo Overlay
```bash
curl -X POST "http://localhost:8000/api/v1/logo/upload" \
  -H "Authorization: Bearer $TOKEN" \
  -F "video_file=@/tmp/test_media/video_test.mp4" \
  -F "logo_file=@/tmp/test_media/logo_test.png" \
  -F "position=bottom-right" \
  -F "logo_scale=0.15"
```

### Monitora Job
```bash
# Sostituisci JOB_ID con quello ricevuto
curl -X GET "http://localhost:8000/api/v1/logo/jobs/JOB_ID" \
  -H "Authorization: Bearer $TOKEN"
```

---

## 🐛 TROUBLESHOOTING

### Server non si avvia
```bash
# Verifica dipendenze
pip install -r requirements.txt

# Verifica database
ls -la database.db

# Controlla logs
python main.py 2>&1 | tee server.log
```

### API risponde 401 Unauthorized
- Verifica di aver fatto login
- Verifica di aver cliccato "Authorize" in Swagger
- Il token JWT scade dopo 30 giorni, ri-fai login

### Job rimane "processing" per sempre
- Controlla i logs del server
- Verifica che i file input esistano
- Alcuni servizi richiedono FFmpeg installato

### Whisper non disponibile
```bash
# Installa Whisper (opzionale)
pip install openai-whisper

# Verifica installazione
python -c "import whisper; print('OK')"
```

### FFmpeg non trovato
```bash
# Installa FFmpeg
sudo apt-get update
sudo apt-get install -y ffmpeg

# Verifica installazione
ffmpeg -version
```

---

## 📊 VERIFICA STATO SISTEMA

### Controlla servizi disponibili
```bash
python -c "
from app.pipelines.orchestrator import PipelineOrchestrator
from app.core.database import SessionLocal

db = SessionLocal()
orch = PipelineOrchestrator(db)

print('Servizi inizializzati:')
print('1. Chromakey:', hasattr(orch, 'chromakey_service'))
print('2. Translation:', hasattr(orch, 'translation_service'))
print('3. Thumbnail:', hasattr(orch, 'thumbnail_service'))
print('4. YouTube:', hasattr(orch, 'youtube_service'))
print('5. Logo:', hasattr(orch, 'logo_overlay_service'))
print('6. Transcription:', hasattr(orch, 'transcription_service'))
print('7. Metadata:', hasattr(orch, 'metadata_service'))
print('8. SEO:', hasattr(orch, 'seo_metadata_service'))
"
```

**Output atteso:** Tutti `True`

---

## 🎯 TEST RAPIDO COMPLETO (5 MINUTI)

**Quick Start Test:**

1. **Avvia server** → `python main.py`
2. **Apri Swagger** → http://localhost:8000/docs
3. **Registra** → `POST /auth/register` (ettore / test1234)
4. **Autorizza** → Pulsante "Authorize" in alto
5. **Test Logo** → `POST /logo/upload` con video + logo
6. **Test Pipeline** → Crea pipeline con 2-3 step
7. **Verifica Output** → Controlla file generati in `output/`

**Se tutto funziona:** ✅ Sistema operativo al 100%

---

## 📁 FILE OUTPUT

I file generati dalle API vengono salvati in:
```
/home/user/AIVideoMaker/output/
```

Controlla contenuto:
```bash
ls -lah /home/user/AIVideoMaker/output/
```

---

## 🎉 CONCLUSIONE

**Sistema completamente testato se:**
- ✅ Server si avvia senza errori
- ✅ Login funziona e ricevi token JWT
- ✅ Almeno 1 API standalone funziona (es: logo, metadata)
- ✅ Pipeline multi-step completa con successo
- ✅ File output vengono generati correttamente

**Hai testato tutto?** Sistema pronto per produzione! 🚀

---

**Guida creata da:** Claude Code
**Data:** 2025-11-08
**Versione sistema:** 8/9 servizi attivi (88.9%)
