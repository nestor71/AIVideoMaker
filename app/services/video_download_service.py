"""
Video Download Service - Download video dal web
================================================
Servizio per scaricare video da YouTube, TikTok, Vimeo, Twitter, Instagram, ecc.
Usa yt-dlp (fork attivo di youtube-dl).

Piattaforme supportate:
- YouTube
- TikTok
- Vimeo
- Twitter/X
- Facebook
- Instagram
- Dailymotion
- E 1000+ altri siti
"""

from __future__ import annotations
import logging
import subprocess
from pathlib import Path
from typing import Optional, Callable, Dict, Any
from dataclasses import dataclass
from datetime import datetime

from app.core.config import settings

logger = logging.getLogger(__name__)

# Verifica disponibilità yt-dlp
try:
    import yt_dlp
    YT_DLP_AVAILABLE = True
except ImportError:
    yt_dlp = None
    YT_DLP_AVAILABLE = False


@dataclass
class VideoDownloadParams:
    """Parametri download video"""
    url: str  # URL video
    output_path: Path  # Dove salvare il video

    # Opzioni qualità
    quality: str = "best"  # "best", "worst", "720p", "1080p", "4k"
    format_preference: str = "mp4"  # "mp4", "webm", "mkv", "any"

    # Opzioni audio
    extract_audio: bool = False  # Scarica solo audio
    audio_format: str = "mp3"  # "mp3", "m4a", "wav", "opus"

    # Opzioni metadata
    embed_thumbnail: bool = True  # Aggiungi thumbnail nel video
    embed_metadata: bool = True  # Aggiungi metadata
    embed_subtitles: bool = False  # Aggiungi sottotitoli

    # Opzioni avanzate
    max_filesize: Optional[int] = None  # Max dimensione in MB (None = nessun limite)
    age_limit: Optional[int] = None  # Limita età contenuto


