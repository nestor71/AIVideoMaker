# 🎬 Chromakey & CTA Video - Guida Completa

## 📋 Indice
1. [Panoramica](#panoramica)
2. [Installazione](#installazione)
3. [Configurazione](#configurazione)
4. [Come Usare](#come-usare)
5. [Parametri Spiegati](#parametri-spiegati)
6. [Best Practices](#best-practices)
7. [Esempi Pratici](#esempi-pratici)
8. [Troubleshooting](#troubleshooting)
9. [Tips Avanzati](#tips-avanzati)
10. [FAQ](#faq)

---

## 🌟 Panoramica

La funzionalità **Chromakey & CTA (Call To Action)** ti permette di rimuovere lo sfondo verde (green screen) da un video e sovrapporre il soggetto su un altro video di sfondo. È perfetto per creare video professionali con presentatori, tutorial, call-to-action temporizzate e molto altro.

### Cos'è il Chromakey?

Il **chromakey** (o **chroma key**) è una tecnica che rimuove un colore specifico (solitamente verde o blu) da un video, rendendo trasparente quella porzione. Questo ti permette di:

- **Sovrapporre persone** su sfondi diversi
- **Creare CTA temporizzate**: mostra un presentatore che parla in momenti specifici del video
- **Combinare più video** in modo professionale
- **Aggiungere elementi interattivi** ai tuoi contenuti

### Caratteristiche Principali:

- ✅ **Rimozione Sfondo Verde/Blu**: Algoritmo HSV avanzato per dettagli precisi
- 🎯 **Posizionamento Personalizzato**: Posiziona il soggetto ovunque sullo schermo (X, Y)
- 📏 **Scala Dinamica**: Ridimensiona da 10% a 200% mantenendo la qualità
- 🔆 **Opacità Controllabile**: Da trasparente (0%) a opaco (100%)
- ⏱️ **Timing Preciso**: Mostra la CTA solo in momenti specifici (es: dal secondo 5 al 10)
- 🎵 **Audio Avanzato**: 6 modalità audio per sincronizzazione perfetta
- 🖼️ **Logo Overlay**: Aggiungi watermark o loghi con trasparenza
- ⚡ **Modalità Veloce + GPU**: Accelerazione hardware per elaborazione rapida
- 📊 **Progress Tracking**: Monitora l'avanzamento in tempo reale

---

## 🚀 Installazione

### 1. Installa le Dipendenze Python

```bash
# Dalla directory del progetto
pip install -r requirements.txt
```

Le dipendenze installate includono:
- `opencv-python` (cv2) - Per elaborazione video e rimozione sfondo
- `numpy` - Per operazioni matematiche sulle immagini
- `ffmpeg-python` - Per manipolazione audio/video avanzata

### 2. Verifica OpenCV

Controlla che OpenCV sia installato correttamente:

```bash
python -c "import cv2; print(cv2.__version__)"
```

Dovresti vedere un numero di versione (es: `4.8.1`).

### 3. Verifica FFmpeg

Il sistema usa FFmpeg per la gestione dell'audio. Verifica l'installazione:

```bash
ffmpeg -version
```

Se non installato:
- **macOS**: `brew install ffmpeg`
- **Ubuntu/Debian**: `sudo apt install ffmpeg`
- **Windows**: Scarica da [ffmpeg.org](https://ffmpeg.org/download.html)

### 4. (Opzionale) Accelerazione GPU

Per velocizzare l'elaborazione con GPU NVIDIA:

```bash
# Installa CUDA Toolkit dal sito NVIDIA
# Poi installa opencv-python con supporto CUDA
pip install opencv-contrib-python
```

---

## ⚙️ Configurazione

### Configurazione Globale

Il file `app/core/config.py` contiene le impostazioni predefinite:

```python
# Range HSV per rilevamento verde (valori predefiniti)
chromakey_default_lower_hsv: [40, 40, 40]   # Verde scuro
chromakey_default_upper_hsv: [80, 255, 255] # Verde brillante

# Sfocatura bordi per transizione smooth
chromakey_blur_kernel: 5  # Kernel Gaussian blur (pixel)

# Limiti di elaborazione
max_concurrent_jobs: 3      # Job contemporanei
max_upload_size: 500 MB     # Dimensione max file
```

### Impostazioni Utente Personalizzate

Ogni utente può salvare le proprie preferenze in `app/models/user_settings.py`:

```python
# Accedi alle tue impostazioni dalla UI
User Settings > Chromakey > Save Preferences

# Parametri salvabili:
- green_color: Colore da rimuovere (default: #00ff00)
- threshold: Sensibilità rimozione (0-255)
- background_type: "color", "image", "video"
- background_color: Colore sfondo alternativo
```

---

## 📖 Come Usare

### Flusso di Lavoro Standard

#### **Passo 1: Prepara i tuoi Video**

Avrai bisogno di:

1. **Video Foreground** (Green Screen):
   - Video del soggetto davanti a uno sfondo verde/blu
   - Formato: MP4, MOV, AVI
   - Illuminazione uniforme dello sfondo verde
   - Consigliato: 1920x1080px o superiore

2. **Video Background** (Sfondo):
   - Il video su cui sovrapporre il soggetto
   - Formato: MP4, MOV, AVI
   - Risoluzione consigliata: 1920x1080px
   - Durata: deve essere >= durata dell'overlay

#### **Passo 2: Accedi alla Funzionalità**

1. Avvia l'applicazione: `python app.py`
2. Apri il browser su `http://localhost:8000`
3. Vai alla tab **"🎬 Video"** nella barra di navigazione
4. Seleziona la sub-tab **"Chromakey"**

#### **Passo 3: Carica i Video**

**A) Carica Video Foreground (Green Screen)**
- Trascina il video nell'area **"Foreground Video (Green Screen)"**
- Oppure clicca su "Sfoglia File"
- Vedrai un'anteprima del video caricato

**B) Carica Video Background**
- Trascina il video nell'area **"Background Video"**
- Oppure clicca su "Sfoglia File"
- Vedrai un'anteprima del video di sfondo

#### **Passo 4: Configura i Parametri**

Usa gli slider per regolare:

1. **Position X** (-500 a +500 pixel):
   - 0 = centro orizzontale
   - -500 = spostato a sinistra
   - +500 = spostato a destra

2. **Position Y** (-500 a +500 pixel):
   - 0 = centro verticale
   - -500 = spostato in alto
   - +500 = spostato in basso

3. **Scale** (0.1 a 2.0):
   - 0.5 = metà dimensione
   - 1.0 = dimensione originale
   - 1.5 = 150% più grande

4. **Opacity** (0.0 a 1.0):
   - 0.0 = completamente trasparente
   - 0.5 = semi-trasparente
   - 1.0 = completamente opaco

5. **Green Threshold** (0 a 255):
   - Sensibilità rilevamento verde
   - Aumenta se il verde non viene rimosso completamente
   - Diminuisci se vengono rimossi colori errati

6. **Tolerance** (0 a 255):
   - Tolleranza nella rimozione del colore
   - Valori alti = rimozione più aggressiva
   - Valori bassi = rimozione più conservativa

#### **Passo 5: Imposta il Timing (Opzionale)**

Se vuoi mostrare la CTA solo in un momento specifico:

```javascript
// Esempio via API
{
  "start_time": 5.0,    // Inizia al secondo 5
  "end_time": 15.0      // Termina al secondo 15
}
```

**Nota**: Tramite UI web, la CTA è mostrata per tutta la durata del video. Per timing specifico, usa l'API REST.

#### **Passo 6: Scegli Modalità Audio**

Seleziona come gestire l'audio:

- **synced**: Audio sincronizzato (consigliato per CTA parlanti)
- **background**: Solo audio del video di sfondo
- **foreground**: Solo audio del video green screen
- **both**: Mix di entrambi gli audio
- **timed**: Audio sincronizzato solo durante la CTA
- **none**: Nessun audio

#### **Passo 7: Avvia l'Elaborazione**

1. Clicca su **"Elabora Chromakey"**
2. Il sistema mostrerà:
   - Barra di progresso (0-100%)
   - Messaggio di stato corrente
   - Tempo stimato rimanente

**Fasi di elaborazione:**
```
1. Caricamento video (0-10%)
2. Pre-processing frame (10-30%)
3. Rilevamento colore e creazione maschere (30-60%)
4. Compositing frame-by-frame (60-85%)
5. Aggiunta audio (85-95%)
6. Finalizzazione video (95-100%)
```

#### **Passo 8: Scarica il Risultato**

1. Una volta completato, vedrai l'anteprima del video finale
2. Clicca su **"Scarica Video"** per salvarlo
3. Oppure usa **"Nuova Elaborazione"** per fare un altro chromakey

---

## 🎛️ Parametri Spiegati

### 1. Parametri HSV (Hue, Saturation, Value)

Il sistema usa lo spazio colore HSV per rilevare il verde:

```python
# Lower HSV: [H_min, S_min, V_min]
lower_hsv = [40, 40, 40]
# Verde scuro: Tonalità 40°, Saturazione 40%, Luminosità 40%

# Upper HSV: [H_max, S_max, V_max]
upper_hsv = [80, 255, 255]
# Verde brillante: Tonalità 80°, Saturazione 100%, Luminosità 100%
```

**Quando modificarli:**
- **Sfondo blu**: Cambia H a [100-130]
- **Sfondo verde chiaro**: Aumenta S_min a [60-80]
- **Sfondo verde scuro**: Diminuisci V_min a [20-30]

### 2. Threshold e Tolerance

**Green Threshold** (0-255):
- Controlla quanta "verde" deve avere un pixel per essere rimosso
- Default: 100 (funziona bene per green screen standard)
- Aumenta a 150-200 per sfondi verde scuro
- Diminuisci a 50-80 per sfondi molto luminosi

**Tolerance** (0-255):
- Quanto "tollerante" è il sistema con variazioni di colore
- Default: 50
- Aumenta a 80-100 se hai ombre o pieghe nel telo verde
- Diminuisci a 20-40 per rimozione ultra-precisa

### 3. Edge Blur

```python
chromakey_blur_kernel = 5  # Pixel di sfocatura bordi
```

- **Valori bassi (1-3)**: Bordi netti, ma possibili artefatti
- **Valori medi (5-7)**: Bordi naturali (consigliato)
- **Valori alti (9-15)**: Bordi molto morbidi, effetto "alone"

### 4. Modalità Audio Dettagliate

| Modalità | Descrizione | Caso d'Uso |
|----------|-------------|------------|
| **synced** | Audio foreground sincronizzato perfettamente | CTA con presentatore che parla |
| **background** | Solo audio del video di sfondo | CTA senza parlato, musica di fondo |
| **foreground** | Solo audio del green screen | Focus sul messaggio CTA |
| **both** | Mix 50/50 di entrambi gli audio | Dialogo + musica |
| **timed** | Audio foreground solo durante CTA (start_time → end_time) | CTA intermittente |
| **none** | Nessun audio | Aggiungere audio personalizzato dopo |

### 5. Spill Reduction

Lo "spill" è la luce verde riflessa sul soggetto:

```python
spill_reduction = 0.5  # 0.0 = nessuna riduzione, 1.0 = massima
```

- **0.0**: Nessuna correzione (più veloce)
- **0.5**: Correzione bilanciata (consigliato)
- **1.0**: Massima correzione (può alterare colori del soggetto)

---

## 🎯 Best Practices

### 1. Preparazione Green Screen

✅ **Illuminazione Uniforme**:
- Usa almeno 2-3 luci per illuminare uniformemente il telo verde
- Evita ombre sul telo verde
- Distanza soggetto-sfondo: minimo 1.5 metri

✅ **Qualità del Telo Verde**:
- Telo liscio senza pieghe
- Colore verde brillante e uniforme
- Copri tutto il frame (evita bordi visibili)

❌ **Errori Comuni**:
- Telo verde con pieghe o sporco
- Illuminazione irregolare (un lato più scuro)
- Soggetto troppo vicino al telo (riflessi verdi)

### 2. Ripresa del Video Foreground

✅ **Impostazioni Camera**:
- Risoluzione: minimo 1920x1080px (Full HD)
- Framerate: 30fps o 60fps
- Bitrate: alto (20-50 Mbps per qualità professionale)
- Formato: MP4 (H.264)

✅ **Posizione Soggetto**:
- Centra il soggetto nel frame
- Lascia spazio sopra la testa (headroom)
- Mantieni distanza costante dalla camera

### 3. Scelta del Video Background

✅ **Compatibilità**:
- Risoluzione uguale o superiore al foreground
- Framerate uguale (30fps con 30fps)
- Durata >= durata della CTA

✅ **Composizione**:
- Evita sfondi troppo occupati (distraggono)
- Usa sfondi che complementano il soggetto
- Considera dove posizionerai la CTA (angolo, centro, ecc.)

### 4. Regolazione Parametri

**Workflow Consigliato:**

1. **Inizia con valori default**:
   - Position: 0, 0
   - Scale: 1.0
   - Opacity: 1.0
   - Threshold: 100
   - Tolerance: 50

2. **Testa con 5 secondi di video**:
   - Elabora solo una breve clip per testare velocemente
   - Regola threshold/tolerance fino a rimozione perfetta

3. **Ottimizza posizionamento**:
   - Sposta X/Y per posizionare il soggetto
   - Scala per dimensione appropriata
   - Opacità per effetti creativi

4. **Elabora video completo**:
   - Una volta soddisfatto, elabora il video intero
   - Salva le impostazioni per riutilizzarle

### 5. Performance e Velocità

✅ **Ottimizza i Tempi**:
- Usa `fast_mode=true` per elaborazione 2x più veloce (qualità leggermente ridotta)
- Abilita `gpu_accel=true` se hai GPU NVIDIA (3-5x più veloce)
- Riduci risoluzione video se non necessaria (es: 1280x720)

✅ **Gestione File**:
- Comprimi video prima dell'upload (usa HandBrake)
- Elimina video elaborati non necessari dalla cartella `outputs/`
- Monitora spazio disco (un video 5 min = ~500MB)

---

## 💡 Esempi Pratici

### Esempio 1: CTA Presentatore Angolo

**Scenario**: Tutorial con presentatore che appare nell'angolo in basso a destra.

**Parametri:**
```json
{
  "foreground_video": "presentatore_greenscreen.mp4",
  "background_video": "schermata_tutorial.mp4",
  "position_x": 400,      // Spostato a destra
  "position_y": 250,      // Spostato in basso
  "scale": 0.5,           // Metà dimensione
  "opacity": 1.0,         // Completamente opaco
  "start_time": 0,        // Dall'inizio
  "end_time": 60,         // Per 1 minuto
  "audio_mode": "synced", // Con parlato del presentatore
  "green_threshold": 100,
  "tolerance": 50
}
```

**Risultato**: Presentatore piccolo nell'angolo che parla durante tutto il tutorial.

---

### Esempio 2: CTA Intro Video

**Scenario**: Introduzione di 10 secondi all'inizio del video con presentatore a schermo intero.

**Parametri:**
```json
{
  "foreground_video": "intro_presentatore.mp4",
  "background_video": "video_principale.mp4",
  "position_x": 0,        // Centrato
  "position_y": 0,        // Centrato
  "scale": 1.5,           // 150% più grande
  "opacity": 1.0,         // Opaco
  "start_time": 0,        // Dall'inizio
  "end_time": 10,         // Primi 10 secondi
  "audio_mode": "foreground", // Solo audio presentatore
  "green_threshold": 120,
  "tolerance": 60
}
```

**Risultato**: Presentatore grande che introduce il video, poi scompare e parte il contenuto principale.

---

### Esempio 3: CTA Semi-Trasparente

**Scenario**: Watermark video con presentatore semi-trasparente sempre visibile.

**Parametri:**
```json
{
  "foreground_video": "logo_animato_greenscreen.mp4",
  "background_video": "contenuto_principale.mp4",
  "position_x": -350,     // Angolo in alto a sinistra
  "position_y": -250,
  "scale": 0.3,           // Molto piccolo
  "opacity": 0.6,         // Semi-trasparente
  "start_time": 0,
  "end_time": 120,        // Tutta la durata
  "audio_mode": "background", // Solo audio video principale
  "green_threshold": 100,
  "tolerance": 50
}
```

**Risultato**: Logo/brand sempre visibile come watermark trasparente.

---

### Esempio 4: Sfondo Blu (Bluescreen)

**Scenario**: Video girato con sfondo blu invece che verde.

**Modifiche Necessarie:**
```python
# In app/core/config.py, modifica:
chromakey_default_lower_hsv = [100, 100, 50]   # Blu scuro
chromakey_default_upper_hsv = [130, 255, 255]  # Blu brillante

# Oppure via API:
{
  "foreground_video": "video_bluescreen.mp4",
  "background_video": "sfondo.mp4",
  "green_threshold": 110,  # Soglia blu
  "tolerance": 60,
  # ... altri parametri
}
```

**Risultato**: Rimozione sfondo blu anziché verde.

---

## 🐛 Troubleshooting

### Problema: "Il verde non viene rimosso completamente"

**Cause:**
- Illuminazione non uniforme
- Threshold troppo basso
- Tolerance troppo bassa

**Soluzioni:**
1. Aumenta **Green Threshold** a 120-150
2. Aumenta **Tolerance** a 70-90
3. Modifica lower/upper HSV per catturare più sfumature di verde:
   ```python
   lower_hsv = [35, 30, 30]  # Range più ampio
   upper_hsv = [85, 255, 255]
   ```

---

### Problema: "Parti del soggetto vengono rimosse"

**Cause:**
- Threshold troppo alto
- Soggetto ha colori verdi (vestiti, oggetti)
- Riflessi verdi sul soggetto (spill)

**Soluzioni:**
1. Diminuisci **Green Threshold** a 70-90
2. Diminuisci **Tolerance** a 30-40
3. Abilita **spill_reduction**:
   ```python
   spill_reduction = 0.7  # Riduce riflessi verdi
   ```
4. Chiedi al soggetto di evitare vestiti verdi

---

### Problema: "Bordi del soggetto sono frastagliati"

**Cause:**
- Edge blur troppo basso
- Risoluzione video bassa
- Compressione video eccessiva

**Soluzioni:**
1. Aumenta **Edge Blur** a 7-11:
   ```python
   chromakey_blur_kernel = 9
   ```
2. Usa video sorgente ad alta risoluzione (1080p+)
3. Riduci compressione video (bitrate più alto)

---

### Problema: "Audio non sincronizzato"

**Cause:**
- Framerate diverso tra foreground e background
- Durata audio diversa da video
- Latenza di encoding

**Soluzioni:**
1. Assicurati che entrambi i video abbiano **stesso framerate** (30fps o 60fps)
2. Usa modalità audio **"synced"** per sincronizzazione automatica
3. Controlla la durata con FFprobe:
   ```bash
   ffprobe -i video.mp4 -show_entries format=duration
   ```

---

### Problema: "Elaborazione molto lenta"

**Cause:**
- Video ad alta risoluzione (4K)
- Modalità fast_mode disabilitata
- GPU non utilizzata

**Soluzioni:**
1. Abilita **fast_mode**:
   ```json
   {"fast_mode": true}
   ```
2. Abilita accelerazione GPU (se disponibile):
   ```json
   {"gpu_accel": true}
   ```
3. Riduci risoluzione a 1080p:
   ```bash
   ffmpeg -i input_4k.mp4 -vf scale=1920:1080 input_1080p.mp4
   ```

**Tempi Stimati:**
| Risoluzione | Durata | CPU | GPU |
|-------------|--------|-----|-----|
| 1280x720    | 1 min  | 2 min | 30 sec |
| 1920x1080   | 1 min  | 5 min | 1 min |
| 3840x2160   | 1 min  | 20 min | 4 min |

---

### Problema: "Errore: File not found"

**Cause:**
- Path file errato
- File non caricato correttamente
- Permessi insufficienti

**Soluzioni:**
1. Verifica che i file esistano:
   ```bash
   ls uploads/
   ls outputs/
   ```
2. Controlla permessi cartelle:
   ```bash
   chmod 755 uploads/ outputs/ temp/
   ```
3. Usa path assoluti invece di relativi

---

### Problema: "Out of Memory (OOM)"

**Cause:**
- Video troppo lungo o alta risoluzione
- RAM insufficiente
- Troppi job contemporanei

**Soluzioni:**
1. Elabora video più corti (max 5 minuti per volta)
2. Riduci **max_concurrent_jobs** a 1 in config
3. Aumenta RAM del sistema (min 8GB consigliati)
4. Usa video compressi

---

## 🚀 Tips Avanzati

### 1. Batch Processing Multiple CTA

Elabora più CTA contemporaneamente via API:

```python
import requests

ctas = [
    {"start": 0, "end": 10, "position_x": 0, "position_y": 0},
    {"start": 30, "end": 45, "position_x": 400, "position_y": 250},
    {"start": 90, "end": 120, "position_x": -400, "position_y": -250}
]

for i, cta in enumerate(ctas):
    response = requests.post('http://localhost:8000/api/v1/chromakey/process', json={
        "foreground_video": "cta.mp4",
        "background_video": "main.mp4",
        "output_name": f"output_cta_{i}.mp4",
        **cta
    })
    print(f"CTA {i} job ID: {response.json()['job_id']}")
```

### 2. Logo Overlay con Trasparenza

Aggiungi un logo watermark alla composizione:

```json
{
  "foreground_video": "presentatore.mp4",
  "background_video": "sfondo.mp4",
  "logo_path": "logo.png",        // PNG con alpha channel
  "logo_position": "top-right",   // top-left, top-right, bottom-left, bottom-right
  "logo_scale": 0.15,             // 15% dimensione originale
  "logo_opacity": 0.8             // 80% opacità
}
```

### 3. Preset Personalizzati

Salva configurazioni comuni:

```python
# In app/models/user_settings.py
PRESETS = {
    "corner_presenter": {
        "position_x": 400,
        "position_y": 250,
        "scale": 0.5,
        "opacity": 1.0,
        "audio_mode": "synced"
    },
    "fullscreen_intro": {
        "position_x": 0,
        "position_y": 0,
        "scale": 1.5,
        "opacity": 1.0,
        "audio_mode": "foreground"
    },
    "watermark_logo": {
        "position_x": -350,
        "position_y": -250,
        "scale": 0.3,
        "opacity": 0.6,
        "audio_mode": "background"
    }
}

# Usa via API:
{
  "preset": "corner_presenter",
  "foreground_video": "video.mp4",
  "background_video": "sfondo.mp4"
}
```

### 4. Chromakey Multi-Layer

Sovrapponi più soggetti green screen:

```python
# Primo layer
layer1 = chromakey_service.process({
    "foreground": "persona1.mp4",
    "background": "sfondo.mp4",
    "position_x": -200,
    "output": "temp_layer1.mp4"
})

# Secondo layer (usa output primo come background)
layer2 = chromakey_service.process({
    "foreground": "persona2.mp4",
    "background": "temp_layer1.mp4",
    "position_x": 200,
    "output": "final.mp4"
})
```

**Risultato**: Due persone green screen sullo stesso sfondo.

### 5. Integrazione con Pipeline

Automatizza workflow completi:

```json
{
  "pipeline": [
    {
      "step": 1,
      "job_type": "chromakey",
      "parameters": {
        "foreground_video": "cta.mp4",
        "background_video": "main.mp4",
        "output_name": "video_con_cta.mp4"
      }
    },
    {
      "step": 2,
      "job_type": "seo_metadata",
      "parameters": {
        "video": "video_con_cta.mp4",
        "generate_description": true
      }
    },
    {
      "step": 3,
      "job_type": "youtube_upload",
      "parameters": {
        "video": "video_con_cta.mp4",
        "title": "Tutorial con CTA",
        "privacy": "public"
      }
    }
  ]
}
```

### 6. Monitoring e Logging

Traccia l'elaborazione in dettaglio:

```python
def progress_callback(progress, message):
    print(f"[{progress}%] {message}")
    # Salva in database
    db.update_job(job_id, progress=progress, message=message)
    # Notifica via WebSocket
    websocket.send({"job_id": job_id, "progress": progress})

chromakey_service.process(params, callback=progress_callback)
```

### 7. Color Grading Post-Chromakey

Migliora colori dopo la composizione:

```python
# Aggiungi in chromakey_service.py dopo compositing
def apply_color_grading(frame):
    # Aumenta saturazione
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    hsv[:, :, 1] = np.clip(hsv[:, :, 1] * 1.2, 0, 255)

    # Aumenta contrasto
    lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
    lab[:, :, 0] = np.clip(lab[:, :, 0] * 1.1, 0, 255)

    return cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
```

---

## 🎓 FAQ

**Q: Posso usare uno sfondo verde sfumato?**
A: Non consigliato. Lo sfondo deve essere il più uniforme possibile. Sfumature e gradienti creano problemi nella rimozione.

---

**Q: Quanto deve essere grande il green screen?**
A: Deve coprire completamente il frame della camera. Minimo 2x3 metri per riprese a mezzobusto, 3x6 metri per corpo intero.

---

**Q: Posso usare un muro verde invece di un telo?**
A: Sì, se dipinto con vernice verde chroma key (es: Rosco Chroma Key Green). Assicurati che sia opaco e uniforme.

---

**Q: Il sistema funziona con blue screen?**
A: Sì! Modifica i parametri HSV per rilevare il blu:
```python
lower_hsv = [100, 100, 50]   # Blu
upper_hsv = [130, 255, 255]
```

---

**Q: Posso rimuovere altri colori (rosso, giallo)?**
A: Tecnicamente sì, ma verde e blu sono preferiti perché:
- Meno presenti nei toni della pelle
- Più facili da illuminare uniformemente
- Standard nell'industria

---

**Q: Quanto costa in termini di processing?**
A: Elaborazione locale, nessun costo API. Solo risorse del tuo computer (CPU/GPU).

---

**Q: Posso elaborare video 4K?**
A: Sì, ma richiede:
- 16GB+ RAM
- GPU potente (o molto tempo con CPU)
- Almeno 10-20 minuti per video di 1 minuto

---

**Q: Il risultato è commercialmente utilizzabile?**
A: Sì, il video elaborato è completamente tuo. Assicurati di avere diritti sui video sorgente.

---

**Q: Come ottengo risultati professionali?**
A:
1. Illumina uniformemente il green screen (3+ luci)
2. Usa video sorgente ad alta qualità (1080p+, bitrate alto)
3. Mantieni distanza soggetto-sfondo (min 1.5m)
4. Regola finemente threshold e tolerance
5. Usa edge blur adeguato (5-9 pixel)

---

**Q: Posso usare video da smartphone?**
A: Sì, ma assicurati di:
- Filmare in 1080p o 4K
- Buona illuminazione del green screen
- Tenere lo smartphone stabile (usa un treppiede)

---

**Q: L'audio del presentatore è sfasato?**
A: Usa modalità audio **"synced"** e verifica che foreground e background abbiano lo stesso framerate (30fps o 60fps).

---

**Q: Posso automatizzare l'upload a YouTube dopo?**
A: Sì! Usa la pipeline con step sequenziali:
```
chromakey → seo_metadata → youtube_upload
```

---

## 📊 Metriche e Performance

### Consumo Risorse

| Risoluzione | RAM | CPU (8 core) | GPU (RTX 3060) | Tempo (1 min video) |
|-------------|-----|--------------|----------------|---------------------|
| 720p        | 2GB | 100% (2 min) | 30% (30 sec)   | 30 sec - 2 min      |
| 1080p       | 4GB | 100% (5 min) | 50% (1 min)    | 1 min - 5 min       |
| 4K          | 8GB | 100% (20 min)| 80% (4 min)    | 4 min - 20 min      |

### Qualità Output

- **Codec Video**: H.264 (compatibilità universale)
- **Bitrate**: 5-15 Mbps (alta qualità)
- **Audio**: AAC 192 kbps stereo
- **Framerate**: Mantiene framerate originale
- **Risoluzione**: Mantiene risoluzione background

---

## 📚 Risorse Utili

- [OpenCV Documentation - Color Detection](https://docs.opencv.org/4.x/df/d9d/tutorial_py_colorspaces.html)
- [Green Screen Best Practices (YouTube Creator Academy)](https://creatoracademy.youtube.com/)
- [FFmpeg Audio Mixing Guide](https://trac.ffmpeg.org/wiki/AudioChannelManipulation)
- [HSV Color Space Explained](https://en.wikipedia.org/wiki/HSL_and_HSV)

---

## 🤝 Supporto

Per problemi o domande:
1. Consulta questa guida e la sezione Troubleshooting
2. Controlla i log in `app.log` per errori dettagliati
3. Verifica le impostazioni in `app/core/config.py`
4. Testa con video brevi (5-10 secondi) prima di elaborare video lunghi
5. Apri una issue su GitHub con screenshot e log

---

## 📝 Changelog

**v1.0.0** (2025-11-11)
- Implementazione completa chromakey con HSV detection
- 6 modalità audio con sincronizzazione automatica
- Posizionamento, scala, opacità personalizzabili
- Supporto logo overlay
- Accelerazione GPU opzionale
- API REST completa
- UI web interattiva
- Job management con progress tracking
- Pipeline orchestration

---

**Buona creazione di video con Chromakey! 🎬✨**
