"""
Screen Record Service - Screen/Window Recording
================================================
Servizio indipendente per registrazione schermo/finestra/area:
- Registrazione schermo intero
- Registrazione finestra specifica
- Registrazione area personalizzata
- Audio sistema + microfono opzionale
- Configurazione FPS, qualità, codec

Completamente testabile, nessuna dipendenza da FastAPI.
"""

import subprocess
import logging
import time
import pyautogui
from pathlib import Path
from typing import Optional, Callable, Dict, Any, Tuple
from dataclasses import dataclass
import threading

from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class ScreenRecordParams:
    """Parametri registrazione schermo"""
    output_path: Path

    # Modalità
    mode: str = "fullscreen"  # "fullscreen", "window", "area", "custom"
    window_title: Optional[str] = None  # Se mode=window
    monitor_index: Optional[int] = 0  # Indice monitor (0=primario, 1=secondario, etc.)
    area_x: Optional[int] = None  # Se mode=area o custom
    area_y: Optional[int] = None
    area_width: Optional[int] = None
    area_height: Optional[int] = None

    # Durata
    duration_seconds: Optional[int] = None  # None = illimitata (ferma manualmente)

    # Video settings
    fps: int = 30
    quality: str = "high"  # low, medium, high, ultra

    # Audio
    record_audio: bool = True
    audio_device: Optional[str] = None  # Device ID (None = default)


