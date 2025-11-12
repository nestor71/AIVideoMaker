# 🚀 Launcher macOS per AIVideoMaker

Questo documento spiega come utilizzare i launcher per macOS che avviano automaticamente l'applicazione AIVideoMaker.

## 📦 Cosa contiene

Sono stati creati **due metodi** per avviare facilmente l'applicazione su macOS:

### 1. Script `.command` (Metodo Semplice)
**File**: `Avvia_AIVideoMaker.command`

- ✅ Doppio clic per avviare
- ✅ Non richiede installazione
- ✅ Mostra output dettagliato nel terminale

### 2. App Bundle (Metodo Professionale)
**File**: `AIVideoMaker.app`

- ✅ Icona nel Finder come app nativa
- ✅ Può essere spostata nella cartella Applicazioni
- ✅ Avvio rapido dal Launchpad
- ✅ Esperienza utente più pulita

---

## 🎯 Come Usare

### Metodo 1: Script `.command`

1. **Trova il file** `Avvia_AIVideoMaker.command` nella cartella del progetto
2. **Doppio clic** sul file
3. Se macOS blocca l'esecuzione:
   - Tasto destro sul file → **"Apri"**
   - Conferma "Apri" nel popup di sicurezza
   - (Questo va fatto solo la prima volta)
4. Il terminale si aprirà automaticamente e:
   - ✅ Attiverà il virtual environment
   - ✅ Installerà le dipendenze (solo alla prima esecuzione)
   - ✅ Avvierà il server FastAPI
   - ✅ Aprirà il browser su `http://localhost:8000`

### Metodo 2: App Bundle

1. **Trova** `AIVideoMaker.app` nella cartella del progetto
2. **(Opzionale)** Trascina l'app nella cartella **Applicazioni**
3. **Doppio clic** sull'app
4. Se macOS blocca l'esecuzione:
   - Vai in **Preferenze di Sistema** → **Sicurezza e Privacy**
   - Clicca **"Apri comunque"**
   - (Questo va fatto solo la prima volta)
5. L'app aprirà il terminale e avvierà tutto automaticamente

---

## 🔧 Cosa fa automaticamente lo script

### 1️⃣ Controllo Virtual Environment
- Verifica se esiste `venv/`
- Se non esiste, lo crea automaticamente
- Attiva il virtual environment

### 2️⃣ Installazione Dipendenze
- Alla prima esecuzione installa tutte le dipendenze da `requirements.txt`
- Crea un marker file per evitare reinstallazioni inutili
- Aggiorna pip automaticamente

### 3️⃣ Configurazione `.env`
- Controlla se esiste il file `.env`
- Se non esiste, lo crea da `.env.example`
- Avvisa l'utente di configurare le chiavi API

### 4️⃣ Gestione Porta
- Controlla se la porta 8000 è già in uso
- Chiede se terminare il processo esistente
- Riavvia pulito se necessario

### 5️⃣ Avvio Server
- Avvia `python main.py` in background
- Monitora che il server sia pronto
- Attende fino a 30 secondi per il health check

### 6️⃣ Apertura Browser
- Apre automaticamente Safari (o browser predefinito)
- Naviga su `http://localhost:8000`
- L'applicazione è pronta all'uso!

---

## 📋 Requisiti

### Software Richiesto
- **macOS** 10.13 (High Sierra) o superiore
- **Python 3.8+** installato
  ```bash
  # Controlla versione Python
  python3 --version

  # Se non hai Python 3, installalo con Homebrew:
  brew install python3
  ```

### Dipendenze Sistema
Alcune funzionalità richiedono librerie di sistema:

```bash
# Homebrew (se non installato)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# FFmpeg (per processamento video)
brew install ffmpeg

# PostgreSQL (database - opzionale)
brew install postgresql@14
```

---

## 🐛 Risoluzione Problemi

### Problema: "Impossibile aprire perché proviene da uno sviluppatore non identificato"

**Soluzione**:
1. Tasto destro sul file → **"Apri"**
2. Clicca **"Apri"** nel popup
3. Oppure:
   ```bash
   # Rimuovi quarantena macOS
   xattr -d com.apple.quarantine Avvia_AIVideoMaker.command
   xattr -d com.apple.quarantine AIVideoMaker.app
   ```

