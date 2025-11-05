import cv2
import numpy as np
import argparse
import os
import subprocess
import tempfile


def remove_background_and_overlay_timed(foreground_video, background_video, output_video,
                                        start_time=0, duration=None,
                                        lower_green=None, upper_green=None, blur_kernel=5,
                                        audio_source='background', position=(0, 0), scale=1.0, opacity=1.0,
                                        fast_mode=False, gpu_accel=False,
                                        logo_path=None, logo_position=None, logo_scale=0.1, progress_callback=None):
    """
    Rimuove lo sfondo verde e sovrappone la call to action in un momento specifico
    """
    print(f"🎬 Avvio elaborazione...")
    print(f"   Foreground: {foreground_video}")
    print(f"   Background: {background_video}")
    print(f"   Output: {output_video}")
    print(f"   Modalità veloce: {fast_mode}")
    print(f"   GPU: {gpu_accel}")

    if lower_green is None:
        lower_green = np.array([40, 40, 40])
    if upper_green is None:
        upper_green = np.array([80, 255, 255])

    try:
        # Apri i video
        fg_cap = cv2.VideoCapture(foreground_video)
        bg_cap = cv2.VideoCapture(background_video)

        if not fg_cap.isOpened():
            print(f"❌ Errore: impossibile aprire il video foreground {foreground_video}")
            return False

        if not bg_cap.isOpened():
            print(f"❌ Errore: impossibile aprire il video background {background_video}")
            return False

        # Proprietà video
        bg_fps = int(bg_cap.get(cv2.CAP_PROP_FPS))
        bg_width = int(bg_cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        bg_height = int(bg_cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        bg_frames = int(bg_cap.get(cv2.CAP_PROP_FRAME_COUNT))
        bg_duration = bg_frames / bg_fps

        fg_fps = int(fg_cap.get(cv2.CAP_PROP_FPS))
        fg_width = int(fg_cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        fg_height = int(fg_cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fg_frames = int(fg_cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fg_duration = fg_frames / fg_fps

        print(f"✅ Background: {bg_width}x{bg_height}, {bg_duration:.1f}s, FPS: {bg_fps}")
        print(f"✅ Foreground: {fg_width}x{fg_height}, {fg_duration:.1f}s, FPS: {fg_fps}")

        # Calcola timing
        start_frame = int(start_time * bg_fps)
        if duration is None:
            duration = fg_duration
        end_frame = int((start_time + duration) * bg_fps)

        print(f"📅 Call to action: dal secondo {start_time} per {duration:.1f}s (frame {start_frame}-{end_frame})")
        print(f"🎵 Audio mode: {audio_source}")

        # Calcola dimensioni scalate
        new_fg_width = int(fg_width * scale)
        new_fg_height = int(fg_height * scale)

    except Exception as e:
        print(f"❌ Errore durante l'apertura dei video: {e}")
        return False

    try:
        # Carica il logo se fornito
        logo_img = None
        if logo_path and os.path.exists(logo_path):
            print(f"📷 Caricando logo: {logo_path}")
            logo_img = cv2.imread(logo_path, cv2.IMREAD_UNCHANGED)
            if logo_img is not None:
                # Scala il logo
                if logo_img.shape[2] == 4:  # RGBA
                    logo_height, logo_width = logo_img.shape[:2]
                else:  # RGB, aggiungi canale alpha
                    logo_img = cv2.cvtColor(logo_img, cv2.COLOR_BGR2BGRA)
                    logo_height, logo_width = logo_img.shape[:2]
                
                new_logo_width = int(logo_width * logo_scale)
                new_logo_height = int(logo_height * logo_scale)
                logo_img = cv2.resize(logo_img, (new_logo_width, new_logo_height))
                print(f"✅ Logo caricato: {new_logo_width}x{new_logo_height}")

        # Pre-processa tutti i frame del foreground con chroma key
        print("🔄 Pre-processando call to action...")
        fg_processed_frames = []
        fg_masks = []

        # Ottimizzazione: se fast_mode, processa solo i frame necessari
        if fast_mode:
            print("🚀 Modalità veloce: pre-processando solo frame necessari...")
            total_needed_frames = min(len(range(int(duration * fg_fps))) if duration else fg_frames, fg_frames)
        else:
            total_needed_frames = fg_frames

        frame_idx = 0
        while frame_idx < total_needed_frames:
            ret, fg_frame = fg_cap.read()
            if not ret:
                break

            # Scala se necessario
            if scale != 1.0:
                fg_frame = cv2.resize(fg_frame, (new_fg_width, new_fg_height))

            # Chroma key ottimizzato
            hsv = cv2.cvtColor(fg_frame, cv2.COLOR_BGR2HSV)
            mask = cv2.inRange(hsv, lower_green, upper_green)

            # Pulizia maschera (ridotta se fast_mode)
            if fast_mode:
                mask = cv2.GaussianBlur(mask, (blur_kernel, blur_kernel), 0)
            else:
                kernel = np.ones((3, 3), np.uint8)
                mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
                mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
                mask = cv2.GaussianBlur(mask, (blur_kernel, blur_kernel), 0)

            # Inverti maschera
            mask_inv = cv2.bitwise_not(mask)

            # Applica opacità
            if opacity < 1.0:
                mask_inv = (mask_inv * opacity).astype(np.uint8)

            # Estrai soggetto
            fg_subject = cv2.bitwise_and(fg_frame, fg_frame, mask=mask_inv)

            fg_processed_frames.append(fg_subject)
            fg_masks.append(mask_inv)
            frame_idx += 1

        fg_cap.release()
        print(f"✅ Processati {len(fg_processed_frames)} frame della call to action")

    except Exception as e:
        print(f"❌ Errore durante pre-processamento: {e}")
        return False

    try:
        # Configura writer con codec ottimizzato
        if gpu_accel:
            fourcc = cv2.VideoWriter_fourcc(*'H264')
            print("🚀 Usando codec hardware H264")
        elif fast_mode:
            fourcc = cv2.VideoWriter_fourcc(*'XVID')
            print("🚀 Usando codec veloce XVID")
        else:
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')

        out = cv2.VideoWriter(output_video, fourcc, bg_fps, (bg_width, bg_height))

        if not out.isOpened():
            print("❌ Errore: impossibile creare il video writer")
            return False

        print("🎬 Avvio elaborazione video...")

        # Processa video frame by frame
        x, y = position
        frame_count = 0

        while frame_count < bg_frames:
            # Check for cancellation more frequently (every 10 frames)
            if frame_count % 10 == 0 and progress_callback:
                should_continue = progress_callback(None)  # Just check, don't update progress
                if should_continue is False:
                    print("🛑 Processing interrupted - early exit")
                    bg_cap.release()
                    fg_cap.release()
                    out.release()
                    if os.path.exists(output_video):
                        os.remove(output_video)
                    return False
            
            bg_ret, bg_frame = bg_cap.read()
            if not bg_ret:
                break

            result = bg_frame.copy()

            # Controlla se siamo nel range della call to action
            if start_frame <= frame_count < end_frame:
                fg_frame_idx = int((frame_count - start_frame) * fg_fps / bg_fps)

                if fg_frame_idx >= len(fg_processed_frames):
                    fg_frame_idx = len(fg_processed_frames) - 1

                if fg_frame_idx >= 0 and fg_frame_idx < len(fg_processed_frames):
                    fg_subject = fg_processed_frames[fg_frame_idx]
                    mask_inv = fg_masks[fg_frame_idx]

                    # Verifica bounds
                    x_safe = max(0, min(x, bg_width - fg_subject.shape[1]))
                    y_safe = max(0, min(y, bg_height - fg_subject.shape[0]))

                    y_end = min(y_safe + fg_subject.shape[0], bg_height)
                    x_end = min(x_safe + fg_subject.shape[1], bg_width)
                    fg_h = y_end - y_safe
                    fg_w = x_end - x_safe

                    if fg_h > 0 and fg_w > 0:
                        fg_crop = fg_subject[:fg_h, :fg_w]
                        mask_crop = mask_inv[:fg_h, :fg_w]

                        bg_area = result[y_safe:y_end, x_safe:x_end]
                        mask_norm = mask_crop.astype(float) / 255.0
                        mask_norm = np.stack([mask_norm, mask_norm, mask_norm], axis=2)

                        result[y_safe:y_end, x_safe:x_end] = \
                            (fg_crop * mask_norm + bg_area * (1 - mask_norm)).astype(np.uint8)

            # Aggiungi logo se presente
            if logo_img is not None and logo_position is not None:
                logo_x, logo_y = logo_position
                logo_h, logo_w = logo_img.shape[:2]
                
                # Controlla bounds del logo (spostato 3 pixel più vicino agli angoli)
                logo_x_safe = max(3, min(logo_x, bg_width - logo_w - 3))
                logo_y_safe = max(3, min(logo_y, bg_height - logo_h - 3))
                logo_x_end = logo_x_safe + logo_w
                logo_y_end = logo_y_safe + logo_h
                
                # Overlay del logo con alpha blending
                if logo_img.shape[2] == 4:  # RGBA
                    logo_bgr = logo_img[:, :, :3]
                    logo_alpha = logo_img[:, :, 3] / 255.0
                    
                    bg_area_logo = result[logo_y_safe:logo_y_end, logo_x_safe:logo_x_end]
                    logo_alpha_3ch = np.stack([logo_alpha, logo_alpha, logo_alpha], axis=2)
                    
                    result[logo_y_safe:logo_y_end, logo_x_safe:logo_x_end] = \
                        (logo_bgr * logo_alpha_3ch + bg_area_logo * (1 - logo_alpha_3ch)).astype(np.uint8)

            out.write(result)
            frame_count += 1

            progress_interval = 60 if fast_mode else 30  # More frequent updates
            if frame_count % progress_interval == 0:
                progress = (frame_count / bg_frames) * 100
                print(f"🔄 Progresso: {progress:.1f}% ({frame_count}/{bg_frames})")
                # Update progress via callback if provided
                if progress_callback:
                    # Use full 0-100% range for more accurate progress
                    mapped_progress = 30 + int(progress * 0.65)  # Map 0-100% to 30-95% range
                    should_continue = progress_callback(mapped_progress)
                    # If callback returns False, stop processing
                    if should_continue is False:
                        print("🛑 Processing interrupted by callback")
                        bg_cap.release()
                        fg_cap.release()
                        out.release()
                        # Clean up incomplete output file
                        if os.path.exists(output_video):
                            os.remove(output_video)
                        return False

        bg_cap.release()
        out.release()
        print("✅ Video processato con successo!")

    except Exception as e:
        print(f"❌ Errore durante elaborazione video: {e}")
        return False

    # Gestione audio
    if audio_source == 'none':
        print(f"✅ Video (senza audio) salvato in: {output_video}")
        if progress_callback:
            progress_callback(100)
        return True

    print("🎵 Gestione audio...")
    if progress_callback:
        progress_callback(90)
    temp_video = output_video.replace('.mp4', '_temp.mp4')

    try:
        os.rename(output_video, temp_video)
    except Exception as e:
        print(f"❌ Errore rinominando file temporaneo: {e}")
        return False

    try:
        if audio_source == 'background':
            codec = 'copy' if fast_mode else 'aac'
            cmd = [
                'ffmpeg', '-y', '-v', 'error',
                '-i', temp_video,
                '-i', background_video,
                '-c:v', 'copy',
                '-c:a', codec,
            ]
            if codec == 'aac':
                cmd.extend(['-b:a', '128k'])
            cmd.extend([
                '-map', '0:v:0',
                '-map', '1:a:0',
                '-shortest',
                output_video
            ])
        elif audio_source == 'foreground':
            cmd = [
                'ffmpeg', '-y', '-v', 'error',
                '-i', temp_video,
                '-i', foreground_video,
                '-c:v', 'copy',
                '-c:a', 'aac', '-b:a', '128k',
                '-map', '0:v:0',
                '-map', '1:a:0',
                '-shortest',
                output_video
            ]
        elif audio_source == 'both':
            cmd = [
                'ffmpeg', '-y', '-v', 'error',
                '-i', temp_video,
                '-i', background_video,
                '-i', foreground_video,
                '-filter_complex', '[1:a][2:a]amix=inputs=2[a]',
                '-c:v', 'copy',
                '-c:a', 'aac', '-b:a', '128k',
                '-map', '0:v:0',
                '-map', '[a]',
                '-shortest',
                output_video
            ]
        elif audio_source == 'timed':
            end_time = start_time + (duration if duration else fg_duration)
            delay_ms = int(start_time * 1000)

            filter_complex = f"""
            [1:a]volume=1.0[bg];
            [2:a]adelay={delay_ms}|{delay_ms},volume=1.2[fg_delayed];
            [bg][fg_delayed]amix=inputs=2:duration=longest:dropout_transition=2[final]
            """

            cmd = [
                'ffmpeg', '-y', '-v', 'error',
                '-i', temp_video,
                '-i', background_video,
                '-i', foreground_video,
                '-filter_complex', filter_complex,
                '-c:v', 'copy',
                '-c:a', 'aac', '-b:a', '128k',
                '-map', '0:v:0',
                '-map', '[final]',
                '-shortest',
                output_video
            ]
        elif audio_source == 'synced':
            end_time = start_time + (duration if duration else fg_duration)
            delay_ms = int(start_time * 1000)

            filter_complex = f"""
            [1:a]volume=0.8[bg];
            [2:a]adelay={delay_ms}|{delay_ms},volume=1.0[fg_synced];
            [bg][fg_synced]amix=inputs=2:duration=longest:dropout_transition=2[final]
            """

            cmd = [
                'ffmpeg', '-y', '-v', 'error',
                '-i', temp_video,
                '-i', background_video,
                '-i', foreground_video,
                '-filter_complex', filter_complex,
                '-c:v', 'copy',
                '-c:a', 'aac', '-b:a', '128k',
                '-map', '0:v:0',
                '-map', '[final]',
                '-shortest',
                output_video
            ]

        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        os.remove(temp_video)
        print(f"✅ Video con audio ({audio_source}) salvato in: {output_video}")
        if progress_callback:
            progress_callback(100)
        return True

    except subprocess.CalledProcessError as e:
        print(f"❌ Errore ffmpeg: {e.stderr}")
        print("🔄 Ripristino video senza audio...")
        try:
            os.rename(temp_video, output_video)
            print(f"✅ Video (senza audio) salvato in: {output_video}")
            if progress_callback:
                progress_callback(100)
            return True
        except:
            print(f"❌ Errore nel ripristino file")
            return False

    except FileNotFoundError:
        print("❌ ffmpeg non trovato!")
        try:
            os.rename(temp_video, output_video)
            print(f"✅ Video (senza audio) salvato in: {output_video}")
            print("💡 Installa ffmpeg per l'audio:")
            print("  macOS: brew install ffmpeg")
            print("  Ubuntu: sudo apt install ffmpeg")
            if progress_callback:
                progress_callback(100)
            return True
        except:
            print(f"❌ Errore nel ripristino file")
            return False

    except Exception as e:
        print(f"❌ Errore generico audio: {e}")
        try:
            os.rename(temp_video, output_video)
            return True
        except:
            return False


def preview_timed_overlay(foreground_video, background_video, start_time=0, duration=None,
                          lower_green=None, upper_green=None):
    """
    Anteprima della sovrapposizione temporizzata
    """
    if lower_green is None:
        lower_green = np.array([40, 40, 40])
    if upper_green is None:
        upper_green = np.array([80, 255, 255])

    fg_cap = cv2.VideoCapture(foreground_video)
    bg_cap = cv2.VideoCapture(background_video)

    if not fg_cap.isOpened() or not bg_cap.isOpened():
        print("Errore nell'apertura dei video")
        return

    bg_fps = int(bg_cap.get(cv2.CAP_PROP_FPS))
    bg_frames = int(bg_cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fg_frames = int(fg_cap.get(cv2.CAP_PROP_FRAME_COUNT))

    start_frame = int(start_time * bg_fps)
    if duration:
        end_frame = int((start_time + duration) * bg_fps)
    else:
        end_frame = start_frame + fg_frames

    print(f"Anteprima timing: frame {start_frame}-{end_frame}")
    print("Controlli: 'q' esci, 'spazio' pausa, 's' vai al start, frecce ←→ avanti/indietro")

    cv2.namedWindow('Timed Preview')
    cv2.createTrackbar('Timeline', 'Timed Preview', 0, bg_frames - 1, lambda x: None)
    cv2.createTrackbar('H Min', 'Timed Preview', lower_green[0], 180, lambda x: None)
    cv2.createTrackbar('H Max', 'Timed Preview', upper_green[0], 180, lambda x: None)

    paused = False
    current_frame = 0

    while True:
        timeline_pos = cv2.getTrackbarPos('Timeline', 'Timed Preview')

        if not paused and timeline_pos != current_frame:
            current_frame = timeline_pos
            bg_cap.set(cv2.CAP_PROP_POS_FRAMES, current_frame)

        bg_ret, bg_frame = bg_cap.read()
        if not bg_ret:
            break

        result = bg_frame.copy()
        current_time = current_frame / bg_fps

        # Mostra call to action solo nel timing giusto
        if start_frame <= current_frame < end_frame:
            fg_frame_idx = current_frame - start_frame
            fg_cap.set(cv2.CAP_PROP_POS_FRAMES, fg_frame_idx)
            fg_ret, fg_frame = fg_cap.read()

            if fg_ret:
                h_min = cv2.getTrackbarPos('H Min', 'Timed Preview')
                h_max = cv2.getTrackbarPos('H Max', 'Timed Preview')

                hsv = cv2.cvtColor(fg_frame, cv2.COLOR_BGR2HSV)
                lower = np.array([h_min, lower_green[1], lower_green[2]])
                upper = np.array([h_max, upper_green[1], upper_green[2]])
                mask = cv2.inRange(hsv, lower, upper)
                mask = cv2.GaussianBlur(mask, (5, 5), 0)
                mask_inv = cv2.bitwise_not(mask)

                if (fg_frame.shape[1] <= bg_frame.shape[1] and
                        fg_frame.shape[0] <= bg_frame.shape[0]):
                    fg_subject = cv2.bitwise_and(fg_frame, fg_frame, mask=mask_inv)
                    bg_area = result[0:fg_frame.shape[0], 0:fg_frame.shape[1]]
                    mask_norm = np.stack([mask_inv / 255.0] * 3, axis=2)
                    result[0:fg_frame.shape[0], 0:fg_frame.shape[1]] = \
                        (fg_subject * mask_norm + bg_area * (1 - mask_norm)).astype(np.uint8)

        # Info timing
        cv2.putText(result, f"Time: {current_time:.1f}s", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        if start_frame <= current_frame < end_frame:
            cv2.putText(result, "CALL TO ACTION ON", (10, 70),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

        display = cv2.resize(result, (1280, 720))
        cv2.imshow('Timed Preview', display)

        key = cv2.waitKey(30) & 0xFF
        if key == ord('q'):
            break
        elif key == ord(' '):
            paused = not paused
        elif key == ord('s'):
            current_frame = start_frame
            cv2.setTrackbarPos('Timeline', 'Timed Preview', current_frame)

        if not paused:
            current_frame = min(bg_frames - 1, current_frame + 1)
            cv2.setTrackbarPos('Timeline', 'Timed Preview', current_frame)

    fg_cap.release()
    bg_cap.release()
    cv2.destroyAllWindows()


def main():
    try:
        parser = argparse.ArgumentParser(description='Call to Action temporizzata con chromakey')
        parser.add_argument('foreground', help='Video call to action (con green screen)')
        parser.add_argument('background', help='Video di sfondo')
        parser.add_argument('-o', '--output', help='Video di output')

        # TIMING
        parser.add_argument('--start', type=float, default=0,
                            help='Quando inizia la call to action (secondi)')
        parser.add_argument('--duration', type=float,
                            help='Durata call to action (None = durata foreground)')

        # AUDIO
        parser.add_argument('--audio', choices=['background', 'foreground', 'both', 'timed', 'synced', 'none'],
                            default='background', help='Sorgente audio')

        parser.add_argument('--preview', action='store_true', help='Anteprima temporizzata')

        # Parametri velocità
        parser.add_argument('--fast', action='store_true', help='Modalità veloce')
        parser.add_argument('--gpu', action='store_true', help='Accelerazione GPU')

        # Parametri chroma key
        parser.add_argument('--h-min', type=int, default=40)
        parser.add_argument('--h-max', type=int, default=80)
        parser.add_argument('--s-min', type=int, default=40)
        parser.add_argument('--s-max', type=int, default=255)
        parser.add_argument('--v-min', type=int, default=40)
        parser.add_argument('--v-max', type=int, default=255)
        parser.add_argument('--blur', type=int, default=5)

        # Parametri posizionamento
        parser.add_argument('--x', type=int, default=0, help='Posizione X')
        parser.add_argument('--y', type=int, default=0, help='Posizione Y')
        parser.add_argument('--scale', type=float, default=1.0, help='Scala')
        parser.add_argument('--opacity', type=float, default=1.0, help='Opacità')

        args = parser.parse_args()

        if not os.path.exists(args.foreground):
            print(f"❌ {args.foreground} non trovato")
            return

        if not os.path.exists(args.background):
            print(f"❌ {args.background} non trovato")
            return

        lower_green = np.array([args.h_min, args.s_min, args.v_min])
        upper_green = np.array([args.h_max, args.s_max, args.v_max])

        if args.preview:
            preview_timed_overlay(args.foreground, args.background, args.start,
                                  args.duration, lower_green, upper_green)
        else:
            output = args.output or args.foreground.replace('.mp4', '_timed_overlay.mp4')
            success = remove_background_and_overlay_timed(
                args.foreground, args.background, output,
                args.start, args.duration, lower_green, upper_green, args.blur,
                args.audio, (args.x, args.y), args.scale, args.opacity,
                args.fast, args.gpu
            )

            if success:
                print(f"🎉 Elaborazione completata con successo!")
            else:
                print(f"❌ Elaborazione fallita!")

    except Exception as e:
        print(f"❌ Errore generale: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    if len(os.sys.argv) == 1:
        print("🎬 === CALL TO ACTION TEMPORIZZATA ===")
        print("\nEsempi d'uso:")
        print("python chromakey.py call_to_action.mp4 ticktock.mp4 --start 5 --audio synced --fast")
        print("python chromakey.py cta.mp4 bg.mp4 --start 10 --duration 5 --preview")
    else:
        main()
#   python chromakey.py call_to_action.mp4 ticktock.mp4 --start 5 --audio synced --fast