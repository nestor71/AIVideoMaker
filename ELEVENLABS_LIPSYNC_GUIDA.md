# 🎬 Guida Integrazione ElevenLabs per Lip-Sync Professionale

**Data:** 2025-11-01
**Soluzione:** ElevenLabs Video Dubbing API per traduzione con lip-sync

---

## 🎯 Perché ElevenLabs?

**ElevenLabs** è la soluzione **professionale** per video dubbing con lip-sync automatico.

### ✅ Vantaggi vs Wav2Lip

| Caratteristica | Wav2Lip (Open Source) | ElevenLabs API |
|----------------|----------------------|----------------|
| **Qualità Voci** | Robotiche (gTTS) | Ultra-realistiche (AI) |
| **Lip-Sync** | Manuale, complesso | Automatico |
| **Velocità** | 20-30 min (GPU) | 2-5 minuti (cloud) |
| **Setup** | Complesso (GPU, modelli) | API Key semplice |
| **Costo** | Gratis ma lento | $1-5 per video |
| **Hardware** | GPU NVIDIA obbligatoria | Nessun hardware speciale |
| **Qualità Finale** | Media | Eccellente |

---

## 📋 Cosa Offre ElevenLabs

### 1. **Video Dubbing API**

Traduce automaticamente video con:
- ✅ Trascrizione audio (come Whisper)
- ✅ Traduzione intelligente
- ✅ Sintesi vocale ultra-realistica
- ✅ **Lip-sync automatico** (movimento labbra sincronizzato)
- ✅ Preserva tono, emozioni, intonazione

### 2. **Voci AI Realistiche**

- **500+ voci** in 29 lingue
- Voci maschili, femminili, neutre
- Emozioni: felice, triste, eccitato, neutro
- **Voice cloning**: clona la voce originale del video

### 3. **Lingue Supportate**

Tutte quelle già implementate + molte altre:
- Inglese, Italiano, Spagnolo, Francese, Tedesco
- Portoghese, Russo, Giapponese, Cinese, Coreano
- Arabo, Hindi, Turco, Polacco, Olandese
- + altre 14 lingue

---

## 💰 Prezzi ElevenLabs

### Piani (Novembre 2024)

| Piano | Costo/Mese | Caratteri/Mese | Video Dubbing |
|-------|------------|----------------|---------------|
| **Free** | $0 | 10,000 | ❌ No |
| **Starter** | $5 | 30,000 | ✅ Sì (limitato) |
| **Creator** | $22 | 100,000 | ✅ Sì |
| **Pro** | $99 | 500,000 | ✅ Sì (prioritario) |
| **Scale** | $330 | 2,000,000 | ✅ Sì (ultra veloce) |

### Costo per Video

**Esempio video 5 minuti (750 parole):**
- Trascrizione + Traduzione + TTS: ~5,000 caratteri
- **Costo: ~$0.50 - $2.00** a seconda del piano

**Piano Creator ($22/mese):**
- ~50 video da 5 minuti al mese

---

## 🚀 Come Integrare ElevenLabs

### Step 1: Ottieni API Key

