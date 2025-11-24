"""
Screen recorder multi-platform per AI Video Maker
Supporta: schermo intero, finestra, audio sistema
"""

import cv2
import numpy as np
import pyautogui
import subprocess
import tempfile
import threading
import queue
import time
import platform
from pathlib import Path
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class ScreenRecorder:
    """Registratore schermo cross-platform"""

    def __init__(self, output_path: str, fps: int = 30, audio_source: str = "system"):
        self.output_path = output_path
        self.fps = fps
        self.audio_source = audio_source
        self.is_recording = False
        self.video_thread = None
        self.audio_process = None
        self.temp_video_path = None
        self.temp_audio_path = None
        self.frame_queue = queue.Queue(maxsize=60)
        self.system = platform.system()

    def start_recording(self, region=None):
        """
        Avvia registrazione

        Args:
            region: (x, y, width, height) o None per schermo intero
        """
        if self.is_recording:
            logger.warning("Registrazione già in corso")
            return False

        try:
            # Setup temporanei
            temp_dir = Path(tempfile.gettempdir())
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.temp_video_path = temp_dir / f"screen_{timestamp}.mp4"
            self.temp_audio_path = temp_dir / f"audio_{timestamp}.wav"

            # Determina dimensioni
            if region:
                self.region = region
                width, height = region[2], region[3]
            else:
                screen_size = pyautogui.size()
                width, height = screen_size.width, screen_size.height
                self.region = (0, 0, width, height)

            logger.info(f"Avvio recording: {width}x{height} @ {self.fps}fps")

            # Avvia cattura video
            self.is_recording = True
            self.video_thread = threading.Thread(target=self._video_capture_loop)
            self.video_thread.start()

            # Avvia cattura audio se richiesto
            if self.audio_source != "none":
                self._start_audio_capture()

            return True

        except Exception as e:
            logger.error(f"Errore avvio recording: {e}")
            self.is_recording = False
            return False

    def stop_recording(self):
        """Ferma registrazione e salva file"""
        if not self.is_recording:
            logger.warning("Nessuna registrazione in corso")
            return False

        try:
            logger.info("Stopping recording...")
            self.is_recording = False

            # Attendi thread video
            if self.video_thread:
                self.video_thread.join(timeout=5)

            # Ferma audio
            if self.audio_process:
                self._stop_audio_capture()

            # Combina video + audio
            if self.audio_source != "none" and self.temp_audio_path.exists():
                success = self._merge_video_audio()
            else:
                # Solo video, rinomina
                import shutil
                shutil.move(str(self.temp_video_path), self.output_path)
                success = True

            # Cleanup
            self._cleanup_temp_files()

            logger.info(f"Recording salvato: {self.output_path}")
            return success

        except Exception as e:
            logger.error(f"Errore stop recording: {e}")
            return False

    def _video_capture_loop(self):
        """Loop cattura frame (thread separato)"""
        try:
            x, y, width, height = self.region

            # Setup video writer
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(
                str(self.temp_video_path),
                fourcc,
                self.fps,
                (width, height)
            )

            if not out.isOpened():
                logger.error("Impossibile creare video writer")
                return

            frame_time = 1.0 / self.fps
            frame_count = 0

            logger.info("Cattura video avviata")

            while self.is_recording:
                start_time = time.time()

                try:
                    # Cattura screenshot
                    screenshot = pyautogui.screenshot(region=(x, y, width, height))

                    # Converti PIL -> numpy -> BGR
                    frame = np.array(screenshot)
                    frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)

                    # Scrivi frame
                    out.write(frame)
                    frame_count += 1

                    # Mantieni framerate
                    elapsed = time.time() - start_time
                    sleep_time = max(0, frame_time - elapsed)
                    if sleep_time > 0:
                        time.sleep(sleep_time)

                    # Log ogni 100 frame
                    if frame_count % 100 == 0:
                        actual_fps = 1.0 / (time.time() - start_time + sleep_time)
                        logger.debug(f"Frame {frame_count}, FPS: {actual_fps:.1f}")

                except Exception as e:
                    logger.error(f"Errore cattura frame: {e}")
                    continue

            out.release()
            logger.info(f"Cattura video completata: {frame_count} frame")

        except Exception as e:
            logger.error(f"Errore video capture loop: {e}")

    def _start_audio_capture(self):
        """Avvia cattura audio (platform-specific)"""
        try:
            if self.system == "Darwin":  # macOS
                # ffmpeg con avfoundation
                cmd = [
                    'ffmpeg', '-f', 'avfoundation',
                    '-i', ':1',  # :1 = audio device di sistema
                    '-ac', '2',  # stereo
                    '-ar', '44100',  # 44.1kHz
                    str(self.temp_audio_path)
                ]
            elif self.system == "Linux":
                # ffmpeg con pulseaudio
                cmd = [
                    'ffmpeg', '-f', 'pulse',
                    '-i', 'default',
                    '-ac', '2',
                    '-ar', '44100',
                    str(self.temp_audio_path)
                ]
            elif self.system == "Windows":
                # ffmpeg con dshow
                cmd = [
                    'ffmpeg', '-f', 'dshow',
                    '-i', 'audio="Stereo Mix"',
                    '-ac', '2',
                    '-ar', '44100',
                    str(self.temp_audio_path)
                ]
            else:
                logger.warning(f"Sistema {self.system} non supportato per audio")
                return

            self.audio_process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            logger.info("Cattura audio avviata")

        except Exception as e:
            logger.error(f"Errore avvio cattura audio: {e}")

    def _stop_audio_capture(self):
        """Ferma cattura audio"""
        try:
            if self.audio_process:
                self.audio_process.terminate()
                self.audio_process.wait(timeout=3)
                logger.info("Cattura audio fermata")
        except Exception as e:
            logger.error(f"Errore stop audio: {e}")

    def _merge_video_audio(self):
        """Combina video e audio con ffmpeg"""
        try:
            cmd = [
                'ffmpeg', '-y',
                '-i', str(self.temp_video_path),
                '-i', str(self.temp_audio_path),
                '-c:v', 'copy',
                '-c:a', 'aac',
                '-b:a', '128k',
                '-shortest',
                self.output_path
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode == 0:
                logger.info("Video e audio combinati con successo")
                return True
            else:
                logger.error(f"Errore merge ffmpeg: {result.stderr}")
                # Fallback: salva solo video
                import shutil
                shutil.move(str(self.temp_video_path), self.output_path)
                return True

        except Exception as e:
            logger.error(f"Errore merge video/audio: {e}")
            return False

    def _cleanup_temp_files(self):
        """Rimuove file temporanei"""
        try:
            if self.temp_video_path and self.temp_video_path.exists():
                self.temp_video_path.unlink()
            if self.temp_audio_path and self.temp_audio_path.exists():
                self.temp_audio_path.unlink()
        except Exception as e:
            logger.error(f"Errore cleanup: {e}")


def get_available_windows():
    """
    Elenca finestre disponibili per cattura

    Returns:
        List[dict]: Lista finestre con {title, pid, bounds}
    """
    system = platform.system()
    windows = []

    try:
        if system == "Darwin":  # macOS
            # Usa AppleScript per elencare finestre
            script = '''
            tell application "System Events"
                set windowList to {}
                repeat with proc in application processes
                    repeat with win in windows of proc
                        set end of windowList to {name of proc, name of win}
                    end repeat
                end repeat
                return windowList
            end tell
            '''
            result = subprocess.run(
                ['osascript', '-e', script],
                capture_output=True,
                text=True
            )

            # Parse output
            lines = result.stdout.strip().split(', ')
            for i in range(0, len(lines), 2):
                if i+1 < len(lines):
                    windows.append({
                        'app': lines[i],
                        'title': lines[i+1],
                        'bounds': None  # macOS limita accesso bounds
                    })

        elif system == "Linux":
            # Usa wmctrl
            result = subprocess.run(
                ['wmctrl', '-l'],
                capture_output=True,
                text=True
            )

            for line in result.stdout.split('\n'):
                if line:
                    parts = line.split(None, 3)
                    if len(parts) >= 4:
                        windows.append({
                            'id': parts[0],
                            'desktop': parts[1],
                            'title': parts[3],
                            'bounds': None
                        })

        elif system == "Windows":
            # Usa pywin32
            try:
                import win32gui

                def callback(hwnd, windows_list):
                    if win32gui.IsWindowVisible(hwnd):
                        title = win32gui.GetWindowText(hwnd)
                        if title:
                            rect = win32gui.GetWindowRect(hwnd)
                            windows_list.append({
                                'hwnd': hwnd,
                                'title': title,
                                'bounds': rect
                            })

                win32gui.EnumWindows(callback, windows)

            except ImportError:
                logger.warning("pywin32 non installato - impossibile elencare finestre")

    except Exception as e:
        logger.error(f"Errore enumerazione finestre: {e}")

    return windows


def get_screen_info():
    """
    Ottiene info su schermi disponibili

    Returns:
        dict: Info schermi
    """
    try:
        screen_size = pyautogui.size()

        return {
            'primary': {
                'width': screen_size.width,
                'height': screen_size.height,
                'bounds': (0, 0, screen_size.width, screen_size.height)
            },
            # Per multi-monitor serve libreria platform-specific
            'monitors': [
                {
                    'id': 0,
                    'primary': True,
                    'width': screen_size.width,
                    'height': screen_size.height
                }
            ]
        }
    except Exception as e:
        logger.error(f"Errore get screen info: {e}")
        return {}