### Problema: "command not found: python3"

**Soluzione**:
```bash
# Installa Python 3 con Homebrew
brew install python3

# Verifica installazione
which python3
python3 --version
```

### Problema: "Porta 8000 già in uso"

**Soluzione**:
1. Lo script chiede automaticamente se terminare il processo
2. Oppure manualmente:
   ```bash
   # Trova processo sulla porta 8000
   lsof -ti:8000

   # Termina il processo
   kill -9 $(lsof -ti:8000)
   ```

### Problema: Dipendenze non si installano

**Soluzione**:
```bash
# Entra nella directory del progetto
cd /path/to/AIVideoMaker

# Attiva venv manualmente
source venv/bin/activate

# Aggiorna pip
pip install --upgrade pip

# Installa dipendenze
pip install -r requirements.txt

# Controlla errori specifici
```

### Problema: Il server non parte

**Soluzione**:
```bash
# Controlla i log
tail -f /tmp/aividemaker.log

# Verifica configurazione
cat .env

# Prova avvio manuale
source venv/bin/activate
python main.py
```

---

## 🎨 Personalizzazione

### Cambiare Porta Server

Modifica il file `.env`:
```bash
# Aggiungi questa riga
API_PORT=8080
```

Poi modifica lo script `Avvia_AIVideoMaker.command`:
```bash
# Cerca tutte le occorrenze di "8000" e sostituisci con "8080"
```

### Aggiungere Icona Personalizzata

Per l'app bundle `AIVideoMaker.app`:

1. Crea un file icona `.icns`
2. Copialo in `AIVideoMaker.app/Contents/Resources/AppIcon.icns`
3. Aggiorna `Info.plist`:
   ```xml
   <key>CFBundleIconFile</key>
   <string>AppIcon</string>
   ```

---

## 📱 Arresto Applicazione

### Da Terminale
- Premi **CTRL+C** nel terminale aperto dallo script

### Da Riga di Comando
```bash
# Metodo 1: Uccidi tutti i processi Python
killall python

# Metodo 2: Uccidi processo su porta 8000
kill -9 $(lsof -ti:8000)

# Metodo 3: Trova PID specifico
ps aux | grep "main.py"
kill -9 <PID>
```

---

## 📊 Log e Debugging

### Visualizza Log in Tempo Reale
```bash
tail -f /tmp/aividemaker.log
```

### Salva Log Completo
```bash
cat /tmp/aividemaker.log > ~/Desktop/aividemaker_debug.log
```

### Debug Manuale
```bash
cd /path/to/AIVideoMaker
source venv/bin/activate
python main.py
# Il server mostrerà tutti i log nel terminale
```

---

## ✅ Checklist Post-Installazione

- [ ] Python 3.8+ installato
- [ ] FFmpeg installato (`brew install ffmpeg`)
- [ ] File `.env` configurato con le chiavi API
- [ ] Virtual environment creato (`venv/` presente)
- [ ] Dipendenze installate
- [ ] Porta 8000 libera
- [ ] Browser si apre automaticamente
- [ ] Applicazione accessibile su http://localhost:8000

---

## 🔗 Link Utili

- **Applicazione Web**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs (solo in dev mode)
- **Health Check**: http://localhost:8000/health
- **Admin Dashboard**: http://localhost:8000/admin

---

## 🆘 Supporto

Se riscontri problemi:

1. Controlla i **log**: `tail -f /tmp/aividemaker.log`
2. Verifica **requisiti**: Python 3.8+, FFmpeg, PostgreSQL
3. Controlla **file .env**: Chiavi API configurate correttamente
4. Prova **avvio manuale**: Segui sezione "Debug Manuale"

---

## 📝 Note

- Il server continua a girare **in background** anche dopo aver chiuso il browser
- Per fermarlo completamente, chiudi il terminale o premi **CTRL+C**
- Lo script controlla automaticamente gli aggiornamenti delle dipendenze
- I log sono salvati in `/tmp/aividemaker.log`

---

**Creato per AIVideoMaker Professional v2.0**
_Avvio semplice e automatizzato su macOS_ 🚀