class VideoDownloadService:
    """
    Servizio download video da web.

    Supporta YouTube, TikTok, Vimeo, Twitter, Instagram e 1000+ siti.
    """

    def __init__(self, config: Optional[Any] = None):
        """Inizializza service"""
        self.config = config or settings
        self.output_dir = Path(self.config.output_dir) if hasattr(self.config, 'output_dir') else Path('./output')
        self.output_dir.mkdir(parents=True, exist_ok=True)

        if not YT_DLP_AVAILABLE:
            logger.warning("⚠️ yt-dlp non disponibile. Installa con: pip install yt-dlp")

    def download(
        self,
        params: VideoDownloadParams,
        progress_callback: Optional[Callable[[int, str], bool]] = None
    ) -> Dict[str, Any]:
        """
        Scarica video da URL

        Args:
            params: Parametri download
            progress_callback: Callback progresso (progress_pct, message) -> continue?

        Returns:
            dict: Risultato con path video scaricato

        Raises:
            RuntimeError: Se yt-dlp non disponibile o download fallisce
        """

        if not YT_DLP_AVAILABLE:
            raise RuntimeError(
                "yt-dlp non installato. Installa con: pip install yt-dlp"
            )

        logger.info(f"🌐 Inizio download video da: {params.url}")

        try:
            # Callback progresso per yt-dlp
            def progress_hook(d):
                if progress_callback is None:
                    return

                if d['status'] == 'downloading':
                    # Estrai percentuale
                    percent_str = d.get('_percent_str', '0%').replace('%', '').strip()
                    try:
                        progress = int(float(percent_str))
                    except:
                        progress = 0

                    downloaded = d.get('downloaded_bytes', 0)
                    total = d.get('total_bytes', 0) or d.get('total_bytes_estimate', 0)

                    if total > 0:
                        size_mb = total / 1024 / 1024
                        downloaded_mb = downloaded / 1024 / 1024
                        message = f"Download: {downloaded_mb:.1f}/{size_mb:.1f} MB ({progress}%)"
                    else:
                        message = f"Download in corso... {progress}%"

                    # Chiama callback
                    should_continue = progress_callback(progress, message)
                    if not should_continue:
                        raise RuntimeError("Download cancellato dall'utente")

                elif d['status'] == 'finished':
                    if progress_callback:
                        progress_callback(100, "Download completato, elaborazione finale...")

            # Costruisci opzioni yt-dlp
            ydl_opts = self._build_yt_dlp_options(params)
            ydl_opts['progress_hooks'] = [progress_hook]

            # Download con yt-dlp
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Estrai info video
                info = ydl.extract_info(params.url, download=True)

                # Path file scaricato
                if params.extract_audio:
                    filename = ydl.prepare_filename(info).replace('.webm', f'.{params.audio_format}').replace('.m4a', f'.{params.audio_format}')
                else:
                    filename = ydl.prepare_filename(info)

                downloaded_path = Path(filename)

                # Sposta in output_path se diverso
                if downloaded_path != params.output_path:
                    params.output_path.parent.mkdir(parents=True, exist_ok=True)
                    downloaded_path.rename(params.output_path)
                    final_path = params.output_path
                else:
                    final_path = downloaded_path

                logger.info(f"✅ Download completato: {final_path}")

                return {
                    "success": True,
                    "output_path": str(final_path),
                    "title": info.get('title', 'Unknown'),
                    "duration": info.get('duration', 0),
                    "uploader": info.get('uploader', 'Unknown'),
                    "upload_date": info.get('upload_date', 'Unknown'),
                    "view_count": info.get('view_count', 0),
                    "like_count": info.get('like_count', 0),
                    "description": info.get('description', ''),
                    "thumbnail": info.get('thumbnail', ''),
                    "filesize": final_path.stat().st_size,
                    "url": params.url
                }

        except Exception as e:
            logger.error(f"❌ Errore download: {e}")
            raise RuntimeError(f"Impossibile scaricare video: {e}")

    def _build_yt_dlp_options(self, params: VideoDownloadParams) -> Dict[str, Any]:
        """Costruisce opzioni yt-dlp"""

        opts = {
            'outtmpl': str(params.output_path.with_suffix('')) + '.%(ext)s',
            'quiet': False,
            'no_warnings': False,
        }

        # Qualità video
        if params.extract_audio:
            opts['format'] = 'bestaudio/best'
            opts['postprocessors'] = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': params.audio_format,
                'preferredquality': '192',
            }]
        else:
            # Formato video
            if params.quality == "best":
                if params.format_preference == "mp4":
                    opts['format'] = 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'
                else:
                    opts['format'] = 'bestvideo+bestaudio/best'
            elif params.quality == "worst":
                opts['format'] = 'worst'
            elif params.quality in ["720p", "1080p", "4k"]:
                height = {"720p": 720, "1080p": 1080, "4k": 2160}[params.quality]
                if params.format_preference == "mp4":
                    opts['format'] = f'bestvideo[height<={height}][ext=mp4]+bestaudio[ext=m4a]/best[height<={height}]'
                else:
                    opts['format'] = f'bestvideo[height<={height}]+bestaudio/best[height<={height}]'

            # Merge video+audio se necessario
            opts['merge_output_format'] = params.format_preference if params.format_preference != "any" else "mp4"

        # Metadata
        if params.embed_thumbnail:
            opts['writethumbnail'] = True
            opts['postprocessors'] = opts.get('postprocessors', []) + [{
                'key': 'EmbedThumbnail',
            }]

        if params.embed_subtitles:
            opts['writesubtitles'] = True
            opts['writeautomaticsub'] = True
            opts['subtitleslangs'] = ['en', 'it']
            opts['postprocessors'] = opts.get('postprocessors', []) + [{
                'key': 'FFmpegEmbedSubtitle',
            }]

        # Limiti
        if params.max_filesize:
            opts['max_filesize'] = params.max_filesize * 1024 * 1024  # MB to bytes

        if params.age_limit:
            opts['age_limit'] = params.age_limit

        return opts

    def get_video_info(self, url: str) -> Dict[str, Any]:
        """
        Ottieni informazioni video senza scaricare

        Args:
            url: URL video

        Returns:
            dict: Info video (titolo, durata, uploader, ecc.)
        """

        if not YT_DLP_AVAILABLE:
            raise RuntimeError("yt-dlp non installato")

        try:
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)

                return {
                    "title": info.get('title', 'Unknown'),
                    "duration": info.get('duration', 0),
                    "uploader": info.get('uploader', 'Unknown'),
                    "upload_date": info.get('upload_date', 'Unknown'),
                    "view_count": info.get('view_count', 0),
                    "like_count": info.get('like_count', 0),
                    "description": info.get('description', ''),
                    "thumbnail": info.get('thumbnail', ''),
                    "formats_available": len(info.get('formats', [])),
                    "url": url,
                    "extractor": info.get('extractor', 'Unknown'),
                    "webpage_url": info.get('webpage_url', url)
                }
        except Exception as e:
            logger.error(f"❌ Errore get_video_info: {e}")
            raise RuntimeError(f"Impossibile ottenere info video: {e}")
