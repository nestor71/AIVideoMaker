"""
Chromakey Service - Green Screen Processing
============================================
Servizio indipendente per rimozione sfondo verde e compositing video.

Completamente testabile, nessuna dipendenza da FastAPI.
Usa il modulo chromakey.py ottimizzato e funzionante.
"""

import numpy as np
import logging
from pathlib import Path
from typing import Optional, Callable, Dict, Any, Tuple
from dataclasses import dataclass

from app.core.config import settings
# Importa la funzione chromakey ottimizzata
from chromakey import remove_background_and_overlay_timed

logger = logging.getLogger(__name__)


@dataclass
class ChromakeyParams:
    """Parametri chromakey processing"""
    # Video files
    foreground_path: Path
    background_path: Path
    output_path: Path

    # Timing
    start_time: float = 0.0
    duration: Optional[float] = None

    # Chromakey HSV ranges
    lower_hsv: Tuple[int, int, int] = (40, 40, 40)
    upper_hsv: Tuple[int, int, int] = (80, 255, 255)
    blur_kernel: int = 5

    # Audio
    audio_mode: str = "synced"  # background, foreground, both, timed, synced, none

    # Position & scale
    position: Tuple[int, int] = (0, 0)
    scale: float = 1.0
    opacity: float = 1.0

    # Performance
    fast_mode: bool = False  # Default False per usare algoritmo avanzato
    gpu_accel: bool = False

    # Logo overlay (opzionale)
    logo_path: Optional[Path] = None
    logo_position: Optional[Tuple[int, int]] = None
    logo_scale: float = 0.1


class ChromakeyService:
    """
    Servizio chromakey processing professionale.

    Indipendente da FastAPI, completamente testabile.
    Usa il modulo chromakey.py ottimizzato.
    """

    def __init__(self, config: Optional[Any] = None):
        """
        Inizializza service

        Args:
            config: Configurazione (default: settings globale)
        """
        self.config = config or settings
        logger.info("ChromakeyService inizializzato con chromakey.py ottimizzato")

    def process(
        self,
        params: ChromakeyParams,
        progress_callback: Optional[Callable[[int, str], bool]] = None
    ) -> Dict[str, Any]:
        """
        Elabora video con chromakey usando il modulo chromakey.py ottimizzato

        Args:
            params: Parametri chromakey
            progress_callback: Callback progresso (progress, message) -> continue

        Returns:
            dict: Risultato processing con chiave 'output_path', 'success', 'metrics'

        Raises:
            ValueError: Se parametri invalidi
            RuntimeError: Se elaborazione fallisce
        """
        logger.info(f"🎬 Avvio chromakey processing")
        logger.info(f"   Foreground: {params.foreground_path}")
        logger.info(f"   Background: {params.background_path}")
        logger.info(f"   Output: {params.output_path}")
        logger.info(f"   Fast mode: {params.fast_mode}, GPU: {params.gpu_accel}")

        # Validazione
        if not params.foreground_path.exists():
            raise ValueError(f"Foreground video non trovato: {params.foreground_path}")
        if not params.background_path.exists():
            raise ValueError(f"Background video non trovato: {params.background_path}")
        if params.scale <= 0:
            raise ValueError("Scale deve essere > 0")
        if not (0.0 <= params.opacity <= 1.0):
            raise ValueError("Opacity deve essere tra 0.0 e 1.0")

        # Prepara parametri per chromakey.py
        lower_green = np.array(params.lower_hsv)
        upper_green = np.array(params.upper_hsv)

        # Callback wrapper per convertire formato
        def chromakey_progress_callback(progress):
            """Wrapper per convertire callback da chromakey.py a formato service"""
            if progress_callback is None:
                return True

            # Converti None a messaggio generico
            if progress is None:
                return progress_callback(0, "Elaborazione in corso...")

            # Mappa il progresso da chromakey.py
            message = "Elaborazione chromakey..."
            if progress < 30:
                message = "Pre-processing frames..."
            elif progress < 95:
                message = "Compositing video..."
            else:
                message = "Finalizzazione audio..."

            return progress_callback(int(progress), message)

        try:
            # Crea directory output se non esiste
            params.output_path.parent.mkdir(parents=True, exist_ok=True)

            # Esegui chromakey usando la funzione ottimizzata
            success = remove_background_and_overlay_timed(
                foreground_video=str(params.foreground_path),
                background_video=str(params.background_path),
                output_video=str(params.output_path),
                start_time=params.start_time,
                duration=params.duration,
                lower_green=lower_green,
                upper_green=upper_green,
                blur_kernel=params.blur_kernel,
                audio_source=params.audio_mode,
                position=params.position,
                scale=params.scale,
                opacity=params.opacity,
                fast_mode=params.fast_mode,
                gpu_accel=params.gpu_accel,
                logo_path=str(params.logo_path) if params.logo_path else None,
                logo_position=params.logo_position,
                logo_scale=params.logo_scale,
                progress_callback=chromakey_progress_callback
            )

            if not success:
                raise RuntimeError("Chromakey processing fallito")

            logger.info("✅ Chromakey processing completato con successo")

            # Calcola metriche output
            output_size = params.output_path.stat().st_size if params.output_path.exists() else 0

            return {
                "success": True,
                "output_path": str(params.output_path),
                "metrics": {
                    "output_size_mb": round(output_size / (1024 * 1024), 2),
                    "fast_mode": params.fast_mode,
                    "audio_mode": params.audio_mode
                }
            }

        except Exception as e:
            logger.error(f"❌ Errore chromakey processing: {e}")
            raise
