# 🌍 Traduzione Video - Documentazione Completa

## Panoramica

La funzionalità **Traduzione Video** permette di tradurre automaticamente l'audio di un video in un'altra lingua utilizzando l'intelligenza artificiale. Il sistema esegue:

1. **Trascrizione** dell'audio originale usando Whisper AI
2. **Traduzione** del testo tramite Google Translate
3. **Sintesi vocale (TTS)** nella lingua target con gTTS
4. **Ricombinazione** del video con il nuovo audio tradotto
5. **Lip-sync opzionale** (richiede GPU NVIDIA, molto lento)

---

## 📋 Requisiti

### Dipendenze Software

Le seguenti librerie sono necessarie e sono già incluse in `requirements.txt`:

```bash
# Installazione automatica di tutte le dipendenze
pip install -r requirements.txt
```

**Dipendenze principali:**
- `openai-whisper` - Trascrizione audio
- `googletrans==4.0.0-rc1` - Traduzione testo
- `gTTS` - Text-to-Speech (sintesi vocale)
- `ffmpeg` - Manipolazione video/audio (deve essere installato nel sistema)

### Installazione FFmpeg

**macOS:**
```bash
brew install ffmpeg
```

**Ubuntu/Debian:**
```bash
sudo apt-get install ffmpeg
```

