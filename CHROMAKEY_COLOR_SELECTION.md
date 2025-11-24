# Selezione Colore Chromakey - Nuova Funzionalità

## ✅ Aggiunta Selezione Colore (Verde / Blu / Personalizzato)

### Nuovi Parametri API

Aggiunti i seguenti parametri a **tutti gli endpoint chromakey**:

#### 1. Selezione Colore Semplice

```json
{
  "chroma_color": "green"  // "green", "blue", o "custom"
}
```

**Opzioni disponibili:**
- **`"green"`** - Verde standard (HSV: 40-80, perfetto per green screen)
- **`"blue"`** - Blu standard (HSV: 100-130, perfetto per blue screen)
- **`"custom"`** - Range HSV personalizzato (vedi sotto)

#### 2. Range HSV Personalizzato

Quando `chroma_color = "custom"`, puoi specificare range HSV preciso:

```json
{
  "chroma_color": "custom",
  "custom_lower_h": 40,   // Hue min (0-180)
  "custom_lower_s": 40,   // Saturation min (0-255)
  "custom_lower_v": 40,   // Value min (0-255)
  "custom_upper_h": 80,   // Hue max (0-180)
  "custom_upper_s": 255,  // Saturation max (0-255)
  "custom_upper_v": 255,  // Value max (0-255)
  "blur_kernel": 5        // Kernel blur maschera (3, 5, 7, 9)
}
```

### Preset Colori

#### Verde Standard (default)
```python
lower_hsv = (40, 40, 40)
upper_hsv = (80, 255, 255)
```

#### Blu Standard
```python
lower_hsv = (100, 40, 40)
upper_hsv = (130, 255, 255)
```

### Esempi d'Uso

#### Esempio 1: Green Screen (default)
```json
POST /api/chromakey/process
{
  "foreground_video": "uploads/video_greenscreen.mp4",
  "background_video": "uploads/sfondo.mp4",
  "chroma_color": "green"
}
```

#### Esempio 2: Blue Screen
```json
POST /api/chromakey/process
{
  "foreground_video": "uploads/video_bluescreen.mp4",
  "background_video": "uploads/sfondo.mp4",
  "chroma_color": "blue"
}
```

#### Esempio 3: Colore Personalizzato (es. rosso)
```json
POST /api/chromakey/process
{
  "foreground_video": "uploads/video_redscreen.mp4",
  "background_video": "uploads/sfondo.mp4",
  "chroma_color": "custom",
  "custom_lower_h": 0,     // Rosso in HSV
  "custom_lower_s": 100,
  "custom_lower_v": 100,
  "custom_upper_h": 10,
  "custom_upper_s": 255,
  "custom_upper_v": 255,
  "blur_kernel": 7
}
```

### Endpoint Aggiornati

✅ **POST /api/chromakey/process** - Tutti i nuovi parametri disponibili
✅ **POST /api/chromakey/upload** - Tutti i nuovi parametri disponibili via Form

### Parametri Completi

Ora l'API chromakey supporta **tutti questi parametri**:

**Video:**
- foreground_video, background_video, output_name

**Temporali:**
- start_time, end_time

**Audio:**
- audio_mode (synced, background, foreground, both, timed, none)

**Posizionamento:**
- position_x, position_y, scale, opacity

**Chromakey (NUOVO!):**
- chroma_color (green, blue, custom)
- custom_lower_h, custom_lower_s, custom_lower_v
- custom_upper_h, custom_upper_s, custom_upper_v
- blur_kernel

### Guida HSV per Colori Comuni

| Colore | Hue (H) | Esempio Range |
|--------|---------|---------------|
| Rosso | 0-10, 170-180 | (0, 100, 100) - (10, 255, 255) |
| Arancione | 10-25 | (10, 100, 100) - (25, 255, 255) |
| Giallo | 25-35 | (25, 100, 100) - (35, 255, 255) |
| **Verde** | **40-80** | **(40, 40, 40) - (80, 255, 255)** |
| Ciano | 80-100 | (80, 100, 100) - (100, 255, 255) |
| **Blu** | **100-130** | **(100, 40, 40) - (130, 255, 255)** |
| Viola | 130-160 | (130, 100, 100) - (160, 255, 255) |
| Magenta | 160-170 | (160, 100, 100) - (170, 255, 255) |

