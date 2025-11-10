# 🎬 AI Video Maker - Chromakey Editor

Editor professionale per chromakey e compositing video con interfaccia web moderna e menu hamburger accattivante.

## ✨ Caratteristiche

- **Interfaccia Web Moderna**: Design responsive con gradiente accattivante
- **Menu Hamburger Animato**: Navigazione intuitiva per dispositivi mobili
- **Chromakey Professionale**: Rimozione sfondo verde con parametri avanzati
- **Timing Preciso**: Controllo temporale per call-to-action
- **Audio Sincronizzato**: Multiple opzioni di gestione audio
- **Modalità Veloce**: Ottimizzazioni per elaborazione rapida
- **Upload Drag & Drop**: Interfaccia drag-and-drop per file video
- **Progress Monitoring**: Monitoraggio in tempo reale dell'elaborazione

## 🚀 Quick Start

### 1. Installazione

```bash
# Clone o scarica il progetto
cd AIVideoMaker

# Crea ambiente virtuale
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# o
venv\\Scripts\\activate  # Windows

# Installa dipendenze
pip install -r requirements.txt
```

### 2. Avvio Web App

```bash
# Avvia il server FastAPI
python app.py

# Oppure usa uvicorn direttamente
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

Apri il browser su: `http://localhost:8000`

### 3. Avvio GUI Desktop (Tkinter)

```bash
python gui.py
```

### 4. Uso da Command Line

```bash
python chromakey.py call_to_action.mp4 background.mp4 --start 5 --audio synced --fast
```

## 📁 Struttura Progetto

```
AIVideoMaker/
├── app.py                  # FastAPI web application
├── chromakey.py           # Core video processing logic
├── gui.py                 # Tkinter desktop GUI
├── requirements.txt       # Python dependencies
├── README.md             # Documentation
├── templates/            # HTML templates
│   ├── index.html        # Main web interface (all-in-one)
│   └── index_clean.html  # Clean separated version
├── static/               # Web assets
│   ├── css/
│   │   ├── styles.css    # Main stylesheet
│   │   └── alerts.css    # Alert system styles
│   └── js/
│       └── app.js        # JavaScript functionality
├── uploads/              # Uploaded video files
└── outputs/              # Processed video results
```

## 🎯 Funzionalità Web Interface

### Menu Hamburger
- **Animazione fluida** con trasformazione icona
- **Sidebar scorrevole** con backdrop blur
- **Menu responsive** per mobile e desktop
- **Chiusura automatica** al click esterno

### Upload Video
- **Drag & Drop** intuitivo per file video
- **Preview anteprime** dei file caricati
- **Validazione formato** (MP4, AVI, MOV, MKV)
- **Progress indicator** durante upload

### Impostazioni Avanzate
- **Timing preciso**: Slider per tempo inizio e durata
- **Posizionamento**: Controlli X/Y, scala, opacità  
- **Audio sync**: 6 modalità audio diverse
- **Performance**: Modalità veloce e GPU acceleration

### Processing
- **Real-time progress** con barra di progresso
- **Status monitoring** dell'elaborazione
- **Stop/Resume** controllo del processo
- **Download automatico** del risultato

## 🛠️ Configurazione Avanzata

### Parametri Chromakey

```bash
# Parametri HSV per green screen
--h-min 40 --h-max 80      # Hue range
--s-min 40 --s-max 255     # Saturation range  
--v-min 40 --v-max 255     # Value range
--blur 5                   # Blur kernel size
```

### Opzioni Audio

- `background`: Usa solo audio del video di sfondo
- `foreground`: Usa solo audio della call-to-action  
- `both`: Mix entrambi gli audio
- `timed`: Audio temporizzato con timing preciso
- `synced`: Audio sincronizzato (raccomandato)
- `none`: Nessun audio

### Performance

```bash
--fast          # Modalità veloce (meno qualità, più veloce)
--gpu           # Accelerazione GPU (se supportata)
```

## 📱 Responsive Design

- **Mobile-first approach**
- **Touch-friendly controls** 
- **Adaptive layouts** per tutti i device
- **Hamburger menu** per navigazione mobile
- **Swipe gestures** supportate

## 🎨 Personalizzazione Stili

### Colori Principali
- **Primary**: `#00d4aa` (Teal accattivante)
- **Secondary**: `#6c5ce7` (Purple)  
- **Danger**: `#ff6b6b` (Red)
- **Background**: Gradiente `#667eea` → `#764ba2`

### CSS Variabili
```css
:root {
  --primary-color: #00d4aa;
  --secondary-color: #6c5ce7;
  --danger-color: #ff6b6b;
  --success-color: #00d4aa;
}
```

## 🔧 API Endpoints

### Upload
- `POST /api/upload` - Upload video file
- `GET /api/jobs/{job_id}` - Check processing status

### Processing  
- `POST /api/process` - Start video processing
- `DELETE /api/jobs/{job_id}` - Cancel/delete job

### Download
- `GET /api/download/{job_id}` - Download processed video

## 🚀 Deployment

### Docker (Raccomandato)
```bash
# Crea Dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8000

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Production
```bash
# Con Gunicorn
gunicorn -w 4 -k uvicorn.workers.UvicornWorker app:app --bind 0.0.0.0:8000
```

## 📋 TODO

- [ ] Implementare anteprima video real-time
- [ ] Aggiungere template preconfigurati
- [ ] Sistema di gestione progetti  
- [ ] Export in multipli formati
- [ ] Integrazione cloud storage
- [ ] Editor timeline avanzato

## 🤝 Contributing

1. Fork il progetto
2. Crea feature branch (`git checkout -b feature/AmazingFeature`)  
3. Commit modifiche (`git commit -m 'Add some AmazingFeature'`)
4. Push branch (`git push origin feature/AmazingFeature`)
5. Apri Pull Request

## 📄 License

Distribuito sotto licenza MIT. Vedi `LICENSE` per maggiori informazioni.

## 🙏 Credits

- **OpenCV** per computer vision
- **FastAPI** per web framework  
- **Font Awesome** per icone
- **Uvicorn** per ASGI server

---

**Sviluppato con ❤️ per creatori di contenuti**# Test SSH configurato con successo - Mon Nov 10 01:56:47 CET 2025
