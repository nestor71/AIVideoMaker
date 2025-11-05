# Estensioni File Supportate - AI Video Maker

## 📹 **Video** (13 formati)
- **Comuni**: MP4, AVI, MOV, MKV, WEBM
- **Legacy**: FLV, WMV, M4V
- **Streaming**: TS, MPG, MPEG
- **Mobile**: 3GP
- **Open**: OGV

**Metadata visualizzati**: Nome, dimensione, durata, risoluzione, codec, bitrate

---

## 🎵 **Audio** (8 formati)
- **Lossy**: MP3, AAC, OGG, OPUS, WMA
- **Lossless**: WAV, FLAC, M4A

**Metadata visualizzati**: Nome, dimensione, durata, bitrate

---

## 🖼️ **Immagini** (10 formati)
- **Raster**: PNG, JPG, JPEG, GIF, BMP, WEBP, TIFF, TIF
- **Vettoriale**: SVG
- **Icone**: ICO

**Metadata visualizzati**: Nome, dimensione, risoluzione (width x height)

---

## 📝 **Sottotitoli** (5 formati)
- SRT, VTT, ASS, SSA, SUB

**Metadata visualizzati**: Nome, dimensione, numero righe

---

## 📄 **Documenti** (6 formati)
- **Testo**: TXT, LOG
- **Office**: PDF, DOC, DOCX, RTF, ODT

**Metadata visualizzati**: Nome, dimensione, numero righe (solo TXT/LOG)

---

## 📦 **Archivi** (7 formati)
- **ZIP**, RAR, 7Z, TAR, GZ, BZ2, XZ

**Metadata visualizzati**: Nome, dimensione

---

## 🔢 **Dati** (6 formati)
- JSON, XML, CSV, YAML, YML, TOML

**Metadata visualizzati**: Nome, dimensione, numero righe

---

## 🎨 **Icone e Colori nel Modal**

Ogni tipo di file ha un'icona FontAwesome e un colore distintivo:

| Tipo | Icona | Colore | Hex |
|------|-------|--------|-----|
| Video | `fa-file-video` | Rosa | `#ec4899` |
| Audio | `fa-file-audio` | Viola | `#8b5cf6` |
| Sottotitoli | `fa-closed-captioning` | Ciano | `#06b6d4` |
| Immagini | `fa-file-image` | Arancione | `#f59e0b` |
| Documenti | `fa-file-alt` | Verde | `#10b981` |
| Archivi | `fa-file-archive` | Arancio scuro | `#f97316` |
| Dati | `fa-file-code` | Blu | `#3b82f6` |
| Altri | `fa-file` | Indigo | `#818cf8` |

---

## 🧪 Test Eseguiti

✅ **MP4**: video - Video (con durata, risoluzione, codec)
✅ **SRT**: subtitle - Sottotitoli
✅ **PNG**: image - Immagine
✅ **JSON**: data - Dati
✅ **TXT**: document - Documento (con conteggio righe)
✅ **ZIP**: archive - Archivio
✅ **FLV**: video - Video
✅ **GIF**: image - Immagine

---

## 🚀 Utilizzo

Tutti i file generati dall'applicazione vengono automaticamente riconosciuti e visualizzati nel modal di completamento con:
- ✨ Icona colorata per tipo
- 📊 Dimensione formattata (MB/KB)
- ⏱️ Durata (per video/audio)
- 🎯 Badge estensione
- 📥 Download ZIP di tutti i file

**Totale formati supportati**: **55 estensioni**