class ScreenRecordService:
    """
    Servizio registrazione schermo/finestra.

    Modalità:
    - fullscreen: Schermo intero
    - window: Finestra specifica (richiede window_title)
    - area: Area personalizzata (richiede area_x, area_y, area_width, area_height)
    """

    MODES = ["fullscreen", "window", "area", "custom"]
    QUALITY_PRESETS = {
        "low": {"crf": 28, "preset": "ultrafast"},
        "medium": {"crf": 23, "preset": "fast"},
        "high": {"crf": 18, "preset": "medium"},
        "ultra": {"crf": 15, "preset": "slow"}
    }

    def __init__(self, config: Optional[Any] = None):
        """Inizializza service"""
        self.config = config or settings
        self.ffmpeg_path = self.config.ffmpeg_path
        self.recording_process = None
        self.stop_event = threading.Event()

    def record(
        self,
        params: ScreenRecordParams,
        progress_callback: Optional[Callable[[int, str], bool]] = None
    ) -> Dict[str, Any]:
        """
        Registra schermo

        Args:
            params: Parametri registrazione
            progress_callback: Callback progresso

        Returns:
            Dict con risultato

        Raises:
            ValueError: Parametri non validi
            RuntimeError: Errore registrazione
        """
        # Valida input
        if params.mode not in self.MODES:
            raise ValueError(f"Modalità non valida. Disponibili: {self.MODES}")

        if params.mode == "window" and not params.window_title:
            raise ValueError("mode='window' richiede window_title")

        if params.mode == "area" and not all([
            params.area_x is not None,
            params.area_y is not None,
            params.area_width,
            params.area_height
        ]):
            raise ValueError("mode='area' richiede area_x, area_y, area_width, area_height")

        if progress_callback:
            progress_callback(0, "Preparazione registrazione...")

        # Ottieni dimensioni area registrazione
        capture_region = self._get_capture_region(params)

        if progress_callback:
            progress_callback(10, "Avvio registrazione...")

        # Avvia registrazione
        self._start_recording(params, capture_region, progress_callback)

        return {
            "output_path": str(params.output_path),
            "mode": params.mode,
            "duration_seconds": params.duration_seconds,
            "fps": params.fps,
            "capture_region": capture_region
        }

    def stop_recording(self):
        """Ferma registrazione in corso"""
        if self.recording_process:
            self.recording_process.terminate()
            self.recording_process.wait(timeout=5)
            self.recording_process = None

    def _get_capture_region(self, params: ScreenRecordParams) -> Dict[str, int]:
        """
        Ottieni regione di cattura

        Args:
            params: Parametri

        Returns:
            Dict con x, y, width, height
        """
        if params.mode == "fullscreen":
            # Schermo intero
            screen_width, screen_height = pyautogui.size()
            return {
                "x": 0,
                "y": 0,
                "width": screen_width,
                "height": screen_height
            }

        elif params.mode == "window":
            # Finestra specifica (richiede PyGetWindow)
            try:
                import pygetwindow as gw
                windows = gw.getWindowsWithTitle(params.window_title)

                if not windows:
                    raise ValueError(f"Finestra '{params.window_title}' non trovata")

                win = windows[0]
                return {
                    "x": win.left,
                    "y": win.top,
                    "width": win.width,
                    "height": win.height
                }

            except ImportError:
                raise RuntimeError("PyGetWindow non installato. Usa: pip install pygetwindow")

        elif params.mode == "area":
            # Area personalizzata
            return {
                "x": params.area_x,
                "y": params.area_y,
                "width": params.area_width,
                "height": params.area_height
            }

        elif params.mode == "custom":
            # Modalità custom: monitor specifico + eventuale area
            # Se ha area personalizzata, usa quella
            if params.area_x is not None and params.area_width:
                return {
                    "x": params.area_x,
                    "y": params.area_y,
                    "width": params.area_width,
                    "height": params.area_height
                }
            # Altrimenti usa tutto il monitor (per ora usa dimensioni schermo primario)
            # TODO: implementare rilevamento dimensioni monitor specifico
            screen_width, screen_height = pyautogui.size()
            return {
                "x": 0,
                "y": 0,
                "width": screen_width,
                "height": screen_height
            }

    def _start_recording(
        self,
        params: ScreenRecordParams,
        capture_region: Dict[str, int],
        progress_callback: Optional[Callable[[int, str], bool]] = None
    ):
        """
        Avvia registrazione ffmpeg

        Args:
            params: Parametri
            capture_region: Regione cattura
            progress_callback: Callback
        """
        quality = self.QUALITY_PRESETS.get(params.quality, self.QUALITY_PRESETS["high"])

        # Comando ffmpeg (varia per OS)
        import platform
        system = platform.system()

        if system == "Linux":
            cmd = self._build_linux_cmd(params, capture_region, quality)
        elif system == "Darwin":  # macOS
            cmd = self._build_macos_cmd(params, capture_region, quality)
        elif system == "Windows":
            cmd = self._build_windows_cmd(params, capture_region, quality)
        else:
            raise RuntimeError(f"OS non supportato: {system}")

        # Avvia processo
        try:
            self.recording_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )

            # Se durata specificata, attendi e poi ferma
            if params.duration_seconds:
                if progress_callback:
                    start_time = time.time()
                    while time.time() - start_time < params.duration_seconds:
                        elapsed = time.time() - start_time
                        progress_pct = int((elapsed / params.duration_seconds) * 100)
                        progress_callback(progress_pct, f"Registrazione in corso ({int(elapsed)}s / {params.duration_seconds}s)")
                        time.sleep(1)

                self.stop_recording()

                if progress_callback:
                    progress_callback(100, "Registrazione completata!")

        except Exception as e:
            logger.error(f"Errore registrazione: {e}")
            raise RuntimeError(f"Impossibile avviare registrazione: {e}")

    def _build_linux_cmd(
        self,
        params: ScreenRecordParams,
        region: Dict[str, int],
        quality: Dict[str, Any]
    ) -> list:
        """Comando ffmpeg per Linux (X11/Wayland)"""
        cmd = [
            self.ffmpeg_path,
            '-f', 'x11grab',
            '-framerate', str(params.fps),
            '-video_size', f"{region['width']}x{region['height']}",
            '-i', f":0.0+{region['x']},{region['y']}"
        ]

        if params.record_audio:
            cmd.extend(['-f', 'pulse', '-i', 'default'])

        cmd.extend([
            '-c:v', 'libx264',
            '-preset', quality['preset'],
            '-crf', str(quality['crf']),
            '-y',
            str(params.output_path)
        ])

        return cmd

    def _build_macos_cmd(
        self,
        params: ScreenRecordParams,
        region: Dict[str, int],
        quality: Dict[str, Any]
    ) -> list:
        """Comando ffmpeg per macOS (AVFoundation)"""
        cmd = [
            self.ffmpeg_path,
            '-f', 'avfoundation',
            '-capture_cursor', '1',
            '-framerate', str(params.fps)
        ]

        # Video + audio su macOS
        if params.record_audio:
            cmd.extend(['-i', '1:0'])  # Screen:Audio
        else:
            cmd.extend(['-i', '1'])  # Solo screen

        # Crop se non fullscreen
        if params.mode != "fullscreen":
            cmd.extend([
                '-filter:v', f"crop={region['width']}:{region['height']}:{region['x']}:{region['y']}"
            ])

        cmd.extend([
            '-c:v', 'libx264',
            '-preset', quality['preset'],
            '-crf', str(quality['crf']),
            '-y',
            str(params.output_path)
        ])

        return cmd

    def _build_windows_cmd(
        self,
        params: ScreenRecordParams,
        region: Dict[str, int],
        quality: Dict[str, Any]
    ) -> list:
        """Comando ffmpeg per Windows (GDI/DirectShow)"""
        cmd = [
            self.ffmpeg_path,
            '-f', 'gdigrab',
            '-framerate', str(params.fps),
            '-offset_x', str(region['x']),
            '-offset_y', str(region['y']),
            '-video_size', f"{region['width']}x{region['height']}",
            '-i', 'desktop'
        ]

        if params.record_audio:
            cmd.extend(['-f', 'dshow', '-i', 'audio="Stereo Mix"'])

        cmd.extend([
            '-c:v', 'libx264',
            '-preset', quality['preset'],
            '-crf', str(quality['crf']),
            '-y',
            str(params.output_path)
        ])

        return cmd
