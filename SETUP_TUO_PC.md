# SETUP SUL TUO PC - Guida Completa

**Come installare e testare AIVideoMaker sul tuo computer personale**

---

## 📋 PREREQUISITI

Prima di iniziare, assicurati di avere installato:

- **Python 3.9+** (consigliato 3.10 o 3.11)
- **Git**
- **pip** (package manager Python)

### Verifica versioni

Apri il terminale e controlla:

```bash
python --version   # Deve essere >= 3.9
# Oppure
python3 --version

git --version      # Qualsiasi versione va bene
pip --version      # Deve corrispondere alla versione Python
```

**Su Windows:** Usa `py` invece di `python` se necessario.

---

## 🔽 PASSO 1: CLONA IL REPOSITORY

### Opzione A: Se hai già clonato il repo

```bash
cd /percorso/dove/hai/AIVideoMaker
git checkout main  # O il branch principale
git pull origin main
git checkout claude/project-review-improvements-011CUpkeELM78WpjRDQLfS6q
```

### Opzione B: Clona da zero

```bash
# Vai nella cartella dove vuoi il progetto
cd ~/Documenti/  # O dove preferisci

# Clona il repository
git clone https://github.com/nestor71/AIVideoMaker.git
# OPPURE se usi SSH:
# git clone git@github.com:nestor71/AIVideoMaker.git

cd AIVideoMaker

# Passa al branch con tutte le fix
git checkout claude/project-review-improvements-011CUpkeELM78WpjRDQLfS6q
```

---

## 🐍 PASSO 2: CREA AMBIENTE VIRTUALE (CONSIGLIATO)

**Perché?** Per isolare le dipendenze del progetto dal tuo Python di sistema.

### Su Linux/Mac:

```bash
cd AIVideoMaker

# Crea virtual environment
python3 -m venv venv

# Attiva virtual environment
source venv/bin/activate

# Vedrai (venv) nel prompt:
# (venv) user@computer:~/AIVideoMaker$
```

### Su Windows (PowerShell):

```powershell
cd AIVideoMaker

# Crea virtual environment
py -m venv venv

# Attiva virtual environment
.\venv\Scripts\Activate.ps1

# Se ricevi errore di execution policy:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
# Poi riprova .\venv\Scripts\Activate.ps1
```

### Su Windows (CMD):

```cmd
cd AIVideoMaker
py -m venv venv
venv\Scripts\activate.bat
```

---

## 📦 PASSO 3: INSTALLA DIPENDENZE

Con il virtual environment **attivo** (vedi `(venv)` nel prompt):

```bash
# Aggiorna pip
pip install --upgrade pip

# Installa tutte le dipendenze del progetto
pip install -r requirements.txt
```

**Tempo stimato:** 2-5 minuti (dipende dalla connessione internet)

**Output atteso:**
```
Successfully installed fastapi-0.104.1 uvicorn-0.24.0 sqlalchemy-2.0.23 ...
```

### Se ricevi errori durante l'installazione

**Errore compilazione pacchetti:**
```bash
# Su Linux/Mac, installa build tools
sudo apt-get install python3-dev build-essential  # Ubuntu/Debian
# oppure
brew install python3  # Mac con Homebrew

# Su Windows, installa Visual C++ Build Tools
# Scarica da: https://visualstudio.microsoft.com/visual-cpp-build-tools/
```

**Errore permessi:**
```bash
pip install -r requirements.txt --user
```

---

## ⚙️ PASSO 4: CONFIGURAZIONE (OPZIONALE)

Il sistema funziona con configurazione di default, ma puoi personalizzare:

### Crea file `.env` (opzionale)

```bash
# Copia il template
cp .env.example .env

# Modifica con il tuo editor preferito
nano .env
# oppure
code .env  # Se usi VS Code
```

**Configurazioni principali in `.env`:**

```bash
# Database (SQLite di default - va bene per sviluppo)
DATABASE_URL=sqlite:///./database.db

# JWT Secret (per sicurezza cambialo in produzione)
SECRET_KEY=your-secret-key-change-in-production

# Directories
OUTPUT_DIR=./output
UPLOAD_DIR=./uploads
TEMP_DIR=./temp

# FFmpeg (se installato)
FFMPEG_PATH=/usr/bin/ffmpeg

# Server
API_PREFIX=/api/v1
DEBUG=true
```

**Per ora lascia tutto di default!** Il sistema funziona senza modifiche.

---

## 🗄️ PASSO 5: INIZIALIZZA DATABASE

Il database SQLite verrà creato automaticamente al primo avvio.

