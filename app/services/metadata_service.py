"""
Metadata Service - Video Metadata Extraction
=============================================
Servizio indipendente per estrazione metadati da file video/audio:
- Informazioni generali (durata, dimensione, formato)
- Stream video (codec, risoluzione, fps, bitrate)
- Stream audio (codec, sample rate, canali, bitrate)
- Metadata tags (titolo, autore, copyright, etc.)

Completamente testabile, nessuna dipendenza da FastAPI.
"""

import subprocess
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass

from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class MetadataParams:
    """Parametri estrazione metadati"""
    video_path: Path
    include_streams: bool = True  # Include dettagli stream
    include_format: bool = True   # Include formato container
    include_chapters: bool = False  # Include capitoli


class MetadataService:
    """
    Servizio estrazione metadati video/audio con ffprobe.

    Estrae:
    - Formato container (MP4, AVI, MKV, etc.)
    - Codec video/audio
    - Risoluzione, FPS, bitrate
    - Durata, dimensione file
    - Tags metadata
    """

    def __init__(self, config: Optional[Any] = None):
        """Inizializza service"""
        self.config = config or settings
        self.ffprobe_path = self.config.ffprobe_path

    def extract(self, params: MetadataParams) -> Dict[str, Any]:
        """
        Estrai metadati da video/audio

        Args:
            params: Parametri estrazione

        Returns:
            Dict con metadati completi

        Raises:
            FileNotFoundError: File non trovato
            RuntimeError: Errore ffprobe
        """
        # Valida input
        if not params.video_path.exists():
            raise FileNotFoundError(f"File non trovato: {params.video_path}")

        logger.info(f"Estrazione metadati da: {params.video_path}")

        # Esegui ffprobe
        metadata = self._run_ffprobe(params.video_path)

        # Processa risultato
        result = self._process_metadata(metadata, params)

        return result

    def _run_ffprobe(self, video_path: Path) -> Dict[str, Any]:
        """
        Esegui ffprobe per estrarre metadati

        Args:
            video_path: Path video

        Returns:
            Dict con output ffprobe JSON
        """
        cmd = [
            self.ffprobe_path,
            '-v', 'quiet',
            '-print_format', 'json',
            '-show_format',
            '-show_streams',
            str(video_path)
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )

            return json.loads(result.stdout)

        except subprocess.CalledProcessError as e:
            logger.error(f"Errore ffprobe: {e.stderr}")
            raise RuntimeError(f"Errore estrazione metadati: {e.stderr}")
        except json.JSONDecodeError as e:
            logger.error(f"Errore parsing JSON ffprobe: {e}")
            raise RuntimeError(f"Output ffprobe non valido")

    def _process_metadata(
        self,
        raw_metadata: Dict[str, Any],
        params: MetadataParams
    ) -> Dict[str, Any]:
        """
        Processa metadati raw di ffprobe

        Args:
            raw_metadata: Output ffprobe
            params: Parametri

        Returns:
            Dict metadati processati
        """
        result = {
            "file_path": str(params.video_path),
            "file_name": params.video_path.name,
            "file_size_bytes": params.video_path.stat().st_size,
            "file_size_mb": round(params.video_path.stat().st_size / (1024 * 1024), 2)
        }

        # Format info
        if params.include_format and 'format' in raw_metadata:
            fmt = raw_metadata['format']
            result['format'] = {
                'container': fmt.get('format_name', 'unknown'),
                'duration_seconds': float(fmt.get('duration', 0)),
                'duration_formatted': self._format_duration(float(fmt.get('duration', 0))),
                'bitrate_kbps': int(fmt.get('bit_rate', 0)) // 1000 if fmt.get('bit_rate') else None,
                'nb_streams': int(fmt.get('nb_streams', 0)),
                'tags': fmt.get('tags', {})
            }

        # Streams info
        if params.include_streams and 'streams' in raw_metadata:
            result['streams'] = {
                'video': [],
                'audio': [],
                'subtitle': []
            }

            for stream in raw_metadata['streams']:
                codec_type = stream.get('codec_type', 'unknown')

                if codec_type == 'video':
                    result['streams']['video'].append(self._process_video_stream(stream))
                elif codec_type == 'audio':
                    result['streams']['audio'].append(self._process_audio_stream(stream))
                elif codec_type == 'subtitle':
                    result['streams']['subtitle'].append({
                        'index': stream.get('index'),
                        'codec': stream.get('codec_name'),
                        'language': stream.get('tags', {}).get('language')
                    })

        return result

    def _process_video_stream(self, stream: Dict[str, Any]) -> Dict[str, Any]:
        """Processa stream video"""
        # Calcola FPS
        fps = None
        if 'r_frame_rate' in stream:
            try:
                num, den = map(int, stream['r_frame_rate'].split('/'))
                fps = round(num / den, 2) if den > 0 else None
            except:
                pass

        return {
            'index': stream.get('index'),
            'codec': stream.get('codec_name'),
            'codec_long': stream.get('codec_long_name'),
            'profile': stream.get('profile'),
            'width': stream.get('width'),
            'height': stream.get('height'),
            'resolution': f"{stream.get('width')}x{stream.get('height')}" if stream.get('width') and stream.get('height') else None,
            'fps': fps,
            'bitrate_kbps': int(stream.get('bit_rate', 0)) // 1000 if stream.get('bit_rate') else None,
            'pix_fmt': stream.get('pix_fmt'),
            'color_space': stream.get('color_space'),
            'duration_seconds': float(stream.get('duration', 0)) if stream.get('duration') else None
        }

    def _process_audio_stream(self, stream: Dict[str, Any]) -> Dict[str, Any]:
        """Processa stream audio"""
        return {
            'index': stream.get('index'),
            'codec': stream.get('codec_name'),
            'codec_long': stream.get('codec_long_name'),
            'sample_rate': int(stream.get('sample_rate', 0)) if stream.get('sample_rate') else None,
            'channels': stream.get('channels'),
            'channel_layout': stream.get('channel_layout'),
            'bitrate_kbps': int(stream.get('bit_rate', 0)) // 1000 if stream.get('bit_rate') else None,
            'duration_seconds': float(stream.get('duration', 0)) if stream.get('duration') else None,
            'language': stream.get('tags', {}).get('language')
        }

    def _format_duration(self, seconds: float) -> str:
        """
        Formatta durata in HH:MM:SS

        Args:
            seconds: Durata in secondi

        Returns:
            Stringa formattata "HH:MM:SS"
        """
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)

        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
