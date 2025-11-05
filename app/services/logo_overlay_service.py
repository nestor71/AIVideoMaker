"""
Logo Overlay Service - Video Logo/Watermark Overlay
====================================================
Servizio indipendente per sovrapposizione logo/watermark su video:
- Posizionamento configurabile (angoli, centro, custom)
- Ridimensionamento automatico logo
- Opacità regolabile
- Durata overlay (sempre, tempo specifico)
- Supporto formati immagine (PNG con trasparenza, JPG, etc.)

Completamente testabile, nessuna dipendenza da FastAPI.
"""

import subprocess
import logging
from pathlib import Path
from typing import Optional, Callable, Dict, Any, Tuple
from dataclasses import dataclass

from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class LogoOverlayParams:
    """Parametri sovrapposizione logo"""
    video_path: Path
    logo_path: Path
    output_path: Path

    # Posizionamento
    position: str = "bottom-right"  # top-left, top-right, bottom-left, bottom-right, center, custom
    custom_x: Optional[int] = None  # Se position=custom
    custom_y: Optional[int] = None  # Se position=custom
    margin: int = 20  # Margine dai bordi (pixel)

    # Dimensioni logo
    logo_scale: float = 0.15  # Scala rispetto a larghezza video (0.0-1.0)
    logo_width: Optional[int] = None  # Larghezza fissa (ignora scale)
    logo_height: Optional[int] = None  # Altezza fissa (ignora scale)

    # Opacità
    opacity: float = 1.0  # 0.0 (trasparente) - 1.0 (opaco)

    # Timing
    start_time: Optional[float] = None  # Secondi (None = dall'inizio)
    end_time: Optional[float] = None  # Secondi (None = fino alla fine)


class LogoOverlayService:
    """
    Servizio sovrapposizione logo/watermark su video.

    Posizioni disponibili:
    - top-left, top-right, bottom-left, bottom-right
    - center
    - custom (con custom_x, custom_y)
    """

    POSITIONS = ["top-left", "top-right", "bottom-left", "bottom-right", "center", "custom"]

    def __init__(self, config: Optional[Any] = None):
        """Inizializza service"""
        self.config = config or settings
        self.ffmpeg_path = self.config.ffmpeg_path

    def overlay(
        self,
        params: LogoOverlayParams,
        progress_callback: Optional[Callable[[int, str], bool]] = None
    ) -> Dict[str, Any]:
        """
        Sovrapponi logo su video

        Args:
            params: Parametri overlay
            progress_callback: Callback progresso

        Returns:
            Dict con risultato

        Raises:
            FileNotFoundError: File non trovato
            ValueError: Parametri non validi
            RuntimeError: Errore elaborazione
        """
        # Valida input
        if not params.video_path.exists():
            raise FileNotFoundError(f"Video non trovato: {params.video_path}")

        if not params.logo_path.exists():
            raise FileNotFoundError(f"Logo non trovato: {params.logo_path}")

        if params.position not in self.POSITIONS:
            raise ValueError(f"Posizione non valida. Disponibili: {self.POSITIONS}")

        if params.position == "custom" and (params.custom_x is None or params.custom_y is None):
            raise ValueError("position='custom' richiede custom_x e custom_y")

        if progress_callback:
            progress_callback(0, "Calcolo posizione logo...")

        # Calcola posizione
        overlay_filter = self._build_overlay_filter(params)

        if progress_callback:
            progress_callback(20, "Applicazione logo al video...")

        # Esegui ffmpeg
        self._run_ffmpeg(params, overlay_filter, progress_callback)

        if progress_callback:
            progress_callback(100, "Logo applicato con successo!")

        return {
            "output_path": str(params.output_path),
            "logo_path": str(params.logo_path),
            "position": params.position,
            "opacity": params.opacity
        }

    def _build_overlay_filter(self, params: LogoOverlayParams) -> str:
        """
        Costruisci filtro ffmpeg per overlay

        Args:
            params: Parametri

        Returns:
            Stringa filtro ffmpeg
        """
        filters = []

        # Scala logo se necessario
        if params.logo_width and params.logo_height:
            filters.append(f"[1:v]scale={params.logo_width}:{params.logo_height}[logo]")
        elif params.logo_scale:
            # Scala proporzionale alla larghezza video
            filters.append(f"[1:v]scale=iw*{params.logo_scale}:-1[logo]")
        else:
            filters.append("[1:v]copy[logo]")

        # Opacità
        if params.opacity < 1.0:
            filters.append(f"[logo]format=rgba,colorchannelmixer=aa={params.opacity}[logo_alpha]")
            logo_stream = "logo_alpha"
        else:
            logo_stream = "logo"

        # Posizione
        x, y = self._calculate_position(params)

        # Timing
        if params.start_time is not None or params.end_time is not None:
            enable_filter = []
            if params.start_time is not None:
                enable_filter.append(f"gte(t,{params.start_time})")
            if params.end_time is not None:
                enable_filter.append(f"lte(t,{params.end_time})")

            enable_expr = "*".join(enable_filter)
            overlay_part = f"[0:v][{logo_stream}]overlay={x}:{y}:enable='{enable_expr}'[out]"
        else:
            overlay_part = f"[0:v][{logo_stream}]overlay={x}:{y}[out]"

        filters.append(overlay_part)

        return ";".join(filters)

    def _calculate_position(self, params: LogoOverlayParams) -> Tuple[str, str]:
        """
        Calcola posizione X,Y per overlay

        Args:
            params: Parametri

        Returns:
            Tuple (x_expr, y_expr) per ffmpeg
        """
        margin = params.margin

        if params.position == "top-left":
            return (str(margin), str(margin))

        elif params.position == "top-right":
            return (f"W-w-{margin}", str(margin))

        elif params.position == "bottom-left":
            return (str(margin), f"H-h-{margin}")

        elif params.position == "bottom-right":
            return (f"W-w-{margin}", f"H-h-{margin}")

        elif params.position == "center":
            return ("(W-w)/2", "(H-h)/2")

        elif params.position == "custom":
            return (str(params.custom_x), str(params.custom_y))

        else:
            return (str(margin), str(margin))  # Default top-left

    def _run_ffmpeg(
        self,
        params: LogoOverlayParams,
        filter_complex: str,
        progress_callback: Optional[Callable[[int, str], bool]] = None
    ):
        """
        Esegui ffmpeg per overlay

        Args:
            params: Parametri
            filter_complex: Filtro complesso ffmpeg
            progress_callback: Callback progresso
        """
        cmd = [
            self.ffmpeg_path,
            '-i', str(params.video_path),
            '-i', str(params.logo_path),
            '-filter_complex', filter_complex,
            '-map', '[out]',
            '-map', '0:a?',  # Audio dal video originale (se esiste)
            '-c:a', 'copy',  # Copia audio senza ri-encoding
            '-c:v', 'libx264',
            '-preset', 'medium',
            '-crf', '23',
            '-y',
            str(params.output_path)
        ]

        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )

            # Leggi output per progresso (opzionale)
            for line in process.stderr:
                if progress_callback and "time=" in line:
                    # Parsing progresso da ffmpeg output (semplificato)
                    pass

            process.wait()

            if process.returncode != 0:
                raise RuntimeError(f"Errore ffmpeg overlay")

        except Exception as e:
            logger.error(f"Errore applicazione logo: {e}")
            raise RuntimeError(f"Impossibile applicare logo: {e}")