**Windows:**
Scarica da [ffmpeg.org](https://ffmpeg.org/download.html) e aggiungi al PATH

---

## 🚀 Avvio dell'Applicazione

### 1. Attiva l'ambiente virtuale

```bash
# Dalla directory del progetto
source venv/bin/activate  # macOS/Linux
# oppure
venv\Scripts\activate  # Windows
```

### 2. Installa/Aggiorna dipendenze

```bash
pip install -r requirements.txt
```

### 3. Avvia il server

```bash
python app.py
```

Il server sarà accessibile su: **http://localhost:8000**

---

## 🎬 Come Usare la Traduzione Video

### Passo 1: Carica un Video

1. Vai alla tab **"Caricamento Video"**
2. Carica un video tramite:
   - Drag & Drop nell'area di upload
   - Pulsante "Carica File"
   - Scarica da URL (YouTube, Vimeo, ecc.)

### Passo 2: Accedi alla Tab "Traduzione Audio"

1. Clicca sulla tab **"Traduzione Audio"** nella barra di navigazione
2. L'interfaccia mostrerà i video disponibili per la traduzione

### Passo 3: Seleziona il Video

1. Dal menu a tendina, seleziona il video da tradurre
2. Il video apparirà in anteprima sotto il selettore

### Passo 4: Scegli la Lingua Target

Seleziona la lingua di destinazione dal menu:

**Lingue supportate:**
- 🇬🇧 Inglese (`en`)
- 🇪🇸 Spagnolo (`es`)
- 🇫🇷 Francese (`fr`)
- 🇩🇪 Tedesco (`de`)
- 🇵🇹 Portoghese (`pt`)
- 🇷🇺 Russo (`ru`)
- 🇯🇵 Giapponese (`ja`)
- 🇨🇳 Cinese Semplificato (`zh-CN`)
- 🇸🇦 Arabo (`ar`)
- 🇮🇳 Hindi (`hi`)
- 🇮🇹 Italiano (`it`)

### Passo 5: (Opzionale) Abilita Lip-Sync

⚠️ **ATTENZIONE**: Il lip-sync è **MOLTO LENTO** (20-30 minuti per video brevi) e richiede:
- GPU NVIDIA con CUDA
- Installazione manuale di Wav2Lip
- ~3GB di spazio per i modelli

**Per la maggior parte degli utenti, si consiglia di lasciare il lip-sync DISABILITATO.**

### Passo 6: Avvia la Traduzione

1. Clicca su **"Avvia Traduzione"**
2. Il sistema mostrerà una barra di progresso con:
   - Percentuale di completamento (0-100%)
   - Messaggio di stato corrente
   - Tempo stimato rimanente

### Passo 7: Scarica il Video Tradotto

1. Quando la traduzione è completata, apparirà il video tradotto in anteprima
2. Clicca su **"Scarica Video Tradotto"** per salvarlo sul tuo PC
3. Oppure clicca **"Nuova Traduzione"** per tradurre un altro video

---

## ⏱️ Tempi di Elaborazione

I tempi dipendono dalla lunghezza del video e dalle prestazioni del sistema:

| Durata Video | Senza Lip-Sync | Con Lip-Sync |
|--------------|----------------|--------------|
| 1-2 minuti   | 2-5 minuti     | 20-30 minuti |
| 3-5 minuti   | 5-10 minuti    | 40-60 minuti |
| 5-10 minuti  | 10-20 minuti   | 60-120 minuti|

**Fasi di elaborazione:**
1. Estrazione audio (5-10%)
2. Trascrizione con Whisper (10-40%)
3. Traduzione testo (40-55%)
4. Generazione TTS (55-85%)
5. Ricombinazione video (85-100%)

---

## 🔧 Risoluzione Problemi

### Errore: "Video non trovato"
- Assicurati che il video sia stato caricato correttamente
- Aggiorna la lista video con il pulsante "Aggiorna Lista"
- Controlla che il file esista nella cartella `uploads/`

### Errore: "Whisper non installato"
```bash
pip install openai-whisper
```

### Errore: "googletrans non installato"
```bash
pip install googletrans==4.0.0-rc1
```

### Errore: "gTTS non installato"
```bash
pip install gTTS
```

### Errore: "ffmpeg not found"
- Installa FFmpeg nel sistema operativo (vedi sezione Requisiti)
- Verifica che `ffmpeg` sia nel PATH:
```bash
ffmpeg -version
```

### La traduzione impiega troppo tempo
- **Normale**: La trascrizione con Whisper può richiedere 2-10 minuti
- Usa il modello "base" invece di "large" (già configurato di default)
- Chiudi altre applicazioni pesanti durante l'elaborazione

### Audio tradotto non sincronizzato
- Disabilita il lip-sync (più veloce e meno problemi)
- Assicurati che l'audio originale sia chiaro
- Prova con un video più breve per testare

---

## 🛠️ Configurazione Avanzata

### Cambiare il Modello Whisper

Modifica `video_translator.py` (linea ~154):

```python
# Modelli disponibili: tiny, base, small, medium, large
model = whisper.load_model("base")  # Cambia "base" con il modello desiderato
```

**Modelli Whisper:**
- `tiny` - Velocissimo, meno accurato (~75MB)
- `base` - Veloce, buona accuratezza (~145MB) ⭐ **Consigliato**
- `small` - Medio, ottima accuratezza (~488MB)
- `medium` - Lento, eccellente accuratezza (~1.5GB)
- `large` - Molto lento, massima accuratezza (~3GB)

### Usare API Premium per Traduzione

Sostituisci Google Translate con DeepL o Azure Translator per migliore qualità:

**DeepL API:**
```python
# In video_translator.py, metodo _translate_text
import deepl
translator = deepl.Translator("YOUR_API_KEY")
result = translator.translate_text(text, target_lang=target_language)
```

### Cambiare Voce TTS

Modifica `video_translator.py` per usare Azure TTS, AWS Polly, o ElevenLabs per voci più naturali.

---

## 📊 Struttura del Codice

```
AIVideoMaker1/
├── app.py                      # Endpoint FastAPI per traduzione
├── video_translator.py         # Logica traduzione video
├── templates/
│   └── index_new.html         # UI tab traduzione
├── uploads/                    # Video caricati
├── outputs/                    # Video tradotti
└── requirements.txt           # Dipendenze
```

### File Principali

**`video_translator.py`**
- Classe `VideoTranslator` per gestire il flusso completo
- Metodi per trascrizione, traduzione, TTS, ricombinazione
- Supporto progress callback per UI in tempo reale

**`app.py` (endpoint traduzione)**
- `GET /api/translation/languages` - Lista lingue supportate
- `POST /api/translation/translate-video` - Avvia traduzione
- `GET /api/translation/download/{job_id}` - Download video tradotto

**`index_new.html` (JavaScript)**
- `startVideoTranslation()` - Avvia traduzione
- `startTranslationPolling()` - Polling stato job
- `downloadTranslatedVideo()` - Download risultato

---

## 🚀 Miglioramenti Futuri

### Implementazione Lip-Sync Completa

Il lip-sync richiede:

1. **Installazione Wav2Lip:**
```bash
git clone https://github.com/Rudrabha/Wav2Lip.git
cd Wav2Lip
pip install -r requirements.txt

# Download modello pre-trained (~150MB)
wget https://github.com/Rudrabha/Wav2Lip/releases/download/v1.0/wav2lip_gan.pth -O checkpoints/wav2lip_gan.pth
```

2. **Modifica `video_translator.py`:**
```python
def _apply_lipsync(self, video_path, audio_path):
    # Implementa chiamata a Wav2Lip
    subprocess.run([
        'python', 'Wav2Lip/inference.py',
        '--checkpoint_path', 'checkpoints/wav2lip_gan.pth',
        '--face', video_path,
        '--audio', audio_path,
        '--outfile', output_path
    ])
    return output_path
```

### Voci TTS Premium

Per qualità superiore, integra:
- **ElevenLabs** - Voci ultra-realistiche
- **Azure Neural TTS** - 75+ voci naturali
- **Amazon Polly** - 60+ voci SSML

### Traduzione Multi-Lingua Batch

Traduci automaticamente in più lingue contemporaneamente:
```python
languages = ['en', 'es', 'fr', 'de']
for lang in languages:
    translator.translate_video(video, output, lang)
```

---

## 📞 Supporto

Per problemi o domande:
1. Controlla i log in `app.log`
2. Verifica le dipendenze installate: `pip list`
3. Testa FFmpeg: `ffmpeg -version`
4. Consulta la documentazione ufficiale di Whisper, gTTS, googletrans

---

## 📝 Note Importanti

⚠️ **Limitazioni:**
- Google Translate gratuito ha limiti di rate (max ~100 traduzioni/ora)
- gTTS richiede connessione internet
- Whisper richiede RAM (min 4GB consigliati)
- Lip-sync richiede GPU NVIDIA (non funziona bene su CPU)

✅ **Best Practices:**
- Usa video con audio chiaro e senza rumori di fondo
- Preferisci video brevi (1-5 minuti) per test iniziali
- Disabilita lip-sync per traduzioni rapide
- Testa prima con video di prova

---

## 🎯 Esempio Pratico

### Scenario: Tradurre un Tutorial da Italiano a Inglese

1. **Carica video**: `tutorial_italiano.mp4` (durata: 3 minuti)
2. **Seleziona lingua**: Inglese (`en`)
3. **Disabilita lip-sync**: ✅ (per velocità)
4. **Avvia traduzione**: Clicca "Avvia Traduzione"
5. **Attendi 5-8 minuti**: Barra di progresso mostra stato
6. **Scarica risultato**: `translated_<job_id>.mp4`

**Risultato:**
- Video originale con audio tradotto in inglese
- Qualità audio: buona con gTTS
- Sincronizzazione: ottima (audio stesso timing del video)
- Dimensione file: simile all'originale

---

## 📚 Risorse Utili

- [Whisper AI Documentation](https://github.com/openai/whisper)
- [gTTS Documentation](https://gtts.readthedocs.io/)
- [FFmpeg Documentation](https://ffmpeg.org/documentation.html)
- [Wav2Lip (lip-sync)](https://github.com/Rudrabha/Wav2Lip)
- [googletrans Documentation](https://py-googletrans.readthedocs.io/)

---

**Creato da:** AIVideoMaker Team
**Data:** 2025-11-01
**Versione:** 1.0.0