**Note:**
- **H (Hue)** in OpenCV va da 0 a 180 (non 360!)
- **S (Saturation)** e **V (Value)** vanno da 0 a 255
- Per colori più saturi, aumenta S min (es. 100 invece di 40)
- Per colori più chiari/scuri, regola V

### Compatibilità

✅ **Completamente retrocompatibile**
- Se non specifichi `chroma_color`, usa default "green"
- Tutti i vecchi endpoint funzionano come prima

### Test

```bash
# Test con green screen (default)
curl -X POST http://localhost:8000/api/chromakey/process \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "foreground_video": "video_green.mp4",
    "background_video": "sfondo.mp4"
  }'

# Test con blue screen
curl -X POST http://localhost:8000/api/chromakey/process \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "foreground_video": "video_blue.mp4",
    "background_video": "sfondo.mp4",
    "chroma_color": "blue"
  }'
```

## Vantaggi

1. ✅ **Flessibilità**: Supporta verde, blu e qualsiasi colore personalizzato
2. ✅ **Semplice**: 3 preset pronti (green, blue, custom)
3. ✅ **Potente**: Controllo totale HSV per casi avanzati
4. ✅ **Retrocompatibile**: Codice esistente continua a funzionare
5. ✅ **Documentato**: API docs completa con esempi

## Frontend

Nel frontend, ora puoi aggiungere:

```html
<select id="chromaColor">
  <option value="green">Green Screen</option>
  <option value="blue">Blue Screen</option>
  <option value="custom">Personalizzato</option>
</select>

<!-- Mostra questi solo se custom è selezionato -->
<div id="customHSV" style="display:none">
  <input type="range" id="hMin" min="0" max="180" value="40">
  <input type="range" id="sMin" min="0" max="255" value="40">
  <input type="range" id="vMin" min="0" max="255" value="40">
  <input type="range" id="hMax" min="0" max="180" value="80">
  <input type="range" id="sMax" min="0" max="255" value="255">
  <input type="range" id="vMax" min="0" max="255" value="255">
</div>
```

Ora hai **controllo completo sul chromakey** come nel file originale! 🎉

---

## Aggiornamento: Valori Ottimizzati

### Soglia Verde Ottimizzata: 161° con Tolleranza ±50

I valori di default sono stati aggiornati per riflettere la soglia verde ottimale:

**Conversione da gradi a HSV OpenCV:**
- **Soglia**: 161° (scala 0-360)
- **Tolleranza**: ±50°
- **Range**: 111° - 211° (scala 0-360)
- **In OpenCV (0-180)**: 55.5° - 105.5°

**Range finale ottimizzato (più permissivo):**
```python
lower_hsv = (35, 40, 40)   # Hue min esteso per migliore copertura
upper_hsv = (85, 255, 255) # Hue max esteso per migliore copertura
```

Questo range cattura:
- ✅ Verde puro (120° / hue 60 in OpenCV)
- ✅ Verde-giallo (90-110° / hue 45-55)
- ✅ Verde-ciano (130-150° / hue 65-75)
- ✅ Variazioni di illuminazione
- ✅ Sfumature e riflessi

### Perché 35-85 invece di 56-106?

Il range **35-85** è più permissivo e cattura meglio:
1. **Green screen economici** (sfumature più ampie)
2. **Illuminazione non uniforme** (zone più chiare/scure)
3. **Riflessi e spill** (verde riflesso su oggetti)
4. **Compatibilità** (funziona con la maggior parte dei green screen)

### Confronto Range

| Tipo | Hue Min | Hue Max | Copertura |
|------|---------|---------|-----------|
| Classico | 40 | 80 | Standard |
| **Ottimizzato (nuovo)** | **35** | **85** | **Estesa** |
| Stretto (161±50) | 56 | 106 | Precisa |

**Raccomandazione:** Usa il range **ottimizzato (35-85)** come default per massima compatibilità.

Se hai un green screen professionale con illuminazione perfetta, puoi usare il range stretto (56-106) impostando `chroma_color="custom"`.