Puoi verificare/creare manualmente:

```bash
# Crea il database con le tabelle
python -c "
from app.core.database import engine, Base
from app.models import user, job, pipeline
Base.metadata.create_all(bind=engine)
print('✅ Database creato con successo!')
"
```

**Output atteso:**
```
✅ Database creato con successo!
```

Vedrai il file `database.db` nella root del progetto.

---

## 🚀 PASSO 6: AVVIA IL SERVER

**Finalmente! Avvia il sistema:**

```bash
# Assicurati di essere nella root del progetto
cd AIVideoMaker

# Con virtual environment attivo
python main.py
```

**Output atteso:**

```
INFO:     Will watch for changes in these directories: ['/path/to/AIVideoMaker']
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [12345] using WatchFiles
INFO:     Started server process [12346]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

**Il server è pronto!** ✅

---

## 🌐 PASSO 7: APRI L'INTERFACCIA WEB

### 7.1 Swagger UI (Interfaccia Test API)

Apri il browser e vai a:

```
http://localhost:8000/docs
```

Vedrai l'interfaccia interattiva con tutte le API! 🎉

### 7.2 Documentazione Alternativa (ReDoc)

```
http://localhost:8000/redoc
```

Documentazione in stile libro più leggibile.

### 7.3 Health Check

```
http://localhost:8000/
```

Dovresti vedere:
```json
{
  "message": "AIVideoMaker API",
  "version": "1.0.0",
  "status": "running"
}
```

---

## 🧪 PASSO 8: TESTA IL SISTEMA

### Test 1: Verifica API Disponibili

In Swagger (`http://localhost:8000/docs`) vedrai 9 sezioni:

- **Authentication** - Login e registrazione
- **Chromakey** - Rimozione green screen
- **Translation** - Traduzione video
- **Thumbnail** - Generazione thumbnail
- **YouTube** - Upload YouTube
- **Logo Overlay** - Overlay logo su video
- **Transcription** - Trascrizione audio
- **SEO Metadata AI** - Generazione SEO
- **Metadata** - Estrazione metadata
- **Pipeline** - Workflow automatici

### Test 2: Registra Utente

1. Espandi `POST /api/v1/auth/register`
2. Clicca "Try it out"
3. Inserisci:
```json
{
  "username": "ettore",
  "password": "test1234"
}
```
4. Clicca "Execute"
5. Dovresti vedere **201 Created**

### Test 3: Fai Login

1. Clicca il pulsante **"Authorize"** in alto a destra (icona lucchetto)
2. Inserisci:
   - username: `ettore`
   - password: `test1234`
3. Clicca "Authorize"
4. Clicca "Close"

**Ora sei autenticato!** Tutte le API useranno il tuo token JWT automaticamente.

### Test 4: Test API Semplice (Metadata)

1. Espandi `POST /api/v1/metadata/extract`
2. Clicca "Try it out"
3. Inserisci:
```json
{
  "video_path": "/path/to/any/video.mp4",
  "include_streams": true,
  "include_format": true,
  "include_chapters": false
}
```
4. Execute

**Se non hai video:** Salta questo test, passiamo a quelli con upload.

---

## 📁 PASSO 9: PREPARA FILE DI TEST

Per testare le API che richiedono file, prepara:

### Crea file di test minimali

```bash
# Crea cartella test
mkdir -p test_files

# Scarica/copia video di test
# Usa un qualsiasi video MP4 che hai sul PC
cp /path/to/tuo/video.mp4 test_files/video_test.mp4

# Scarica/copia logo PNG
# Usa un qualsiasi logo/immagine PNG che hai
cp /path/to/tuo/logo.png test_files/logo_test.png
```

**Oppure scarica da internet:**

- Video di test: https://sample-videos.com/
- Logo di test: Qualsiasi immagine PNG

---

## 🧪 PASSO 10: TEST COMPLETO - Logo Overlay

**Test end-to-end di una funzionalità completa:**

### 10.1 Upload e Processa

In Swagger:

1. Espandi `POST /api/v1/logo/upload` (sezione "Logo Overlay")
2. Clicca "Try it out"
3. Carica file:
   - **video_file**: Scegli `test_files/video_test.mp4`
   - **logo_file**: Scegli `test_files/logo_test.png`
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

**Response:**
```json
{
  "job_id": "abc-123-def-456",
  "status": "processing",
  "message": "Job avviato in background"
}
```

### 10.2 Monitora Progresso

