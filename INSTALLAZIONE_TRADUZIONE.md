# 🚀 Guida Rapida: Installazione e Avvio Traduzione Video

## 📋 Prerequisiti

Prima di iniziare, assicurati di avere:
- Python 3.8+ installato
- FFmpeg installato nel sistema
- Connessione internet attiva

---

## ⚙️ Installazione Passo-Passo

### 1. Attiva l'ambiente virtuale

```bash
cd /Users/nestor/Desktop/Progetti\ Claude-Code/cartella\ senza\ nome/AIVideoMaker1

# Attiva venv
source venv/bin/activate
```

### 2. Installa le nuove dipendenze

```bash
# Installa tutte le dipendenze (incluse quelle per traduzione)
pip install -r requirements.txt
```

**Dipendenze installate:**
- `googletrans==4.0.0-rc1` - Traduzione testo con Google Translate
- `gTTS==2.5.3` - Sintesi vocale (Text-to-Speech)
- `openai-whisper` - Trascrizione audio (già presente)

### 3. Verifica installazione

Esegui lo script di test:

```bash
python test_translation.py
```

**Output atteso:**
```
✅ TUTTI I TEST SUPERATI!
```

Se vedi errori, installa le dipendenze mancanti manualmente:

```bash
# Se manca googletrans
pip install googletrans==4.0.0-rc1

# Se manca gTTS
pip install gTTS

# Se manca Whisper
pip install openai-whisper
```

### 4. Verifica FFmpeg

```bash
ffmpeg -version
```

**Se FFmpeg non è installato:**

**macOS:**
```bash
brew install ffmpeg
```

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install ffmpeg
```

**Windows:**
- Scarica da https://ffmpeg.org/download.html
- Aggiungi la cartella `bin` al PATH di sistema

---

## 🎬 Avvio dell'Applicazione

### 1. Avvia il server FastAPI

```bash
python app.py
```

**Output atteso:**
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete.
```

### 2. Apri il browser

Vai su: **http://localhost:8000**

### 3. Accedi alla tab "Traduzione Audio"

1. Clicca sulla tab **"Traduzione Audio"** nella barra di navigazione
2. L'interfaccia mostrerà:
   - Selettore video
   - Menu lingue disponibili (11 lingue)
   - Checkbox lip-sync (opzionale, sconsigliato)
   - Pulsante "Avvia Traduzione"

---

## 🧪 Test Rapido

### Scenario di Test: Traduci un video breve

1. **Carica un video di test (1-2 minuti)**
   - Vai alla tab "Caricamento Video"
   - Carica un video con audio chiaro

2. **Vai alla tab "Traduzione Audio"**
   - Seleziona il video appena caricato
   - Scegli lingua: **Inglese (en)**
   - **NON** abilitare lip-sync (troppo lento)

3. **Avvia traduzione**
   - Clicca "Avvia Traduzione"
   - Attendi 2-5 minuti (barra progresso mostra stato)

4. **Verifica risultato**
   - Video tradotto appare in anteprima
   - Clicca "Scarica Video Tradotto"
   - Riproduci il video: audio dovrebbe essere in inglese

---

## 🔍 Verifica Funzionamento

### Test Endpoint API

Puoi testare gli endpoint direttamente:

**1. Lista lingue supportate:**
```bash
curl http://localhost:8000/api/translation/languages
```

**Output atteso:**
```json
{
  "success": true,
  "languages": {
    "en": "Inglese",
    "es": "Spagnolo",
    "fr": "Francese",
    ...
  }
}
```

**2. Carica video per traduzione:**
```bash
# Carica un video nella cartella uploads/
# Poi avvia traduzione tramite UI
```

---

## ⚠️ Problemi Comuni

### Errore: "No module named 'googletrans'"

**Soluzione:**
```bash
pip install googletrans==4.0.0-rc1
```

### Errore: "No module named 'gtts'"

**Soluzione:**
```bash
pip install gTTS
```

### Errore: "ffmpeg not found"

**Soluzione:**
```bash
# macOS
brew install ffmpeg

# Ubuntu/Debian
sudo apt-get install ffmpeg
```

### Traduzione molto lenta

**Cause:**
- Video troppo lungo
- CPU lenta
- Whisper sta scaricando il modello (prima volta)

**Soluzioni:**
- Usa video più brevi per test (1-2 minuti)
- Attendi il primo download del modello Whisper (~150MB)
- Chiudi altre applicazioni pesanti

### Errore: "Whisper non installato"

**Soluzione:**
```bash
pip install openai-whisper
```

---

## 📊 Struttura File Implementata

```
AIVideoMaker1/
├── app.py                          # ✅ Aggiornato con endpoint traduzione
├── video_translator.py             # ✅ NUOVO - Modulo traduzione
├── templates/
│   └── index_new.html             # ✅ Aggiornato con tab traduzione
├── requirements.txt                # ✅ Aggiornato con dipendenze
├── backup/                         # ✅ NUOVO - Backup file originali
│   ├── app.py.bak
│   ├── index_new.html.bak
│   └── requirements.txt.bak
├── test_translation.py             # ✅ NUOVO - Script test
├── TRADUZIONE_VIDEO_README.md      # ✅ NUOVO - Documentazione completa
└── INSTALLAZIONE_TRADUZIONE.md     # ✅ NUOVO - Guida installazione
```

---

## ✅ Checklist Finale

Prima di usare la traduzione, verifica:

- [ ] Ambiente virtuale attivato
- [ ] Dipendenze installate (`pip list | grep -E "googletrans|gTTS|whisper"`)
- [ ] FFmpeg funzionante (`ffmpeg -version`)
- [ ] Server avviato (`python app.py`)
- [ ] Browser aperto su http://localhost:8000
- [ ] Tab "Traduzione Audio" visibile
- [ ] Lingue caricate nel menu a tendina
- [ ] Video disponibili nel selettore

---

## 🎯 Prossimi Passi

1. **Test con video reale**: Carica un video di 1-2 minuti e traducilo
2. **Prova lingue diverse**: Testa traduzione in Inglese, Spagnolo, Francese
3. **Documenta tempi**: Annota quanto tempo impiega per video di diverse lunghezze
4. **Migliora qualità**: Considera API premium (DeepL, ElevenLabs) per qualità superiore

---

## 📞 Supporto

Se riscontri problemi:

1. **Controlla i log**: `tail -f app.log`
2. **Verifica dipendenze**: `pip list`
3. **Testa FFmpeg**: `ffmpeg -version`
4. **Esegui test**: `python test_translation.py`
5. **Leggi documentazione completa**: `TRADUZIONE_VIDEO_README.md`

---

## 🎉 Conclusione

Se hai seguito tutti i passaggi, dovresti ora avere:

✅ Funzionalità traduzione video completamente integrata
✅ 11 lingue supportate
✅ UI completa con progress tracking
✅ Backend robusto con gestione errori
✅ Documentazione completa

**Buona traduzione! 🌍🎬**
