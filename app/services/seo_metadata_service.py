"""
SEO Metadata Service
====================
Generazione automatica metadata SEO ottimizzati per video:
- Titolo accattivante e SEO-friendly
- Descrizione completa con keywords
- Hashtag rilevanti (numero configurabile)
- Tag SEO (numero configurabile)
- Thumbnail accattivante con text overlay

Usa OpenAI GPT-4 Vision per analisi intelligente del contenuto.
"""

import json
import logging
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List, Dict, Any, Callable
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
import openai

from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class SEOMetadataParams:
    """Parametri per generazione SEO metadata"""
    video_path: Path
    output_dir: Path

    # Parametri SEO
    num_hashtags: int = 10
    num_tags: int = 30
    language: str = "it"  # it, en, es, fr, de, pt, etc.

    # Parametri thumbnail
    generate_thumbnail: bool = True
    thumbnail_style: str = "modern"  # modern, minimal, bold, gradient
    thumbnail_text_overlay: bool = True

    # Parametri analisi video
    num_frames_to_analyze: int = 5  # Frame da campionare
    analyze_audio: bool = True  # Trascrivi audio per contesto

    # Target platform
    target_platform: str = "youtube"  # youtube, instagram, tiktok, facebook


class SEOMetadataService:
    """
    Servizio per generazione automatica metadata SEO ottimizzati.

    Features:
    - Analisi intelligente contenuto video con GPT-4 Vision
    - Generazione titolo SEO-optimized
    - Descrizione completa con keywords
    - Hashtag rilevanti (numero configurabile)
    - Tag SEO (numero configurabile)
    - Thumbnail accattivante con text overlay
    """

    SUPPORTED_LANGUAGES = [
        "it", "en", "es", "fr", "de", "pt", "ru", "ja", "zh", "ar", "hi"
    ]

    THUMBNAIL_STYLES = ["modern", "minimal", "bold", "gradient"]

    PLATFORMS = {
        "youtube": {
            "title_max_length": 100,
            "description_max_length": 5000,
            "thumbnail_size": (1280, 720),
            "hashtag_limit": 15
        },
        "instagram": {
            "title_max_length": 150,
            "description_max_length": 2200,
            "thumbnail_size": (1080, 1080),
            "hashtag_limit": 30
        },
        "tiktok": {
            "title_max_length": 150,
            "description_max_length": 2200,
            "thumbnail_size": (1080, 1920),
            "hashtag_limit": 20
        },
        "facebook": {
            "title_max_length": 255,
            "description_max_length": 63206,
            "thumbnail_size": (1200, 630),
            "hashtag_limit": 10
        }
    }

    def __init__(self, config):
        self.config = config
        self.ffmpeg_path = config.ffmpeg_path
        self.ffprobe_path = config.ffprobe_path

        # Configura OpenAI
        if not config.openai_api_key:
            raise ValueError("OpenAI API key non configurata! Aggiungi OPENAI_API_KEY al file .env")

        openai.api_key = config.openai_api_key

    def generate(
        self,
        params: SEOMetadataParams,
        progress_callback: Optional[Callable[[int, str], None]] = None
    ) -> Dict[str, Any]:
        """
        Genera metadata SEO completi per video

        Returns:
            {
                "title": "...",
                "description": "...",
                "hashtags": ["#tag1", "#tag2", ...],
                "tags": ["tag1", "tag2", ...],
                "thumbnail_path": "...",
                "language": "it",
                "platform": "youtube"
            }
        """
        try:
            if progress_callback:
                progress_callback(0, "Inizializzazione analisi SEO...")

            # Valida input
            self._validate_params(params)

            # Step 1: Estrai frame rappresentativi
            if progress_callback:
                progress_callback(10, "Estrazione frame rappresentativi...")
            frames = self._extract_frames(params.video_path, params.num_frames_to_analyze)

            # Step 2: Trascrizione audio (se richiesta)
            transcription = None
            if params.analyze_audio:
                if progress_callback:
                    progress_callback(30, "Trascrizione audio per contesto...")
                transcription = self._transcribe_audio(params.video_path)

            # Step 3: Analisi con GPT-4 Vision
            if progress_callback:
                progress_callback(50, "Analisi contenuto con AI...")
            analysis = self._analyze_content_with_ai(
                frames=frames,
                transcription=transcription,
                params=params
            )

            # Step 4: Genera metadata SEO
            if progress_callback:
                progress_callback(70, "Generazione metadata SEO...")
            metadata = self._generate_seo_metadata(analysis, params)

            # Step 5: Genera thumbnail (se richiesto)
            thumbnail_path = None
            if params.generate_thumbnail:
                if progress_callback:
                    progress_callback(85, "Creazione thumbnail accattivante...")
                thumbnail_path = self._generate_thumbnail(
                    video_path=params.video_path,
                    title=metadata["title"],
                    frames=frames,
                    params=params
                )

            # Risultato finale
            result = {
                "title": metadata["title"],
                "description": metadata["description"],
                "hashtags": metadata["hashtags"],
                "tags": metadata["tags"],
                "thumbnail_path": str(thumbnail_path) if thumbnail_path else None,
                "language": params.language,
                "platform": params.target_platform,
                "analysis": analysis  # Per debug/riferimento
            }

            if progress_callback:
                progress_callback(100, "Metadata SEO generati!")

            logger.info(f"SEO metadata generati: {len(metadata['hashtags'])} hashtag, {len(metadata['tags'])} tag")
            return result

        except Exception as e:
            logger.error(f"Errore generazione SEO metadata: {e}", exc_info=True)
            raise

    def _validate_params(self, params: SEOMetadataParams):
        """Valida parametri"""
        if not params.video_path.exists():
            raise FileNotFoundError(f"Video non trovato: {params.video_path}")

        if params.language not in self.SUPPORTED_LANGUAGES:
            raise ValueError(f"Lingua non supportata: {params.language}")

        if params.thumbnail_style not in self.THUMBNAIL_STYLES:
            raise ValueError(f"Stile thumbnail non supportato: {params.thumbnail_style}")

        if params.target_platform not in self.PLATFORMS:
            raise ValueError(f"Platform non supportata: {params.target_platform}")

        params.output_dir.mkdir(parents=True, exist_ok=True)

    def _extract_frames(self, video_path: Path, num_frames: int) -> List[np.ndarray]:
        """Estrae N frame rappresentativi dal video"""
        cap = cv2.VideoCapture(str(video_path))
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        # Calcola intervallo per frame uniformemente distribuiti
        interval = max(total_frames // (num_frames + 1), 1)

        frames = []
        for i in range(1, num_frames + 1):
            frame_idx = i * interval
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
            ret, frame = cap.read()

            if ret:
                # Ridimensiona per invio API (max 512px lato lungo)
                h, w = frame.shape[:2]
                max_dim = 512
                scale = min(max_dim / w, max_dim / h)
                new_w, new_h = int(w * scale), int(h * scale)
                frame_resized = cv2.resize(frame, (new_w, new_h))
                frames.append(frame_resized)

        cap.release()
        logger.info(f"Estratti {len(frames)} frame dal video")
        return frames

    def _transcribe_audio(self, video_path: Path) -> Optional[str]:
        """Trascrizione audio veloce per contesto (usa Whisper tiny)"""
        try:
            import whisper

            # Usa modello tiny per velocità
            model = whisper.load_model("tiny")
            result = model.transcribe(str(video_path), language=None)

            transcription = result.get("text", "").strip()
            logger.info(f"Audio trascritto: {len(transcription)} caratteri")
            return transcription

        except Exception as e:
            logger.warning(f"Trascrizione audio fallita: {e}")
            return None

    def _analyze_content_with_ai(
        self,
        frames: List[np.ndarray],
        transcription: Optional[str],
        params: SEOMetadataParams
    ) -> Dict[str, Any]:
        """Analizza contenuto video con GPT-4 Vision"""

        # Prepara prompt per GPT-4
        language_names = {
            "it": "italiano", "en": "english", "es": "español",
            "fr": "français", "de": "deutsch", "pt": "português"
        }
        lang_name = language_names.get(params.language, params.language)

        system_prompt = f"""Sei un esperto SEO specialist per {params.target_platform}.
Analizza questo video e identifica:
1. Topic principale e argomento
2. Tono/stile del contenuto (educativo, intrattenimento, tutorial, vlog, etc.)
3. Target audience
4. Keywords SEO rilevanti
5. Punti chiave del contenuto
6. Emozioni/engagement potenziale

Rispondi in {lang_name} in formato JSON."""

        user_prompt = f"""Analizza questi frame del video"""

        if transcription:
            user_prompt += f"\n\nTrascrizione audio:\n{transcription[:1000]}"  # Max 1000 char

        user_prompt += f"""

Fornisci analisi dettagliata in JSON:
{{
    "topic": "argomento principale",
    "category": "categoria",
    "tone": "tono/stile",
    "target_audience": "pubblico target",
    "key_points": ["punto1", "punto2", ...],
    "keywords": ["keyword1", "keyword2", ...],
    "emotions": ["emozione1", "emozione2"],
    "engagement_score": 1-10
}}"""

        try:
            # Converti primo frame in base64 per Vision API
            import base64
            import io
            from PIL import Image

            frame_pil = Image.fromarray(cv2.cvtColor(frames[0], cv2.COLOR_BGR2RGB))
            buffer = io.BytesIO()
            frame_pil.save(buffer, format="JPEG", quality=85)
            frame_b64 = base64.b64encode(buffer.getvalue()).decode()

            # Chiamata GPT-4 Vision
            response = openai.ChatCompletion.create(
                model="gpt-4-vision-preview",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": user_prompt},
                            {
                                "type": "image_url",
                                "image_url": f"data:image/jpeg;base64,{frame_b64}"
                            }
                        ]
                    }
                ],
                max_tokens=1000,
                temperature=0.7
            )

            analysis_text = response.choices[0].message.content

            # Parse JSON dalla risposta
            analysis = json.loads(analysis_text)
            logger.info(f"Analisi AI completata: topic={analysis.get('topic')}")
            return analysis

        except Exception as e:
            logger.error(f"Errore analisi AI: {e}")
            # Fallback: analisi base
            return {
                "topic": "Video",
                "category": "General",
                "tone": "informativo",
                "target_audience": "generale",
                "key_points": ["Contenuto video"],
                "keywords": ["video"],
                "emotions": ["interesse"],
                "engagement_score": 5
            }

    def _generate_seo_metadata(
        self,
        analysis: Dict[str, Any],
        params: SEOMetadataParams
    ) -> Dict[str, Any]:
        """Genera metadata SEO ottimizzati da analisi AI"""

        platform_config = self.PLATFORMS[params.target_platform]

        # Prompt per generazione metadata
        language_names = {
            "it": "italiano", "en": "english", "es": "español",
            "fr": "français", "de": "deutsch", "pt": "português"
        }
        lang_name = language_names.get(params.language, params.language)

        prompt = f"""Sei un esperto SEO per {params.target_platform}.

Analisi video:
- Topic: {analysis.get('topic')}
- Categoria: {analysis.get('category')}
- Tono: {analysis.get('tone')}
- Target: {analysis.get('target_audience')}
- Keywords: {', '.join(analysis.get('keywords', []))}

Genera in {lang_name}:

1. TITOLO SEO-optimized ({platform_config['title_max_length']} caratteri max):
   - Accattivante, clickbait etico
   - Include keyword principale
   - Provoca curiosità
   - Emoji strategici se appropriato

2. DESCRIZIONE completa ({platform_config['description_max_length']} caratteri max):
   - Primi 2-3 righe: hook immediato
   - Punti chiave del contenuto
   - Call-to-action
   - Keywords distribuite naturalmente

3. {params.num_hashtags} HASHTAG rilevanti:
   - Mix: popolari + di nicchia
   - Tutti lowercase con #

4. {params.num_tags} TAG SEO:
   - Keywords principali e long-tail
   - Sinonimi e varianti
   - Senza #

Formato JSON:
{{
    "title": "...",
    "description": "...",
    "hashtags": ["#tag1", "#tag2", ...],
    "tags": ["tag1", "tag2", ...]
}}"""

        try:
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": f"Sei un SEO specialist per {params.target_platform}. Rispondi SOLO in JSON valido."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=2000,
                temperature=0.8
            )

            metadata_text = response.choices[0].message.content.strip()

            # Rimuovi markdown code block se presente
            if metadata_text.startswith("```"):
                metadata_text = metadata_text.split("```")[1]
                if metadata_text.startswith("json"):
                    metadata_text = metadata_text[4:]

            metadata = json.loads(metadata_text)

            # Valida e tronca se necessario
            metadata["title"] = metadata["title"][:platform_config["title_max_length"]]
            metadata["description"] = metadata["description"][:platform_config["description_max_length"]]
            metadata["hashtags"] = metadata["hashtags"][:params.num_hashtags]
            metadata["tags"] = metadata["tags"][:params.num_tags]

            return metadata

        except Exception as e:
            logger.error(f"Errore generazione metadata: {e}")
            # Fallback
            return {
                "title": f"{analysis.get('topic', 'Video')} - Tutorial Completo",
                "description": f"Guarda questo video su {analysis.get('topic', 'argomento interessante')}!",
                "hashtags": [f"#{kw.replace(' ', '')}" for kw in analysis.get('keywords', ['video'])[:params.num_hashtags]],
                "tags": analysis.get('keywords', ['video'])[:params.num_tags]
            }

    def _generate_thumbnail(
        self,
        video_path: Path,
        title: str,
        frames: List[np.ndarray],
        params: SEOMetadataParams
    ) -> Path:
        """Genera thumbnail accattivante con text overlay"""

        platform_config = self.PLATFORMS[params.target_platform]
        size = platform_config["thumbnail_size"]

        # Usa frame più interessante (al centro)
        base_frame = frames[len(frames) // 2]

        # Converti in PIL
        img = Image.fromarray(cv2.cvtColor(base_frame, cv2.COLOR_BGR2RGB))
        img = img.resize(size, Image.Resampling.LANCZOS)

        # Applica effetti in base allo stile
        if params.thumbnail_style == "modern":
            img = self._apply_modern_style(img)
        elif params.thumbnail_style == "bold":
            img = self._apply_bold_style(img)
        elif params.thumbnail_style == "gradient":
            img = self._apply_gradient_style(img)

        # Aggiungi text overlay se richiesto
        if params.thumbnail_text_overlay:
            img = self._add_text_overlay(img, title, params.thumbnail_style)

        # Salva
        output_path = params.output_dir / f"thumbnail_seo_{params.target_platform}.jpg"
        img.save(output_path, "JPEG", quality=95, optimize=True)

        logger.info(f"Thumbnail generata: {output_path}")
        return output_path

    def _apply_modern_style(self, img: Image.Image) -> Image.Image:
        """Stile moderno: saturazione +20%, contrasto +10%, leggera sharpness"""
        enhancer = ImageEnhance.Color(img)
        img = enhancer.enhance(1.2)

        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(1.1)

        img = img.filter(ImageFilter.SHARPEN)
        return img

    def _apply_bold_style(self, img: Image.Image) -> Image.Image:
        """Stile bold: alto contrasto, saturazione alta"""
        enhancer = ImageEnhance.Color(img)
        img = enhancer.enhance(1.4)

        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(1.3)

        return img

    def _apply_gradient_style(self, img: Image.Image) -> Image.Image:
        """Stile gradient: overlay gradiente colorato"""
        overlay = Image.new("RGBA", img.size, (255, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)

        # Gradiente dal basso (nero semi-trasparente)
        height = img.size[1]
        for i in range(height // 2):
            alpha = int((i / (height // 2)) * 180)
            draw.rectangle(
                [(0, height - i), (img.size[0], height)],
                fill=(0, 0, 0, alpha)
            )

        img = img.convert("RGBA")
        img = Image.alpha_composite(img, overlay)
        return img.convert("RGB")

    def _add_text_overlay(self, img: Image.Image, title: str, style: str) -> Image.Image:
        """Aggiungi titolo overlay sul thumbnail"""
        draw = ImageDraw.Draw(img)

        # Tenta di caricare font
        try:
            font_size = int(img.size[0] * 0.08)  # 8% larghezza
            font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", font_size)
        except:
            font = ImageFont.load_default()

        # Tronca titolo se troppo lungo
        max_chars = 50
        display_title = title if len(title) <= max_chars else title[:max_chars - 3] + "..."

        # Calcola posizione (centrato in basso)
        bbox = draw.textbbox((0, 0), display_title, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        x = (img.size[0] - text_width) // 2
        y = img.size[1] - text_height - int(img.size[1] * 0.1)

        # Background semi-trasparente
        padding = 20
        bg_bbox = [
            x - padding,
            y - padding,
            x + text_width + padding,
            y + text_height + padding
        ]

        # Overlay nero semi-trasparente
        overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        overlay_draw.rectangle(bg_bbox, fill=(0, 0, 0, 200))

        img = img.convert("RGBA")
        img = Image.alpha_composite(img, overlay)

        # Disegna testo
        draw = ImageDraw.Draw(img)
        draw.text((x, y), display_title, fill=(255, 255, 255), font=font)

        return img.convert("RGB")