1. Copia il `job_id` dalla response
2. Espandi `GET /api/v1/logo/jobs/{job_id}`
3. Incolla il `job_id`
4. Clicca "Execute"
5. **Ripeti ogni 5-10 secondi** finché `status` diventa `"completed"`

**Durante processing:**
```json
{
  "job_id": "abc-123-def-456",
  "status": "processing",
  "progress": 50,
  "message": "Applicazione logo overlay..."
}
```

**Completato:**
```json
{
  "job_id": "abc-123-def-456",
  "status": "completed",
  "progress": 100,
  "message": "Logo overlay completato",
  "result": {
    "output_path": "./output/logo_overlay_1234567890.mp4",
    "duration_seconds": 15.5,
    "success": true
  }
}
```

### 10.3 Scarica Output

Il file processato è in:
```
./output/logo_overlay_1234567890.mp4
```

Aprilo e verifica che il logo sia stato applicato! 🎉

---

## 🔄 PASSO 11: TEST PIPELINE (AVANZATO)

**Testa il workflow automatico multi-step:**

### 11.1 Crea Pipeline

1. Espandi `POST /api/v1/pipeline/create`
2. Clicca "Try it out"
3. Inserisci:

```json
{
  "name": "Test Pipeline",
  "description": "Pipeline di test con 2 step",
  "stop_on_error": true,
  "input_files": {
    "video": "./test_files/video_test.mp4",
    "logo": "./test_files/logo_test.png"
  },
  "steps": [
    {
      "step_number": 1,
      "job_type": "logo_overlay",
      "enabled": true,
      "parameters": {
        "video_path": "@input",
        "logo_path": "@input",
        "position": "top-left",
        "logo_scale": 0.2,
        "opacity": 0.8
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
    }
  ]
}
```

4. Execute

**Response:**
```json
{
  "pipeline_id": "xyz-789",
  "status": "created",
  "total_steps": 2,
  "enabled_steps": 2
}
```

### 11.2 Esegui Pipeline

1. Copia `pipeline_id`
2. Espandi `POST /api/v1/pipeline/{pipeline_id}/execute`
3. Incolla `pipeline_id`
4. Execute

**Response:**
```json
{
  "message": "Pipeline avviata in background",
  "pipeline_id": "xyz-789"
}
```

### 11.3 Monitora Esecuzione

1. Espandi `GET /api/v1/pipeline/{pipeline_id}`
2. Incolla `pipeline_id`
3. Execute
4. Ripeti ogni 5 secondi

**Progresso:**
```json
{
  "status": "running",
  "current_step": 1,
  "total_steps": 2,
  "message": "Esecuzione logo_overlay..."
}
```

**Completato:**
```json
{
  "status": "completed",
  "current_step": 2,
  "total_steps": 2,
  "message": "Pipeline completata con successo!",
  "result": {
    "logo_overlay": {
      "success": true,
      "output_path": "./output/logo_overlay_xxx.mp4"
    },
    "metadata_extraction": {
      "success": true,
      "metadata": { /* metadata completi */ }
    }
  }
}
```

**✅ Pipeline funziona!**

---

## 🛠️ DIPENDENZE OPZIONALI

Il sistema funziona anche senza, ma per funzionalità complete:

### FFmpeg (per operazioni video avanzate)

**Su Linux (Ubuntu/Debian):**
```bash
sudo apt-get update
sudo apt-get install -y ffmpeg
```

**Su Mac:**
```bash
brew install ffmpeg
```

**Su Windows:**
1. Scarica da: https://ffmpeg.org/download.html
2. Estrai in `C:\ffmpeg`
3. Aggiungi `C:\ffmpeg\bin` al PATH

**Verifica:**
```bash
ffmpeg -version
```

### Whisper (per trascrizione audio)

**ATTENZIONE:** Whisper richiede 1-10GB di spazio e GPU consigliata.

```bash
pip install openai-whisper
```

**Verifica:**
```bash
python -c "import whisper; print('Whisper OK')"
```

**Se non installi Whisper:**
- Le API `transcription` e `seo` funzionano ma ritornano errore chiaro
- Tutti gli altri servizi funzionano normalmente

---

## 🐛 TROUBLESHOOTING

### Problema: Server non si avvia

**Errore: `Address already in use`**
```bash
# Porta 8000 già occupata, usa un'altra porta
uvicorn main:app --host 0.0.0.0 --port 8001
```

**Errore: `Module not found`**
```bash
# Verifica di aver attivato il virtual environment
source venv/bin/activate  # Linux/Mac
.\venv\Scripts\Activate.ps1  # Windows

# Reinstalla dipendenze
pip install -r requirements.txt
```

