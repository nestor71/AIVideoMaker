"""
Thumbnail Service - AI Thumbnail Generation
============================================
Servizio indipendente per generazione miniature YouTube con:
- Generazione AI (DALL-E 3)
- Upload immagine custom
- Estrazione frame da video
- Text overlay personalizzabile
- Ottimizzazioni CTR automatiche

Completamente testabile, nessuna dipendenza da FastAPI.
"""

import subprocess
import tempfile
import logging
import requests
from pathlib import Path
from typing import Optional, Callable, Dict, Any, Tuple
from dataclasses import dataclass
from PIL import Image, ImageDraw, ImageFont, ImageEnhance
from io import BytesIO

from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class ThumbnailParams:
    """Parametri generazione thumbnail"""
    output_path: Path

    # Source (uno dei tre)
    source_type: str  # "ai", "upload", "frame"
    ai_description: Optional[str] = None
    ai_style: Optional[str] = None
    upload_image_path: Optional[Path] = None
    video_path: Optional[Path] = None
    frame_timestamp: Optional[float] = None

    # Text overlay (opzionale)
    text: Optional[str] = None
    text_position: str = "center"  # "top", "center", "bottom"
    text_color: str = "#FFFFFF"
    text_bg_color: str = "#000000"
    text_bg_opacity: float = 0.7

    # Ottimizzazioni
    enhance_ctr: bool = True


