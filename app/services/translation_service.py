"""
Translation Service - Video Translation
========================================
Servizio indipendente per traduzione video con:
- Trascrizione audio (Whisper)
- Traduzione testo (Google Translate)
- Sintesi vocale (gTTS)
- Lip-sync opzionale (ElevenLabs)

Completamente testabile, nessuna dipendenza da FastAPI.
"""

import os
import subprocess
import tempfile
import logging
from pathlib import Path
from typing import Optional, Callable, Dict, Any
from dataclasses import dataclass
import shutil

from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class TranslationParams:
    """Parametri traduzione video"""
    input_video_path: Path
    output_video_path: Path
    target_language: str
    source_language: str = "auto"
    enable_lipsync: bool = False


class TranslationService:
    """
    Servizio traduzione video professionale.

    Workflow:
    1. Estrai audio da video
    2. Trascrivi audio con Whisper
    3. Traduci testo
    4. Genera TTS
    5. Ricombina video + audio tradotto
    6. (Opzionale) Lip-sync con ElevenLabs
    """

    SUPPORTED_LANGUAGES = {
        'en': 'English',
        'es': 'Spanish',
        'fr': 'French',
        'de': 'German',
        'pt': 'Portuguese',
        'ru': 'Russian',
        'ja': 'Japanese',
        'zh-CN': 'Chinese (Simplified)',
        'ar': 'Arabic',
        'hi': 'Hindi',
        'it': 'Italian'
    }

    def __init__(self, config: Optional[Any] = None):
        """
        Inizializza service

        Args:
            config: Configurazione (default: settings globale)
        """
        self.config = config or settings
        self.ffmpeg_path = self.config.ffmpeg_path
        self.temp_dir = self.config.temp_dir

        # Lazy import di librerie pesanti
        self._whisper_model = None
        self._translator = None

        self._verify_dependencies()

    def _verify_dependencies(self):
        """Verifica dipendenze richieste"""
        try:
            subprocess.run(
                [self.ffmpeg_path, "-version"],
                capture_output=True,
                check=True
            )
        except (subprocess.CalledProcessError, FileNotFoundError):
            raise RuntimeError(f"FFmpeg non disponibile: {self.ffmpeg_path}")

        # Verifica librerie Python
        try:
            import whisper
            import deep_translator
            from gtts import gTTS
        except ImportError as e:
            raise RuntimeError(f"Dipendenze mancanti: {e}. Installa: pip install openai-whisper deep-translator gTTS")

    def translate(
        self,
        params: TranslationParams,
        progress_callback: Optional[Callable[[int, str], bool]] = None
    ) -> Dict[str, Any]:
        """
        Traduce video

        Args:
            params: Parametri traduzione
            progress_callback: Callback progresso (progress, message) -> continue

        Returns:
            dict: Risultato con 'success', 'output_path', 'transcription', 'translation'

        Raises:
            ValueError: Se parametri invalidi
            RuntimeError: Se traduzione fallisce
        """
        logger.info(f"🌍 Avvio traduzione video")
        logger.info(f"   Input: {params.input_video_path}")
        logger.info(f"   Output: {params.output_video_path}")
        logger.info(f"   Target: {params.target_language}")
        logger.info(f"   Lip-sync: {params.enable_lipsync}")

        self._validate_params(params)

        if progress_callback:
            progress_callback(5, "Inizializzazione traduzione...")

        try:
            # Se lip-sync richiesto, usa ElevenLabs
            if params.enable_lipsync:
                return self._translate_with_elevenlabs(params, progress_callback)

            # Metodo standard (più economico)
            return self._translate_standard(params, progress_callback)

        except Exception as e:
            logger.error(f"❌ Errore traduzione: {e}")
            raise

    def _validate_params(self, params: TranslationParams):
        """Valida parametri"""
        if not params.input_video_path.exists():
            raise ValueError(f"Video non trovato: {params.input_video_path}")

        if params.target_language not in self.SUPPORTED_LANGUAGES:
            raise ValueError(
                f"Lingua non supportata: {params.target_language}. "
                f"Supportate: {list(self.SUPPORTED_LANGUAGES.keys())}"
            )

    def _translate_standard(
        self,
        params: TranslationParams,
        progress_callback: Optional[Callable]
    ) -> Dict[str, Any]:
        """Traduzione standard (senza lip-sync)"""

        temp_files = []

        try:
            # STEP 1: Estrai audio
            if progress_callback:
                progress_callback(10, "Estrazione audio...")

            audio_path = self._extract_audio(params.input_video_path)
            temp_files.append(audio_path)
            logger.info(f"✅ Audio estratto: {audio_path}")

            # STEP 2: Trascrizione Whisper
            if progress_callback:
                progress_callback(30, "Trascrizione audio con Whisper AI...")

            transcription = self._transcribe_audio(audio_path, params.source_language)
            logger.info(f"✅ Trascrizione completata: {len(transcription['text'])} caratteri")

            # STEP 3: Traduzione testo
            if progress_callback:
                progress_callback(50, f"Traduzione in {self.SUPPORTED_LANGUAGES[params.target_language]}...")

            translated_text = self._translate_text(transcription['text'], params.target_language)
            logger.info(f"✅ Testo tradotto: {len(translated_text)} caratteri")

            # STEP 4: TTS
            if progress_callback:
                progress_callback(70, "Generazione audio tradotto (TTS)...")

            tts_audio_path = self._generate_tts(translated_text, params.target_language)
            temp_files.append(tts_audio_path)
            logger.info(f"✅ Audio TTS generato: {tts_audio_path}")

            # STEP 5: Combina video + audio tradotto
            if progress_callback:
                progress_callback(90, "Combinazione video con audio tradotto...")

            self._combine_video_audio(
                params.input_video_path,
                Path(tts_audio_path),
                params.output_video_path
            )

            if progress_callback:
                progress_callback(100, "✅ Traduzione completata!")

            return {
                "success": True,
                "output_path": str(params.output_video_path),
                "transcription": transcription['text'],
                "translation": translated_text,
                "method": "standard"
            }

        finally:
            # Cleanup
            for temp_file in temp_files:
                if temp_file and Path(temp_file).exists():
                    Path(temp_file).unlink()

    def _translate_with_elevenlabs(
        self,
        params: TranslationParams,
        progress_callback: Optional[Callable]
    ) -> Dict[str, Any]:
        """Traduzione con ElevenLabs (lip-sync professionale)"""

        try:
            from elevenlabs_integration import ElevenLabsClient

            if progress_callback:
                progress_callback(10, "Connessione a ElevenLabs API...")

            client = ElevenLabsClient(api_key=self.config.elevenlabs_api_key)

            if progress_callback:
                progress_callback(20, "Upload video a ElevenLabs...")

            success = client.dub_video(
                video_path=str(params.input_video_path),
                target_language=params.target_language,
                output_path=str(params.output_video_path),
                source_language=params.source_language
            )

            if not success:
                raise RuntimeError("ElevenLabs dubbing fallito")

            if progress_callback:
                progress_callback(100, "✅ Dubbing con lip-sync completato!")

            return {
                "success": True,
                "output_path": str(params.output_video_path),
                "method": "elevenlabs_lipsync"
            }

        except ImportError:
            logger.warning("ElevenLabs non disponibile, fallback a metodo standard")
            return self._translate_standard(params, progress_callback)
        except Exception as e:
            logger.error(f"Errore ElevenLabs: {e}, fallback a metodo standard")
            return self._translate_standard(params, progress_callback)

    def _extract_audio(self, video_path: Path) -> str:
        """Estrai audio da video con FFmpeg"""
        audio_path = tempfile.mktemp(suffix='.wav', dir=self.temp_dir)

        try:
            subprocess.run([
                self.ffmpeg_path,
                '-i', str(video_path),
                '-vn',  # No video
                '-acodec', 'pcm_s16le',  # WAV 16-bit
                '-ar', '16000',  # 16kHz (ottimale per Whisper)
                '-ac', '1',  # Mono
                '-y',  # Overwrite
                audio_path
            ], check=True, capture_output=True)

            return audio_path

        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Estrazione audio fallita: {e.stderr.decode() if e.stderr else str(e)}")

    def _transcribe_audio(self, audio_path: str, language: str = "auto") -> Dict[str, Any]:
        """Trascrivi audio con Whisper"""
        import whisper

        # Lazy load model
        if self._whisper_model is None:
            logger.info("Caricamento modello Whisper (base)...")
            self._whisper_model = whisper.load_model("base")

        # Transcribe
        result = self._whisper_model.transcribe(
            audio_path,
            language=None if language == "auto" else language,
            fp16=False  # CPU compatibility
        )

        return result

    def _translate_text(self, text: str, target_language: str) -> str:
        """Traduci testo con Google Translate"""
        from deep_translator import GoogleTranslator

        if self._translator is None:
            self._translator = GoogleTranslator(source='auto', target=target_language)
        else:
            self._translator.target = target_language

        # Split testo lungo in chunks (Google Translate ha limiti)
        max_length = 5000
        if len(text) <= max_length:
            return self._translator.translate(text)

        # Traduci in chunks
        chunks = [text[i:i+max_length] for i in range(0, len(text), max_length)]
        translated_chunks = [self._translator.translate(chunk) for chunk in chunks]

        return ' '.join(translated_chunks)

    def _generate_tts(self, text: str, language: str) -> str:
        """Genera audio con gTTS"""
        from gtts import gTTS

        tts_path = tempfile.mktemp(suffix='.mp3', dir=self.temp_dir)

        # Map lingua a codice gTTS
        tts_lang = language.split('-')[0]  # 'zh-CN' -> 'zh'

        tts = gTTS(text=text, lang=tts_lang, slow=False)
        tts.save(tts_path)

        return tts_path

    def _combine_video_audio(
        self,
        video_path: Path,
        audio_path: Path,
        output_path: Path
    ):
        """Combina video con nuovo audio"""
        try:
            subprocess.run([
                self.ffmpeg_path,
                '-i', str(video_path),
                '-i', str(audio_path),
                '-c:v', 'copy',  # Copia video stream senza re-encoding
                '-map', '0:v:0',  # Video da input 0
                '-map', '1:a:0',  # Audio da input 1
                '-shortest',  # Taglia al più corto
                '-y',
                str(output_path)
            ], check=True, capture_output=True)

        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Combinazione video/audio fallita: {e.stderr.decode() if e.stderr else str(e)}")

    @classmethod
    def get_supported_languages(cls) -> Dict[str, str]:
        """Ritorna lingue supportate"""
        return cls.SUPPORTED_LANGUAGES.copy()