**Errore: `No module named app`**
```bash
# Assicurati di essere nella root del progetto
cd AIVideoMaker
python main.py
```

### Problema: API risponde 401 Unauthorized

- Verifica di aver fatto login
- Clicca "Authorize" in Swagger e inserisci credenziali
- Il token JWT scade dopo 30 giorni

### Problema: Job rimane "processing"

**Controlla i logs del server:**

Il terminale dove hai lanciato `python main.py` mostra i logs.

**Errori comuni:**
- File input non esiste → Controlla path
- FFmpeg non installato → Installa FFmpeg
- Permessi negati → Controlla permessi cartelle

### Problema: Import Error durante startup

```bash
# Reinstalla tutte le dipendenze
pip install --force-reinstall -r requirements.txt

# Oppure ricrea virtual environment
deactivate
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Problema: Database locked

```bash
# Ferma il server (CTRL+C)
# Rimuovi il database
rm database.db
# Riavvia
python main.py
```

Il database verrà ricreato automaticamente.

---

## 📂 STRUTTURA PROGETTO

Dopo il setup dovresti avere:

```
AIVideoMaker/
├── venv/                   # Virtual environment (creato da te)
├── app/                    # Codice applicazione
│   ├── api/                # API routes
│   ├── core/               # Config, database
│   ├── models/             # Database models
│   ├── services/           # Business logic
│   └── pipelines/          # Orchestrator
├── output/                 # File generati (creato automaticamente)
├── uploads/                # File uploadati (creato automaticamente)
├── temp/                   # File temporanei (creato automaticamente)
├── backup/                 # Backup file modificati
├── test_files/             # File di test (creato da te)
├── database.db             # Database SQLite (creato automaticamente)
├── main.py                 # Entry point
├── requirements.txt        # Dipendenze Python
├── .env                    # Configurazione (opzionale)
├── GUIDA_TEST.md           # Guida test
├── RISOLUZIONE_COMPLETA.md # Report tecnico
└── SETUP_TUO_PC.md         # Questa guida
```

---

## ✅ CHECKLIST SETUP COMPLETO

Verifica di aver completato tutti gli step:

- [ ] Python 3.9+ installato
- [ ] Repository clonato
- [ ] Branch `claude/project-review-improvements-011CUpkeELM78WpjRDQLfS6q` attivo
- [ ] Virtual environment creato e attivato
- [ ] Dipendenze installate (`pip install -r requirements.txt`)
- [ ] Database creato (automatico al primo avvio)
- [ ] Server avviato (`python main.py`)
- [ ] Swagger UI accessibile (http://localhost:8000/docs)
- [ ] Utente registrato
- [ ] Login effettuato (Authorize in Swagger)
- [ ] Almeno 1 API testata con successo
- [ ] File di output generati in `./output/`

**Se tutto ✅ → Sistema completamente funzionante sul tuo PC!** 🎉

---

## 🚀 COMANDI RAPIDI RIASSUNTO

```bash
# 1. Clona e entra nel progetto
git clone https://github.com/nestor71/AIVideoMaker.git
cd AIVideoMaker
git checkout claude/project-review-improvements-011CUpkeELM78WpjRDQLfS6q

# 2. Setup ambiente
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# .\venv\Scripts\Activate.ps1  # Windows

# 3. Installa dipendenze
pip install --upgrade pip
pip install -r requirements.txt

# 4. Avvia server
python main.py

# 5. Apri browser
# http://localhost:8000/docs
```

---

## 📞 SUPPORTO

**Se hai problemi:**

1. **Controlla i logs** nel terminale dove hai lanciato il server
2. **Leggi il messaggio di errore** completo
3. **Cerca in TROUBLESHOOTING** sopra
4. **Controlla GUIDA_TEST.md** per esempi dettagliati

**File utili:**
- `GUIDA_TEST.md` - Guida testing completa
- `RISOLUZIONE_COMPLETA.md` - Report tecnico del sistema

---

## 🎯 PROSSIMI PASSI

Una volta che il sistema funziona sul tuo PC:

1. **Testa tutte le API** usando Swagger UI
2. **Crea pipeline personalizzate** combinando i servizi
3. **Integra con il tuo frontend** (se ne hai uno)
4. **Installa FFmpeg e Whisper** per funzionalità complete

---

**Guida creata da:** Claude Code
**Data:** 2025-11-08
**Versione sistema:** 8/9 servizi attivi (88.9%)
**Branch:** `claude/project-review-improvements-011CUpkeELM78WpjRDQLfS6q`

**Buon testing, Ettore!** 🚀
