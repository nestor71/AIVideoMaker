"""
Transcription Service - Audio/Video Transcription
==================================================
Servizio indipendente per trascrizione audio/video con Whisper:
- Trascrizione automatica con rilevamento lingua
- Supporto 99+ lingue
- Timestamps per ogni segmento
- Export in formati multipli (JSON, SRT, VTT, TXT)
- Opzioni modello Whisper (tiny, base, small, medium, large)

Completamente testabile, nessuna dipendenza da FastAPI.
"""

import subprocess
import tempfile
import logging
from pathlib import Path

# Import opzionale di Whisper (per permettere avvio server senza Whisper installato)
try:
    import whisper
    WHISPER_AVAILABLE = True
except ImportError:
    whisper = None
    WHISPER_AVAILABLE = False
from typing import Optional, Callable, Dict, Any, List
from dataclasses import dataclass

from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class TranscriptionParams:
    """Parametri trascrizione"""
    media_path: Path  # Video o audio
    output_path: Path  # File output JSON

    # Opzioni Whisper
    model_size: str = "base"  # tiny, base, small, medium, large
    language: Optional[str] = None  # None = auto-detect, o codice lingua (en, it, es, etc.)
    task: str = "transcribe"  # "transcribe" o "translate" (traduce in inglese)

    # Opzioni output
    export_formats: List[str] = None  # ["json", "srt", "vtt", "txt"]
    word_timestamps: bool = False  # Timestamps per parola (più lento)


