"""
Multi-Layer Video Compositor Service
Supporta sovrapposizione illimitata di video, immagini e audio con:
- Dimensioni percentuali (5-100% del video principale)
- Posizionamento XY preciso
- Opacità per layer
- Chromakey green screen removal
- Timing per layer (start time)
"""

import logging
import subprocess
import os
import signal
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)

class CompositorService:
    """Servizio per compositing multi-layer video"""

    def __init__(self):
        self.output_dir = Path("output")
        self.output_dir.mkdir(exist_ok=True)
        # Traccia processi FFmpeg attivi per job_id
        self.active_jobs = {}  # {job_id: subprocess.Popen}

    def check_ffmpeg(self) -> bool:
        """Verifica disponibilità FFmpeg"""
        try:
            result = subprocess.run(
                ['ffmpeg', '-version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except Exception as e:
            logger.error(f"FFmpeg non disponibile: {e}")
            return False

    def cancel_job(self, job_id: str) -> bool:
        """
        Cancella job FFmpeg in esecuzione

        Args:
            job_id: ID del job da cancellare

        Returns:
            True se il processo è stato killato, False se non trovato
        """
        process = self.active_jobs.get(job_id)
        if not process:
            logger.warning(f"⚠️ Processo FFmpeg per job {job_id} non trovato (già completato o non esistente)")
            return False

        try:
            logger.info(f"🛑 Killing processo FFmpeg per job {job_id} (PID: {process.pid})")
            process.kill()  # SIGKILL
            process.wait(timeout=5)  # Aspetta che termini
            logger.info(f"✅ Processo FFmpeg killato con successo")
            return True
        except subprocess.TimeoutExpired:
            logger.error(f"❌ Timeout killing processo FFmpeg (PID: {process.pid})")
            # Force kill
            try:
                import signal
                os.kill(process.pid, signal.SIGKILL)
            except:
                pass
            return False
        except Exception as e:
            logger.error(f"❌ Errore killing processo FFmpeg: {e}")
            return False
        finally:
            # Rimuovi dalla lista anche in caso di errore
            if job_id in self.active_jobs:
                del self.active_jobs[job_id]

    def get_video_info(self, video_path: str) -> Dict[str, Any]:
        """Ottieni informazioni video usando ffprobe"""
        try:
            cmd = [
                'ffprobe',
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                '-show_streams',
                video_path
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode != 0:
                raise Exception(f"ffprobe error: {result.stderr}")

            data = json.loads(result.stdout)

            # Trova stream video
            video_stream = next(
                (s for s in data['streams'] if s['codec_type'] == 'video'),
                None
            )

            if not video_stream:
                raise Exception("Nessuno stream video trovato")

            # Estrai info
            width = int(video_stream.get('width', 0))
            height = int(video_stream.get('height', 0))

            # FPS
            fps_str = video_stream.get('r_frame_rate', '30/1')
            fps_parts = fps_str.split('/')
            fps = int(fps_parts[0]) / int(fps_parts[1]) if len(fps_parts) == 2 else 30

            # Durata
            duration = float(data['format'].get('duration', 0))

            return {
                'width': width,
                'height': height,
                'fps': fps,
                'duration': duration
            }

        except Exception as e:
            logger.error(f"Errore get_video_info: {e}")
            raise

    def build_filter_complex(
        self,
        main_video_info: Dict[str, Any],
        layers: List[Dict[str, Any]],
        target_duration: Optional[float] = None
    ) -> str:
        """
        Costruisce il filtro FFmpeg per overlay multipli

        Args:
            main_video_info: Info del video principale (width, height, fps, duration)
            layers: Lista di layer, ognuno con:
                - type: 'video' | 'image' | 'audio'
                - path: percorso file
                - posX: posizione X in pixel (dal centro)
                - posY: posizione Y in pixel (dal centro)
                - scale: dimensione in percentuale (5-100)
                - opacity: opacità 0-1
                - chromakey: bool, rimuovi sfondo verde
                - threshold: soglia chromakey (0-255)
                - tolerance: tolleranza chromakey (0-255)
                - startTime: tempo inizio in secondi

        Returns:
            Filter complex string per FFmpeg
        """

        main_w = main_video_info['width']
        main_h = main_video_info['height']

        # Input labels
        filter_parts = []

        # Se target_duration è maggiore della durata del video, applica tpad per estenderlo
        if target_duration and target_duration > main_video_info['duration']:
            pad_duration = target_duration - main_video_info['duration']
            # tpad estende il video ripetendo l'ultimo frame
            filter_parts.append(f'[0:v]tpad=stop_mode=clone:stop_duration={pad_duration}[base]')
            current_base = '[base]'
            logger.info(f"   🎞️ Applicato tpad: video esteso di {pad_duration:.1f}s")
        else:
            current_base = '[0:v]'  # Video principale

        # Processa ogni layer
        for idx, layer in enumerate(layers):
            if layer['type'] == 'audio':
                # Audio viene gestito separatamente
                continue

            input_idx = idx + 1  # Input 0 è il video principale
            layer_label = f'[{input_idx}:v]'

            # Calcola dimensioni finali del layer
            scale_percent = layer['scale'] / 100.0
            keep_aspect = layer.get('keepAspectRatio', True)  # Default: mantieni proporzioni

            if keep_aspect:
                # Ottieni info del layer per mantenere aspect ratio
                layer_info = self.get_video_info(layer['path'])
                layer_original_w = layer_info['width']
                layer_original_h = layer_info['height']
                aspect_ratio = layer_original_w / layer_original_h

                # Scala in base all'orientamento
                if aspect_ratio >= 1:
                    # Landscape o quadrato: scala su larghezza
                    layer_w = int(main_w * scale_percent)
                    layer_h = int(layer_w / aspect_ratio)
                else:
                    # Portrait: scala su altezza
                    layer_h = int(main_h * scale_percent)
                    layer_w = int(layer_h * aspect_ratio)
            else:
                # Adatta al video principale (può deformare)
                layer_w = int(main_w * scale_percent)
                layer_h = int(main_h * scale_percent)

            # Calcola posizione assoluta
            # posX e posY sono offset dal centro
            pos_x = int((main_w / 2) + layer['posX'] - (layer_w / 2))
            pos_y = int((main_h / 2) + layer['posY'] - (layer_h / 2))

            # Costruisci filtro per questo layer
            layer_filters = []

            # Get timing info
            start_time = layer.get('startTime', 0)

            # 0. Per i video, gestisci timing con setpts (ritarda il video senza frame neri)
            if layer['type'] == 'video':
                if start_time > 0:
                    # Ritarda il video aggiungendo start_time ai timestamp
                    # PTS+{delay}/TB: aggiunge delay secondi ai timestamp
                    # Questo fa partire il video dopo start_time secondi SENZA frame neri!
                    layer_filters.append(f'setpts=PTS+{start_time}/TB')
                else:
                    # Resetta timestamp per sincronizzazione
                    layer_filters.append('setpts=PTS-STARTPTS')

            # 1. Scala (con o senza aspect ratio)
            if keep_aspect:
                layer_filters.append(f'scale={layer_w}:{layer_h}:force_original_aspect_ratio=decrease')
            else:
                layer_filters.append(f'scale={layer_w}:{layer_h}')

            # 2. Chromakey se richiesto
            if layer.get('chromakey', False):
                # Usa colorkey invece di chromakey (molto più veloce)
                # threshold: 0-150 (quanto verde rimuovere - più alto = più permissivo)
                # tolerance: 0-20.0 (quanto sono morbidi i bordi)
                threshold = layer.get('threshold', 110)  # Default 110 (range 0-150)
                tolerance = layer.get('tolerance', 2.0)   # Default 2.0 (range 0-20)

                # colorkey usa valori diversi: similarity (0.01-1.0) e blend (0.0-1.0)
                # Convertiamo threshold/tolerance in similarity/blend
                # IMPORTANTE: similarity troppo alto rimuove anche bianchi/grigi!
                # Usiamo valori più conservativi: 0.01-0.4 range
                similarity = 0.01 + (threshold / 150.0) * 0.3  # 0.01-0.31: range 0-150
                blend = tolerance / 20.0                        # 0-1: range 0-20

                layer_filters.append(
                    f'colorkey=0x00FF00:{similarity}:{blend}'
                )

            # 3. Opacità
            opacity = layer.get('opacity', 1.0)
            if opacity < 1.0:
                layer_filters.append(f'format=yuva420p,colorchannelmixer=aa={opacity}')

            # 4. Per immagini, NO LOOP! Sarà gestito diversamente con -t e overlay=shortest=1

            # Combina filtri per questo layer
            layer_filter_str = ','.join(layer_filters)
            processed_label = f'[layer{idx}]'
            filter_parts.append(f'{layer_label}{layer_filter_str}{processed_label}')

            # 5. Overlay sul video base
            overlay_filter = f'overlay={pos_x}:{pos_y}'

            # Gestisci timing (startTime gestito da tpad, qui solo endTime)
            end_time = layer.get('endTime', None)

            if end_time is not None:
                # Nascondi il layer dopo endTime
                # Nota: startTime è già gestito da setpts (ritardo timestamp)
                overlay_filter += f":enable='lt(t,{end_time})'"
                logger.info(f"   ⏰ Layer visibile fino a {end_time}s (startTime={start_time}s gestito da setpts)")
            elif start_time > 0:
                logger.info(f"   ⏰ Layer apparirà dopo {start_time}s (via setpts timestamp delay)")

            output_label = f'[out{idx}]'
            filter_parts.append(
                f'{current_base}{processed_label}{overlay_filter}{output_label}'
            )

            # Il risultato di questo overlay diventa la base per il prossimo
            current_base = output_label

        # L'ultimo output è il risultato finale
        filter_complex = ';'.join(filter_parts)

        # Se non ci sono layer, usa solo il video principale
        if not filter_parts:
            return None

        return filter_complex

    async def process_composition(
        self,
        main_video_path: str,
        layers: List[Dict[str, Any]],
        output_filename: Optional[str] = None,
        job_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Processa composizione multi-layer

        Args:
            main_video_path: Percorso video principale
            layers: Lista di layer (vedi build_filter_complex)
            output_filename: Nome file output (opzionale)
            job_id: ID del job (opzionale, per tracking processo FFmpeg)

        Returns:
            Dict con info sul video generato
        """

        try:
            # Verifica FFmpeg
            if not self.check_ffmpeg():
                raise Exception("FFmpeg non disponibile")

            # Info video principale
            logger.info(f"📹 Analisi video principale: {main_video_path}")
            main_info = self.get_video_info(main_video_path)
            logger.info(
                f"   Dimensioni: {main_info['width']}x{main_info['height']}, "
                f"FPS: {main_info['fps']:.1f}, Durata: {main_info['duration']:.1f}s"
            )

            # Filtra solo layer video/immagine
            visual_layers = [l for l in layers if l['type'] in ['video', 'image']]
            audio_layers = [l for l in layers if l['type'] == 'audio']

            logger.info(f"🎨 Layer da processare: {len(visual_layers)} visivi, {len(audio_layers)} audio")

            # Calcola durata massima necessaria basata sui layer
            max_duration = main_info['duration']
            for layer in visual_layers:
                layer_info = self.get_video_info(layer['path'])
                layer_start = layer.get('startTime', 0)
                layer_end = layer.get('endTime', None)

                if layer_end is None:
                    # Il layer dura fino alla sua fine naturale
                    layer_total_duration = layer_start + layer_info.get('duration', 0)
                else:
                    # Il layer finisce a endTime
                    layer_total_duration = layer_end

                if layer_total_duration > max_duration:
                    max_duration = layer_total_duration
                    logger.info(f"   ⏱️ Durata estesa a {max_duration:.1f}s per layer {layer.get('name', 'unknown')}")

            # Se qualche layer richiede più tempo del video principale, usiamo tpad
            if max_duration > main_info['duration']:
                logger.info(f"   🎞️ Video principale esteso da {main_info['duration']:.1f}s a {max_duration:.1f}s")

            # Output path
            if not output_filename:
                timestamp = int(datetime.now().timestamp() * 1000)
                output_filename = f"compositor_{timestamp}.mp4"

            output_path = self.output_dir / output_filename

            # Costruisci comando FFmpeg
            cmd = ['ffmpeg', '-y']  # -y sovrascrive

            # Input 0: video principale
            cmd.extend(['-i', main_video_path])

            # Input 1-N: layer
            for layer in visual_layers:
                if layer['type'] == 'image':
                    # Per immagini: usa -loop 1 -framerate FPS -t DURATA
                    # Questo crea un video dalla singola immagine (MOLTO più veloce del filtro loop!)
                    fps = main_info.get('fps', 24)
                    duration = max_duration  # Usa la durata massima calcolata
                    cmd.extend([
                        '-loop', '1',           # Loop dell'immagine
                        '-framerate', str(fps), # FPS del video principale
                        '-t', str(duration),    # Durata uguale al video principale
                        '-i', layer['path']
                    ])
                else:
                    # Video normali
                    cmd.extend(['-i', layer['path']])

            # Audio layers
            for layer in audio_layers:
                cmd.extend(['-i', layer['path']])

            # Build unified filter_complex for video + audio
            filter_parts = []

            # Video filters
            if visual_layers:
                video_filter = self.build_filter_complex(main_info, visual_layers, max_duration)
                if video_filter:
                    filter_parts.append(video_filter)
                    final_video_output = f'[out{len(visual_layers)-1}]'
                else:
                    final_video_output = '[0:v]'
            else:
                final_video_output = '[0:v]'

            # Audio mixing: main video audio + layer video audios + separate audio files
            audio_inputs = []

            # Audio dai layer video (se presenti) con delay se startTime > 0
            for i, layer in enumerate(visual_layers):
                if layer['type'] == 'video':
                    start_time = layer.get('startTime', 0)
                    if start_time > 0:
                        # Applica delay all'audio (in millisecondi)
                        delay_ms = int(start_time * 1000)
                        delayed_label = f'[a{i+1}d]'
                        filter_parts.append(f'[{i+1}:a]adelay={delay_ms}|{delay_ms}{delayed_label}')
                        audio_inputs.append(delayed_label)
                        logger.info(f"   🔊 Audio layer ritardato di {start_time} secondi")
                    else:
                        audio_inputs.append(f'[{i+1}:a]')

            # Audio dai file audio separati
            for i, layer in enumerate(audio_layers):
                layer_index = len(visual_layers) + i + 1
                start_time = layer.get('startTime', 0)
                if start_time > 0:
                    delay_ms = int(start_time * 1000)
                    delayed_label = f'[a{layer_index}d]'
                    filter_parts.append(f'[{layer_index}:a]adelay={delay_ms}|{delay_ms}{delayed_label}')
                    audio_inputs.append(delayed_label)
                else:
                    audio_inputs.append(f'[{layer_index}:a]')

            # Aggiungi audio dal video principale SOLO se ci sono altri audio da mixare
            if len(audio_inputs) > 0:
                # Se ci sono layer audio/video, aggiungi anche l'audio del video principale e mixa
                audio_inputs.insert(0, '[0:a]')  # Metti il main audio per primo
                # Mix multipli stream audio
                audio_filter = f'{"".join(audio_inputs)}amix=inputs={len(audio_inputs)}:duration=longest[aout]'
                filter_parts.append(audio_filter)
                final_audio_output = '[aout]'
            else:
                # Nessun layer audio, usa direttamente l'audio del video principale (se esiste)
                # Non serve filter_complex per l'audio, sarà mappato con -map 0:a?
                final_audio_output = None

            # Applica filter_complex se ci sono filtri
            if filter_parts:
                combined_filter = ';'.join(filter_parts)
                cmd.extend(['-filter_complex', combined_filter])
                # Mappa output video
                cmd.extend(['-map', final_video_output])
                # Mappa output audio
                if final_audio_output:
                    # Audio processato dal filter_complex (mix di più stream)
                    cmd.extend(['-map', final_audio_output])
                else:
                    # Nessun audio processato, usa direttamente l'audio del video principale (se esiste)
                    cmd.extend(['-map', '0:a?'])  # Audio opzionale con ?
            else:
                # Nessun filtro, mappa diretto
                cmd.extend(['-map', '0:v'])
                cmd.extend(['-map', '0:a?'])  # Audio opzionale

            # Codec e qualità
            # Usa preset ultrafast per elaborazione rapidissima (specialmente con chromakey)
            cmd.extend([
                '-c:v', 'libx264',
                '-preset', 'ultrafast',  # Cambiato da 'medium' a 'ultrafast' per 5-10x velocità
                '-crf', '23',
                '-c:a', 'aac',
                '-b:a', '192k',
                '-movflags', '+faststart',
                str(output_path)
            ])

            logger.info(f"🎬 Comando FFmpeg: {' '.join(cmd[:10])}...")

            # Esegui FFmpeg
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )

            # Salva processo per permettere cancellazione
            if job_id:
                self.active_jobs[job_id] = process
                logger.info(f"   📝 Processo FFmpeg registrato per job {job_id} (PID: {process.pid})")

            try:
                # Leggi output
                stderr_output = []
                for line in process.stderr:
                    stderr_output.append(line)
                    # Log progress ogni 50 righe
                    if len(stderr_output) % 50 == 0:
                        logger.info(f"   FFmpeg processing... ({len(stderr_output)} lines)")

                # Attendi completamento
                returncode = process.wait()
            finally:
                # Rimuovi processo dalla lista attivi
                if job_id and job_id in self.active_jobs:
                    del self.active_jobs[job_id]
                    logger.info(f"   📝 Processo FFmpeg rimosso per job {job_id}")

            if returncode != 0:
                # Log TUTTO lo stderr per debug
                full_stderr = ''.join(stderr_output)
                logger.error(f"❌ FFmpeg fallito - OUTPUT COMPLETO:")
                logger.error(full_stderr)
                # Prendi solo le ultime 50 righe per l'eccezione
                error_msg = ''.join(stderr_output[-50:])
                raise Exception(f"FFmpeg error: {error_msg}")

            # Verifica output
            logger.info(f"🔍 Verifica output_path: {output_path}")
            logger.info(f"🔍 output_path.exists(): {output_path.exists()}")
            logger.info(f"🔍 output_path assoluto: {output_path.absolute()}")

            if not output_path.exists():
                # Lista file nella directory output
                logger.error(f"❌ File output non trovato: {output_path}")
                logger.error(f"   Contenuto directory output:")
                for f in self.output_dir.iterdir():
                    logger.error(f"     - {f.name}")
                raise Exception("File output non creato")

            file_size = output_path.stat().st_size
            logger.info(f"✅ Video generato: {output_path} ({file_size / 1024 / 1024:.2f} MB)")

            # Info output
            output_info = self.get_video_info(str(output_path))

            return {
                'success': True,
                'output_path': str(output_path),
                'filename': output_filename,
                'size_bytes': file_size,
                'size_mb': round(file_size / 1024 / 1024, 2),
                'width': output_info['width'],
                'height': output_info['height'],
                'duration': output_info['duration'],
                'fps': output_info['fps']
            }

        except Exception as e:
            logger.error(f"❌ Errore processing composition: {e}")
            raise


# Singleton instance
compositor_service = CompositorService()