class ThumbnailService:
    """
    Servizio generazione miniature YouTube professionali.

    Supporta 3 modalità:
    1. AI Generation (DALL-E 3)
    2. Upload Custom Image
    3. Extract Frame from Video
    """

    # Dimensioni YouTube
    YOUTUBE_WIDTH = 1280
    YOUTUBE_HEIGHT = 720
    MAX_SIZE_MB = 2.0

    AI_STYLES = {
        "cinematic": "Cinematic movie poster style, dramatic lighting, epic composition",
        "minimal": "Minimal clean design, simple shapes, modern aesthetic",
        "vibrant": "Vibrant colorful style, high energy, eye-catching",
        "tech": "Modern technology style, futuristic, sleek design",
        "playful": "Playful fun style, cartoon-like, engaging",
        "professional": "Professional business style, clean, trustworthy",
        "dark": "Dark moody atmosphere, dramatic shadows, mysterious",
        "bright": "Bright cheerful style, high saturation, positive vibe"
    }

    def __init__(self, config: Optional[Any] = None):
        """Inizializza service"""
        self.config = config or settings
        self.ffmpeg_path = self.config.ffmpeg_path

        # Verifica OpenAI API key se necessario
        if not self.config.openai_api_key:
            logger.warning("OpenAI API key non configurata - generazione AI non disponibile")

    def generate(
        self,
        params: ThumbnailParams,
        progress_callback: Optional[Callable[[int, str], bool]] = None
    ) -> Dict[str, Any]:
        """
        Genera thumbnail

        Args:
            params: Parametri thumbnail
            progress_callback: Callback progresso

        Returns:
            dict: Risultato con 'success', 'output_path', 'size_bytes'

        Raises:
            ValueError: Se parametri invalidi
            RuntimeError: Se generazione fallisce
        """
        logger.info(f"🎨 Avvio generazione thumbnail")
        logger.info(f"   Tipo: {params.source_type}")
        logger.info(f"   Output: {params.output_path}")

        self._validate_params(params)

        if progress_callback:
            progress_callback(5, "Inizializzazione...")

        try:
            # Step 1: Ottieni immagine base secondo source_type
            if params.source_type == "ai":
                if progress_callback:
                    progress_callback(10, "Generazione immagine AI con DALL-E 3...")
                base_image = self._generate_ai_image(params.ai_description, params.ai_style)

            elif params.source_type == "upload":
                if progress_callback:
                    progress_callback(10, "Caricamento immagine...")
                base_image = Image.open(params.upload_image_path)

            elif params.source_type == "frame":
                if progress_callback:
                    progress_callback(10, "Estrazione frame da video...")
                base_image = self._extract_frame(params.video_path, params.frame_timestamp)

            else:
                raise ValueError(f"Source type non valido: {params.source_type}")

            if progress_callback:
                progress_callback(50, "Ridimensionamento a 1280x720...")

            # Step 2: Ridimensiona a dimensioni YouTube
            thumbnail = self._resize_to_youtube(base_image)

            # Step 3: Aggiungi testo se richiesto
            if params.text:
                if progress_callback:
                    progress_callback(70, "Aggiunta testo overlay...")
                thumbnail = self._add_text_overlay(
                    thumbnail,
                    params.text,
                    params.text_position,
                    params.text_color,
                    params.text_bg_color,
                    params.text_bg_opacity
                )

            # Step 4: Ottimizzazioni CTR
            if params.enhance_ctr:
                if progress_callback:
                    progress_callback(85, "Ottimizzazioni CTR (saturazione, contrasto, nitidezza)...")
                thumbnail = self._enhance_for_ctr(thumbnail)

            # Step 5: Salva con compressione ottimale
            if progress_callback:
                progress_callback(95, "Salvataggio thumbnail...")

            self._save_optimized(thumbnail, params.output_path)

            file_size = params.output_path.stat().st_size

            if progress_callback:
                progress_callback(100, "✅ Thumbnail generata!")

            return {
                "success": True,
                "output_path": str(params.output_path),
                "size_bytes": file_size,
                "size_mb": file_size / (1024 * 1024),
                "dimensions": f"{self.YOUTUBE_WIDTH}x{self.YOUTUBE_HEIGHT}"
            }

        except Exception as e:
            logger.error(f"❌ Errore generazione thumbnail: {e}")
            raise

    def _validate_params(self, params: ThumbnailParams):
        """Valida parametri"""
        if params.source_type not in ["ai", "upload", "frame"]:
            raise ValueError(f"source_type deve essere 'ai', 'upload' o 'frame'")

        if params.source_type == "ai" and not self.config.openai_api_key:
            raise ValueError("OpenAI API key non configurata")

        if params.source_type == "upload" and not params.upload_image_path:
            raise ValueError("upload_image_path richiesto per source_type='upload'")

        if params.source_type == "frame":
            if not params.video_path or not params.frame_timestamp:
                raise ValueError("video_path e frame_timestamp richiesti per source_type='frame'")

    def _generate_ai_image(self, description: Optional[str], style: Optional[str]) -> Image.Image:
        """Genera immagine con DALL-E 3"""
        from openai import OpenAI

        client = OpenAI(api_key=self.config.openai_api_key)

        # Costruisci prompt
        style_prefix = ""
        if style and style in self.AI_STYLES:
            style_prefix = self.AI_STYLES[style] + ". "

        prompt = f"{style_prefix}YouTube thumbnail: {description or 'engaging video thumbnail'}. High quality, 16:9 aspect ratio, eye-catching, professional."

        logger.info(f"DALL-E 3 prompt: {prompt[:100]}...")

        # Generate image
        response = client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size="1792x1024",  # Closest to 16:9
            quality="hd",
            n=1
        )

        image_url = response.data[0].url

        # Download immagine
        img_response = requests.get(image_url, timeout=30)
        img_response.raise_for_status()

        image = Image.open(BytesIO(img_response.content))
        logger.info("✅ Immagine AI generata")

        return image

    def _extract_frame(self, video_path: Path, timestamp: float) -> Image.Image:
        """Estrai frame da video con FFmpeg"""
        temp_frame = tempfile.mktemp(suffix='.jpg')

        try:
            subprocess.run([
                self.ffmpeg_path,
                '-ss', str(timestamp),
                '-i', str(video_path),
                '-vframes', '1',
                '-q:v', '2',  # Alta qualità
                '-y',
                temp_frame
            ], check=True, capture_output=True)

            image = Image.open(temp_frame)
            Path(temp_frame).unlink()

            logger.info(f"✅ Frame estratto al secondo {timestamp}")
            return image

        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Estrazione frame fallita: {e.stderr.decode() if e.stderr else str(e)}")

    def _resize_to_youtube(self, image: Image.Image) -> Image.Image:
        """Ridimensiona a 1280x720 mantenendo aspect ratio"""
        # Convert to RGB se necessario
        if image.mode != 'RGB':
            image = image.convert('RGB')

        # Calcola crop per 16:9
        img_ratio = image.width / image.height
        target_ratio = self.YOUTUBE_WIDTH / self.YOUTUBE_HEIGHT

        if img_ratio > target_ratio:
            # Immagine più larga, croppa width
            new_width = int(image.height * target_ratio)
            left = (image.width - new_width) // 2
            image = image.crop((left, 0, left + new_width, image.height))
        elif img_ratio < target_ratio:
            # Immagine più alta, croppa height
            new_height = int(image.width / target_ratio)
            top = (image.height - new_height) // 2
            image = image.crop((0, top, image.width, top + new_height))

        # Resize a dimensioni finali
        image = image.resize((self.YOUTUBE_WIDTH, self.YOUTUBE_HEIGHT), Image.Resampling.LANCZOS)

        return image

    def _add_text_overlay(
        self,
        image: Image.Image,
        text: str,
        position: str,
        text_color: str,
        bg_color: str,
        bg_opacity: float
    ) -> Image.Image:
        """Aggiungi testo overlay"""
        draw = ImageDraw.Draw(image, 'RGBA')

        # Font (usa default se font file non trovato)
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 80)
        except:
            font = ImageFont.load_default()
            logger.warning("Font custom non trovato, uso default")

        # Calcola dimensioni testo
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        # Calcola posizione
        if position == "top":
            x = (self.YOUTUBE_WIDTH - text_width) // 2
            y = 50
        elif position == "center":
            x = (self.YOUTUBE_WIDTH - text_width) // 2
            y = (self.YOUTUBE_HEIGHT - text_height) // 2
        else:  # bottom
            x = (self.YOUTUBE_WIDTH - text_width) // 2
            y = self.YOUTUBE_HEIGHT - text_height - 50

        # Background rectangle con opacity
        padding = 20
        bg_rgba = self._hex_to_rgba(bg_color, bg_opacity)
        draw.rectangle(
            [x - padding, y - padding, x + text_width + padding, y + text_height + padding],
            fill=bg_rgba
        )

        # Testo
        draw.text((x, y), text, font=font, fill=text_color)

        return image

    def _enhance_for_ctr(self, image: Image.Image) -> Image.Image:
        """Ottimizzazioni automatiche per aumentare CTR"""
        # Saturazione +20%
        enhancer = ImageEnhance.Color(image)
        image = enhancer.enhance(1.2)

        # Contrasto +15%
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(1.15)

        # Nitidezza +30%
        enhancer = ImageEnhance.Sharpness(image)
        image = enhancer.enhance(1.3)

        return image

    def _save_optimized(self, image: Image.Image, output_path: Path):
        """Salva con compressione ottimale < 2MB"""
        quality = 95

        while quality > 50:
            # Save in memory per check dimensione
            buffer = BytesIO()
            image.save(buffer, format='JPEG', quality=quality, optimize=True)
            size_mb = buffer.tell() / (1024 * 1024)

            if size_mb <= self.MAX_SIZE_MB:
                # Dimensione OK, salva su file
                with open(output_path, 'wb') as f:
                    f.write(buffer.getvalue())
                logger.info(f"✅ Thumbnail salvata: {size_mb:.2f}MB (quality={quality})")
                return

            quality -= 5

        # Se ancora troppo grande, forza quality minimo
        image.save(output_path, format='JPEG', quality=50, optimize=True)
        logger.warning(f"Thumbnail salvata con quality=50 (potrebbe superare 2MB)")

    def _hex_to_rgba(self, hex_color: str, opacity: float) -> Tuple[int, int, int, int]:
        """Converti HEX color a RGBA tuple"""
        hex_color = hex_color.lstrip('#')
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        a = int(opacity * 255)
        return (r, g, b, a)

    @classmethod
    def get_available_styles(cls) -> Dict[str, str]:
        """Ritorna stili AI disponibili"""
        return cls.AI_STYLES.copy()