1. Vai su [elevenlabs.io](https://elevenlabs.io)
2. Crea account
3. Vai su **Profile → API Keys**
4. Genera API key
5. Copia la chiave

### Step 2: Aggiungi al file `.env`

```bash
# File: .env

# ElevenLabs API
ELEVENLABS_API_KEY=your_api_key_here
```

### Step 3: Installa SDK

```bash
pip install elevenlabs
```

### Step 4: Implementazione

Crea file `elevenlabs_translator.py`:

```python
"""
ElevenLabs Video Dubbing Integration
=====================================
Traduzione video professionale con lip-sync automatico
"""

import os
from elevenlabs import ElevenLabs
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class ElevenLabsTranslator:
    """Traduttore video con ElevenLabs API"""

    def __init__(self, api_key: str = None):
        """
        Inizializza client ElevenLabs

        Args:
            api_key: API key (default: da env ELEVENLABS_API_KEY)
        """
        self.api_key = api_key or os.getenv('ELEVENLABS_API_KEY')
        if not self.api_key:
            raise ValueError("ELEVENLABS_API_KEY non trovata in .env")

        self.client = ElevenLabs(api_key=self.api_key)

    def translate_video(
        self,
        input_video_path: str,
        output_video_path: str,
        target_language: str = 'en',
        source_language: str = 'auto'
    ) -> bool:
        """
        Traduce video con lip-sync automatico

        Args:
            input_video_path: Path video input
            output_video_path: Path video output
            target_language: Lingua target (es. 'en', 'it', 'es')
            source_language: Lingua sorgente ('auto' per rilevamento)

        Returns:
            True se successo
        """
        try:
            logger.info(f"Avvio dubbing ElevenLabs: {input_video_path}")

            # 1. Carica video
            with open(input_video_path, 'rb') as video_file:
                video_data = video_file.read()

            # 2. Crea job di dubbing
            dubbing_job = self.client.dubbing.dub_video(
                video=video_data,
                source_language=source_language,
                target_language=target_language,
                # Opzioni avanzate
                num_speakers=1,  # Numero speaker da rilevare
                watermark=False  # Rimuovi watermark (piani Pro+)
            )

            # 3. Attendi completamento
            logger.info(f"Job dubbing creato: {dubbing_job.dubbing_id}")

            # Polling stato job
            while True:
                status = self.client.dubbing.get_dubbing_project(
                    dubbing_job.dubbing_id
                )

                if status.status == 'completed':
                    logger.info("Dubbing completato!")
                    break
                elif status.status == 'failed':
                    raise Exception(f"Dubbing fallito: {status.error}")

                # Attendi 5 secondi prima del prossimo check
                import time
                time.sleep(5)

            # 4. Download video tradotto
            dubbed_video = self.client.dubbing.get_dubbed_file(
                dubbing_job.dubbing_id,
                language_code=target_language
            )

            # 5. Salva output
            with open(output_video_path, 'wb') as f:
                f.write(dubbed_video)

            logger.info(f"Video tradotto salvato: {output_video_path}")
            return True

        except Exception as e:
            logger.error(f"Errore ElevenLabs dubbing: {e}")
            return False

    def get_available_voices(self, language: str = None) -> list:
        """
        Ottieni lista voci disponibili

        Args:
            language: Filtra per lingua (opzionale)

        Returns:
            Lista voci disponibili
        """
        voices = self.client.voices.get_all()

        if language:
            voices = [v for v in voices if language in v.labels.get('language', '')]

        return voices


# Funzione helper per uso rapido
def translate_video_elevenlabs(
    input_path: str,
    output_path: str,
    target_language: str = 'en',
    source_language: str = 'auto'
) -> bool:
    """
    Traduce video con ElevenLabs (funzione semplificata)

    Args:
        input_path: Video input
        output_path: Video output
        target_language: Lingua destinazione
        source_language: Lingua sorgente (auto)

    Returns:
        True se successo
    """
    translator = ElevenLabsTranslator()
    return translator.translate_video(
        input_path,
        output_path,
        target_language,
        source_language
    )
```

---

## 🔧 Integrazione con AIVideoMaker

### Modifica `video_translator.py`

Aggiungi opzione per usare ElevenLabs:

```python
class VideoTranslator:
    def __init__(self, use_elevenlabs: bool = False):
        self.use_elevenlabs = use_elevenlabs

        if use_elevenlabs:
            # Verifica API key
            if not os.getenv('ELEVENLABS_API_KEY'):
                logger.warning("ELEVENLABS_API_KEY non trovata, uso gTTS")
                self.use_elevenlabs = False

    def translate_video(self, ...):
        if self.use_elevenlabs:
            # Usa ElevenLabs per qualità professionale
            return self._translate_with_elevenlabs(...)
        else:
            # Usa pipeline esistente (Whisper + gTTS)
            return self._translate_with_gtts(...)
```

### Modifica `app.py`

Aggiungi parametro opzionale per scegliere provider:

```python
@app.post("/api/translation/translate-video")
async def translate_video_endpoint(
    background_tasks: BackgroundTasks,
    file_id: str = Form(...),
    target_language: str = Form(...),
    source_language: str = Form('auto'),
    use_elevenlabs: bool = Form(False)  # Nuovo parametro
):
    # Crea translator con provider scelto
    use_elevenlabs = use_elevenlabs and os.getenv('ELEVENLABS_API_KEY')

    translator = VideoTranslator(use_elevenlabs=use_elevenlabs)
    ...
```

### Aggiorna Frontend

Aggiungi checkbox per scegliere provider:

```html
<div class="setting-group">
    <label class="checkbox-label">
        <input type="checkbox" id="useElevenLabs">
        <span>✨ Usa ElevenLabs (Lip-Sync Professionale)</span>
    </label>
    <small>
        🎭 Voci ultra-realistiche con lip-sync automatico.
        Richiede API key ElevenLabs. (~$1-2 per video)
    </small>
</div>
```

---

## 📊 Confronto Qualità

### Pipeline Attuale (gTTS + Whisper)

```
Video Input
    ↓
Whisper (Trascrizione) ✅ Ottimo
    ↓
Google Translate ✅ Buono
    ↓
gTTS (Voce) ⚠️ Robotica
    ↓
FFmpeg (Audio swap) ✅ OK
    ↓
Output (NO lip-sync) ❌

Qualità: 6/10
Velocità: Media (3-5 min)
Costo: Gratis
```

### Pipeline ElevenLabs

```
Video Input
    ↓
ElevenLabs API
  ├─ Trascrizione AI ✅ Eccellente
  ├─ Traduzione ✅ Eccellente
  ├─ Voce AI ✅ Ultra-realistica
  └─ Lip-Sync AI ✅ Automatico
    ↓
Output (CON lip-sync) ✅

Qualità: 9.5/10
Velocità: Veloce (2-5 min)
Costo: $1-2 per video
```

---

## 🎯 Quando Usare ElevenLabs

### ✅ Usa ElevenLabs Se:

- Video per uso professionale/pubblico
- Vuoi lip-sync perfetto
- Budget disponibile ($1-2 per video)
- Necessità voci ultra-realistiche
- Cliente paga per qualità premium

### ❌ Usa gTTS (Attuale) Se:

- Video interni/test
- Budget zero
- Qualità audio accettabile OK
- Non serve lip-sync
- Prototipazione rapida

---

## 🧪 Test ElevenLabs

### Test Rapido (CLI)

```python
# test_elevenlabs.py

import os
from elevenlabs_translator import translate_video_elevenlabs

# Imposta API key
os.environ['ELEVENLABS_API_KEY'] = 'your_key_here'

# Traduci video di test
success = translate_video_elevenlabs(
    input_path='test_video.mp4',
    output_path='test_video_en.mp4',
    target_language='en',
    source_language='it'
)

if success:
    print("✅ Traduzione ElevenLabs completata!")
else:
    print("❌ Errore traduzione")
```

---

## 📝 Configurazione Completa

### File `.env`

```bash
# ElevenLabs API
ELEVENLABS_API_KEY=sk_xxxxxxxxxxxxxxxxxxxxx

# Opzionale: preferenze
ELEVENLABS_MODEL=eleven_multilingual_v2  # Modello da usare
ELEVENLABS_VOICE_ID=default              # Voce specifica (opzionale)
```

### File `requirements.txt`

```txt
# Aggiungi:
elevenlabs==1.0.0
```

### Installazione

```bash
pip install elevenlabs
```

---

## 🎬 Esempio Completo

### Uso Nell'App

```python
# In video_translator.py

class VideoTranslator:
    def _translate_with_elevenlabs(
        self,
        input_video_path: str,
        output_video_path: str,
        target_language: str,
        source_language: str,
        progress_callback
    ) -> bool:
        """Traduce con ElevenLabs"""
        try:
            from elevenlabs_translator import ElevenLabsTranslator

            self._update_progress(progress_callback, 10, "Invio video a ElevenLabs...")

            translator = ElevenLabsTranslator()

            self._update_progress(progress_callback, 30, "ElevenLabs sta elaborando...")

            success = translator.translate_video(
                input_video_path,
                output_video_path,
                target_language,
                source_language
            )

            self._update_progress(progress_callback, 100, "✅ Completato!")

            return success

        except Exception as e:
            logger.error(f"Errore ElevenLabs: {e}")
            return False
```

---

## 📞 Supporto ElevenLabs

- **Documentazione**: https://elevenlabs.io/docs
- **API Reference**: https://elevenlabs.io/docs/api-reference
- **Discord Community**: https://discord.gg/elevenlabs
- **Support Email**: support@elevenlabs.io

---

## ✅ Checklist Implementazione

- [ ] Crea account ElevenLabs
- [ ] Scegli piano (min. Starter $5/mese)
- [ ] Genera API key
- [ ] Aggiungi a `.env`
- [ ] Installa SDK: `pip install elevenlabs`
- [ ] Crea `elevenlabs_translator.py`
- [ ] Modifica `video_translator.py` per supportare ElevenLabs
- [ ] Aggiorna frontend con checkbox opzionale
- [ ] Testa con video breve (1-2 min)
- [ ] Confronta qualità gTTS vs ElevenLabs
- [ ] Decidi se usare come default o opzione

---

## 🎉 Conclusione

**ElevenLabs è la soluzione professionale** per traduzione video con lip-sync.

### Costo/Beneficio

| Aspetto | Valore |
|---------|--------|
| **Qualità voci** | 10/10 |
| **Lip-sync automatico** | 10/10 |
| **Facilità setup** | 9/10 |
| **Velocità** | 9/10 |
| **Costo** | 7/10 ($1-2/video) |

**Raccomandazione:**
- **Usa gTTS gratis** per testing/prototipi
- **Offri ElevenLabs** come upgrade premium ($2-5 extra per video)
- **Migliore esperienza utente** finale

---

**Pronto per implementare lip-sync professionale! 🚀**
