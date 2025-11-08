"""
Chromakey Service - Green Screen Processing
============================================
Servizio indipendente per rimozione sfondo verde e compositing video.

Completamente testabile, nessuna dipendenza da FastAPI.
"""

import cv2
import numpy as np
import subprocess
import tempfile
import logging
from pathlib import Path
from typing import Optional, Callable, Dict, Any, Tuple
from dataclasses import dataclass

from app.core.config import settings

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
    fast_mode: bool = True
    gpu_accel: bool = False

    # Logo overlay (opzionale)
    logo_path: Optional[Path] = None
    logo_position: Optional[Tuple[int, int]] = None
    logo_scale: float = 0.1


class ChromakeyService:
    """
    Servizio chromakey processing professionale.

    Indipendente da FastAPI, completamente testabile.
    """

    def __init__(self, config: Optional[Any] = None):
        """
        Inizializza service

        Args:
            config: Configurazione (default: settings globale)
        """
        self.config = config or settings
        self.ffmpeg_path = self.config.ffmpeg_path
        self.ffprobe_path = self.config.ffprobe_path

        # Verifica FFmpeg disponibile
        self._verify_ffmpeg()

    def _verify_ffmpeg(self):
        """Verifica che FFmpeg sia installato"""
        try:
            subprocess.run(
                [self.ffmpeg_path, "-version"],
                capture_output=True,
                check=True
            )
            logger.info(f"FFmpeg trovato: {self.ffmpeg_path}")
        except (subprocess.CalledProcessError, FileNotFoundError):
            logger.error(f"FFmpeg non trovato al path: {self.ffmpeg_path}")
            raise RuntimeError(f"FFmpeg non disponibile. Installa FFmpeg o verifica path: {self.ffmpeg_path}")

    def process(
        self,
        params: ChromakeyParams,
        progress_callback: Optional[Callable[[int, str], bool]] = None
    ) -> Dict[str, Any]:
        """
        Elabora video con chromakey

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
        self._validate_params(params)

        # Update progress
        if progress_callback:
            if not progress_callback(5, "Caricamento video..."):
                raise InterruptedError("Processing cancellato dall'utente")

        try:
            # Open video captures
            fg_cap = cv2.VideoCapture(str(params.foreground_path))
            bg_cap = cv2.VideoCapture(str(params.background_path))

            if not fg_cap.isOpened():
                raise RuntimeError(f"Impossibile aprire foreground: {params.foreground_path}")
            if not bg_cap.isOpened():
                raise RuntimeError(f"Impossibile aprire background: {params.background_path}")

            # Get video properties
            video_info = self._get_video_info(fg_cap, bg_cap)
            logger.info(f"✅ Background: {video_info['bg_width']}x{video_info['bg_height']}, "
                       f"{video_info['bg_duration']:.1f}s, FPS: {video_info['bg_fps']}")
            logger.info(f"✅ Foreground: {video_info['fg_width']}x{video_info['fg_height']}, "
                       f"{video_info['fg_duration']:.1f}s, FPS: {video_info['fg_fps']}")

            if progress_callback:
                if not progress_callback(15, "Preprocessing frames..."):
                    raise InterruptedError("Processing cancellato")

            # Calculate timing
            timing = self._calculate_timing(params, video_info)
            logger.info(f"📅 Call-to-action: dal secondo {params.start_time} "
                       f"per {timing['duration']:.1f}s (frame {timing['start_frame']}-{timing['end_frame']})")

            # Load logo if provided
            logo_img = None
            if params.logo_path and params.logo_path.exists():
                logo_img = self._load_logo(params.logo_path, params.logo_scale)
                if logo_img is not None:
                    logger.info(f"✅ Logo caricato: {logo_img.shape[1]}x{logo_img.shape[0]}")

            # Process foreground frames with chromakey
            if progress_callback:
                if not progress_callback(30, "Elaborazione chromakey..."):
                    raise InterruptedError("Processing cancellato")

            fg_processed = self._process_foreground_frames(
                fg_cap,
                params,
                video_info,
                timing,
                progress_callback
            )

            logger.info(f"✅ {len(fg_processed)} frame foreground processati")

            # Composite video
            if progress_callback:
                if not progress_callback(60, "Compositing video..."):
                    raise InterruptedError("Processing cancellato")

            success = self._composite_video(
                bg_cap,
                fg_processed,
                params,
                video_info,
                timing,
                logo_img,
                progress_callback
            )

            # Cleanup
            fg_cap.release()
            bg_cap.release()

            if not success:
                raise RuntimeError("Compositing video fallito")

            logger.info("✅ Chromakey processing completato con successo")

            return {
                "success": True,
                "output_path": str(params.output_path),
                "metrics": {
                    "frames_processed": len(fg_processed),
                    "duration": video_info['bg_duration'],
                    "resolution": f"{video_info['bg_width']}x{video_info['bg_height']}",
                    "fps": video_info['bg_fps']
                }
            }

        except Exception as e:
            logger.error(f"❌ Errore chromakey processing: {e}")
            raise

    def _validate_params(self, params: ChromakeyParams):
        """Valida parametri"""
        if not params.foreground_path.exists():
            raise ValueError(f"Foreground video non trovato: {params.foreground_path}")
        if not params.background_path.exists():
            raise ValueError(f"Background video non trovato: {params.background_path}")
        if params.scale <= 0:
            raise ValueError("Scale deve essere > 0")
        if not (0.0 <= params.opacity <= 1.0):
            raise ValueError("Opacity deve essere tra 0.0 e 1.0")

    def _get_video_info(self, fg_cap, bg_cap) -> Dict[str, Any]:
        """Estrae info video"""
        return {
            'bg_fps': int(bg_cap.get(cv2.CAP_PROP_FPS)),
            'bg_width': int(bg_cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
            'bg_height': int(bg_cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
            'bg_frames': int(bg_cap.get(cv2.CAP_PROP_FRAME_COUNT)),
            'bg_duration': int(bg_cap.get(cv2.CAP_PROP_FRAME_COUNT)) / int(bg_cap.get(cv2.CAP_PROP_FPS)),
            'fg_fps': int(fg_cap.get(cv2.CAP_PROP_FPS)),
            'fg_width': int(fg_cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
            'fg_height': int(fg_cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
            'fg_frames': int(fg_cap.get(cv2.CAP_PROP_FRAME_COUNT)),
            'fg_duration': int(fg_cap.get(cv2.CAP_PROP_FRAME_COUNT)) / int(fg_cap.get(cv2.CAP_PROP_FPS)),
        }

    def _calculate_timing(self, params: ChromakeyParams, video_info: Dict) -> Dict[str, Any]:
        """Calcola timing frames"""
        start_frame = int(params.start_time * video_info['bg_fps'])
        duration = params.duration if params.duration is not None else video_info['fg_duration']
        end_frame = int((params.start_time + duration) * video_info['bg_fps'])

        return {
            'start_frame': start_frame,
            'end_frame': end_frame,
            'duration': duration
        }

    def _load_logo(self, logo_path: Path, logo_scale: float) -> Optional[np.ndarray]:
        """Carica e scala logo"""
        try:
            logo = cv2.imread(str(logo_path), cv2.IMREAD_UNCHANGED)
            if logo is None:
                return None

            # Converti a RGBA se necessario
            if logo.shape[2] == 3:
                logo = cv2.cvtColor(logo, cv2.COLOR_BGR2BGRA)

            # Scala
            h, w = logo.shape[:2]
            new_w = int(w * logo_scale)
            new_h = int(h * logo_scale)
            logo = cv2.resize(logo, (new_w, new_h))

            return logo
        except Exception as e:
            logger.error(f"Errore caricamento logo: {e}")
            return None

    def _process_foreground_frames(
        self,
        fg_cap,
        params: ChromakeyParams,
        video_info: Dict,
        timing: Dict,
        progress_callback: Optional[Callable]
    ) -> list:
        """Processa frame foreground con chromakey"""
        logger.info("🔄 Pre-processing foreground frames...")

        fg_processed = []
        fg_masks = []

        lower_green = np.array(params.lower_hsv)
        upper_green = np.array(params.upper_hsv)

        # Calculate scaled dimensions
        new_w = int(video_info['fg_width'] * params.scale)
        new_h = int(video_info['fg_height'] * params.scale)

        frame_count = 0
        total_frames = video_info['fg_frames']

        while True:
            ret, frame = fg_cap.read()
            if not ret:
                break

            # Chromakey processing
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
            mask = cv2.inRange(hsv, lower_green, upper_green)
            mask_inv = cv2.bitwise_not(mask)

            # Blur mask
            if params.blur_kernel > 0:
                mask_inv = cv2.GaussianBlur(mask_inv, (params.blur_kernel, params.blur_kernel), 0)

            # Scale frame
            frame_scaled = cv2.resize(frame, (new_w, new_h))
            mask_scaled = cv2.resize(mask_inv, (new_w, new_h))

            fg_processed.append(frame_scaled)
            fg_masks.append(mask_scaled)

            frame_count += 1

            # Progress callback
            if progress_callback and frame_count % 10 == 0:
                progress = 30 + int((frame_count / total_frames) * 25)
                if not progress_callback(progress, f"Preprocessing frame {frame_count}/{total_frames}"):
                    raise InterruptedError("Processing cancellato")

        return list(zip(fg_processed, fg_masks))

    def _composite_video(
        self,
        bg_cap,
        fg_processed: list,
        params: ChromakeyParams,
        video_info: Dict,
        timing: Dict,
        logo_img: Optional[np.ndarray],
        progress_callback: Optional[Callable]
    ) -> bool:
        """Compone video finale"""
        logger.info("🎨 Compositing video finale...")

        # Create video writer (temp file senza audio)
        temp_video = tempfile.NamedTemporaryFile(suffix='.mp4', delete=False)
        temp_video_path = temp_video.name
        temp_video.close()

        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(
            temp_video_path,
            fourcc,
            video_info['bg_fps'],
            (video_info['bg_width'], video_info['bg_height'])
        )

        frame_idx = 0
        fg_frame_idx = 0
        total_frames = video_info['bg_frames']

        while True:
            ret, bg_frame = bg_cap.read()
            if not ret:
                break

            # Composite foreground se nel timing
            if timing['start_frame'] <= frame_idx < timing['end_frame'] and fg_frame_idx < len(fg_processed):
                fg_frame, fg_mask = fg_processed[fg_frame_idx]

                # Calculate position
                x_pos, y_pos = params.position
                x = (video_info['bg_width'] - fg_frame.shape[1]) // 2 + x_pos
                y = (video_info['bg_height'] - fg_frame.shape[0]) // 2 + y_pos

                # Overlay foreground
                bg_frame = self._overlay_image(bg_frame, fg_frame, fg_mask, x, y, params.opacity)

                fg_frame_idx += 1

            # Overlay logo se presente
            if logo_img is not None and params.logo_position:
                logo_x, logo_y = params.logo_position
                bg_frame = self._overlay_logo(bg_frame, logo_img, logo_x, logo_y)

            out.write(bg_frame)
            frame_idx += 1

            # Progress
            if progress_callback and frame_idx % 10 == 0:
                progress = 60 + int((frame_idx / total_frames) * 30)
                if not progress_callback(progress, f"Compositing frame {frame_idx}/{total_frames}"):
                    out.release()
                    Path(temp_video_path).unlink()
                    raise InterruptedError("Processing cancellato")

        out.release()

        # Add audio with FFmpeg
        if progress_callback:
            progress_callback(95, "Aggiunta audio...")

        success = self._add_audio_ffmpeg(
            temp_video_path,
            params.foreground_path,
            params.background_path,
            params.output_path,
            params.audio_mode,
            timing
        )

        # Cleanup temp
        Path(temp_video_path).unlink()

        return success

    def _overlay_image(
        self,
        bg: np.ndarray,
        fg: np.ndarray,
        mask: np.ndarray,
        x: int,
        y: int,
        opacity: float
    ) -> np.ndarray:
        """Overlay immagine su background con mask e opacity"""
        h, w = fg.shape[:2]
        bg_h, bg_w = bg.shape[:2]

        # Clamp position
        if x < 0 or y < 0 or x + w > bg_w or y + h > bg_h:
            # Crop if out of bounds
            x_start = max(0, x)
            y_start = max(0, y)
            x_end = min(bg_w, x + w)
            y_end = min(bg_h, y + h)

            fg_x_start = max(0, -x)
            fg_y_start = max(0, -y)
            fg_x_end = fg_x_start + (x_end - x_start)
            fg_y_end = fg_y_start + (y_end - y_start)

            roi = bg[y_start:y_end, x_start:x_end]
            fg_crop = fg[fg_y_start:fg_y_end, fg_x_start:fg_x_end]
            mask_crop = mask[fg_y_start:fg_y_end, fg_x_start:fg_x_end]

            # Alpha blend
            mask_3ch = cv2.cvtColor(mask_crop, cv2.COLOR_GRAY2BGR) / 255.0 * opacity
            blended = (fg_crop * mask_3ch + roi * (1 - mask_3ch)).astype(np.uint8)

            bg[y_start:y_end, x_start:x_end] = blended
        else:
            roi = bg[y:y+h, x:x+w]
            mask_3ch = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR) / 255.0 * opacity
            blended = (fg * mask_3ch + roi * (1 - mask_3ch)).astype(np.uint8)
            bg[y:y+h, x:x+w] = blended

        return bg

    def _overlay_logo(self, bg: np.ndarray, logo: np.ndarray, x: int, y: int) -> np.ndarray:
        """Overlay logo con alpha channel"""
        # TODO: implementare overlay logo con alpha blending
        return bg

    def _add_audio_ffmpeg(
        self,
        video_path: str,
        fg_path: Path,
        bg_path: Path,
        output_path: Path,
        audio_mode: str,
        timing: Dict
    ) -> bool:
        """Aggiunge audio con FFmpeg secondo audio_mode"""
        try:
            if audio_mode == "none":
                # Copia video senza audio
                subprocess.run([
                    self.ffmpeg_path, '-i', video_path,
                    '-c:v', 'copy', '-an',
                    '-y', str(output_path)
                ], check=True, capture_output=True)

            elif audio_mode == "background":
                # Audio da background
                subprocess.run([
                    self.ffmpeg_path,
                    '-i', video_path,
                    '-i', str(bg_path),
                    '-c:v', 'copy',
                    '-map', '0:v:0',
                    '-map', '1:a:0',
                    '-shortest',
                    '-y', str(output_path)
                ], check=True, capture_output=True)

            elif audio_mode == "foreground":
                # Audio da foreground
                subprocess.run([
                    self.ffmpeg_path,
                    '-i', video_path,
                    '-i', str(fg_path),
                    '-c:v', 'copy',
                    '-map', '0:v:0',
                    '-map', '1:a:0',
                    '-shortest',
                    '-y', str(output_path)
                ], check=True, capture_output=True)

            elif audio_mode in ["synced", "both", "timed"]:
                # Mix audio foreground + background con amix filter
                subprocess.run([
                    self.ffmpeg_path,
                    '-i', video_path,           # 0: video senza audio
                    '-i', str(fg_path),         # 1: foreground con audio
                    '-i', str(bg_path),         # 2: background con audio
                    '-filter_complex', '[1:a][2:a]amix=inputs=2:duration=shortest:normalize=0[aout]',
                    '-map', '0:v:0',            # Video da input 0
                    '-map', '[aout]',           # Audio mixato
                    '-c:v', 'copy',             # Copia video (no re-encode)
                    '-c:a', 'aac',              # Encode audio come AAC
                    '-b:a', '192k',             # Bitrate audio 192k
                    '-shortest',                # Durata = video più corto
                    '-y', str(output_path)
                ], check=True, capture_output=True)

            logger.info(f"✅ Audio aggiunto (mode: {audio_mode})")
            return True

        except subprocess.CalledProcessError as e:
            logger.error(f"Errore FFmpeg audio: {e.stderr.decode() if e.stderr else str(e)}")
            return False