class TranscriptionService:
    """
    Servizio trascrizione audio/video con Whisper.

    Modelli disponibili:
    - tiny: Veloce, meno preciso (~1GB RAM)
    - base: Bilanciato (~1GB RAM)
    - small: Buona precisione (~2GB RAM)
    - medium: Alta precisione (~5GB RAM)
    - large: Massima precisione (~10GB RAM)
    """

    AVAILABLE_MODELS = ["tiny", "base", "small", "medium", "large"]

    def __init__(self, config: Optional[Any] = None):
        """Inizializza service"""
        self.config = config or settings
        self.ffmpeg_path = self.config.ffmpeg_path
        self.model_cache = {}  # Cache modelli caricati

    def transcribe(
        self,
        params: TranscriptionParams,
        progress_callback: Optional[Callable[[int, str], bool]] = None
    ) -> Dict[str, Any]:
        """
        Trascrivi audio/video

        Args:
            params: Parametri trascrizione
            progress_callback: Callback progresso (progress_pct, message)

        Returns:
            Dict con risultato trascrizione

        Raises:
            FileNotFoundError: File non trovato
            ValueError: Parametri non validi
            RuntimeError: Errore trascrizione
        """
        # Valida input
        if not params.media_path.exists():
            raise FileNotFoundError(f"File non trovato: {params.media_path}")

        if params.model_size not in self.AVAILABLE_MODELS:
            raise ValueError(f"Modello non valido. Disponibili: {self.AVAILABLE_MODELS}")

        if progress_callback:
            progress_callback(0, "Estrazione audio...")

        # Estrai audio se è video
        audio_path = self._extract_audio(params.media_path)

        try:
            if progress_callback:
                progress_callback(20, f"Caricamento modello Whisper ({params.model_size})...")

            # Carica modello Whisper
            model = self._load_model(params.model_size)

            if progress_callback:
                progress_callback(40, "Trascrizione in corso...")

            # Trascrivi
            result = model.transcribe(
                str(audio_path),
                language=params.language,
                task=params.task,
                word_timestamps=params.word_timestamps,
                verbose=False
            )

            if progress_callback:
                progress_callback(80, "Elaborazione risultati...")

            # Processa risultato
            transcription = self._process_result(result, params)

            if progress_callback:
                progress_callback(100, "Trascrizione completata!")

            return transcription

        finally:
            # Cleanup audio temporaneo se estratto
            if audio_path != params.media_path and audio_path.exists():
                audio_path.unlink()

    def _extract_audio(self, media_path: Path) -> Path:
        """
        Estrai audio da video (se necessario)

        Args:
            media_path: Path media

        Returns:
            Path audio WAV
        """
        # Se è già audio WAV, usa direttamente
        if media_path.suffix.lower() in ['.wav']:
            return media_path

        # Estrai audio in WAV temporaneo
        temp_audio = Path(tempfile.mktemp(suffix='.wav'))

        cmd = [
            self.ffmpeg_path,
            '-i', str(media_path),
            '-vn',  # No video
            '-acodec', 'pcm_s16le',  # WAV PCM 16-bit
            '-ar', '16000',  # Sample rate 16kHz (Whisper optimal)
            '-ac', '1',  # Mono
            '-y',  # Overwrite
            str(temp_audio)
        ]

        try:
            subprocess.run(cmd, capture_output=True, check=True)
            return temp_audio
        except subprocess.CalledProcessError as e:
            logger.error(f"Errore estrazione audio: {e.stderr.decode()}")
            raise RuntimeError(f"Impossibile estrarre audio da {media_path}")

    def _load_model(self, model_size: str) -> whisper.Whisper:
        """
        Carica modello Whisper (con cache)

        Args:
            model_size: Dimensione modello

        Returns:
            Modello Whisper caricato
        """
        if model_size not in self.model_cache:
            logger.info(f"Caricamento modello Whisper: {model_size}")
            self.model_cache[model_size] = whisper.load_model(model_size)

        return self.model_cache[model_size]

    def _process_result(
        self,
        result: Dict[str, Any],
        params: TranscriptionParams
    ) -> Dict[str, Any]:
        """
        Processa risultato Whisper e salva output

        Args:
            result: Output Whisper
            params: Parametri

        Returns:
            Dict con metadati trascrizione
        """
        # Salva JSON principale
        import json
        output_data = {
            "text": result["text"],
            "language": result.get("language"),
            "segments": [
                {
                    "id": seg["id"],
                    "start": seg["start"],
                    "end": seg["end"],
                    "text": seg["text"].strip()
                }
                for seg in result.get("segments", [])
            ]
        }

        # Salva JSON
        with open(params.output_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)

        # Export formati aggiuntivi se richiesti
        export_formats = params.export_formats or []
        exported_files = [str(params.output_path)]

        if "srt" in export_formats:
            srt_path = params.output_path.with_suffix('.srt')
            self._export_srt(result["segments"], srt_path)
            exported_files.append(str(srt_path))

        if "vtt" in export_formats:
            vtt_path = params.output_path.with_suffix('.vtt')
            self._export_vtt(result["segments"], vtt_path)
            exported_files.append(str(vtt_path))

        if "txt" in export_formats:
            txt_path = params.output_path.with_suffix('.txt')
            self._export_txt(result["text"], txt_path)
            exported_files.append(str(txt_path))

        return {
            "text": result["text"],
            "language": result.get("language"),
            "segments_count": len(result.get("segments", [])),
            "output_path": str(params.output_path),
            "exported_files": exported_files,
            "duration_seconds": result.get("segments", [])[-1]["end"] if result.get("segments") else 0
        }

    def _export_srt(self, segments: List[Dict], output_path: Path):
        """Export formato SRT (sottotitoli)"""
        with open(output_path, 'w', encoding='utf-8') as f:
            for i, seg in enumerate(segments, 1):
                start = self._format_timestamp_srt(seg["start"])
                end = self._format_timestamp_srt(seg["end"])
                f.write(f"{i}\n")
                f.write(f"{start} --> {end}\n")
                f.write(f"{seg['text'].strip()}\n\n")

    def _export_vtt(self, segments: List[Dict], output_path: Path):
        """Export formato WebVTT"""
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("WEBVTT\n\n")
            for seg in segments:
                start = self._format_timestamp_vtt(seg["start"])
                end = self._format_timestamp_vtt(seg["end"])
                f.write(f"{start} --> {end}\n")
                f.write(f"{seg['text'].strip()}\n\n")

    def _export_txt(self, text: str, output_path: Path):
        """Export testo semplice"""
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(text)

    def _format_timestamp_srt(self, seconds: float) -> str:
        """Formatta timestamp per SRT (00:00:00,000)"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

    def _format_timestamp_vtt(self, seconds: float) -> str:
        """Formatta timestamp per VTT (00:00:00.000)"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"
