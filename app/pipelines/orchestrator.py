"""
Pipeline Orchestrator - Sistema AUTO
=====================================
CORE della funzionalità AUTO richiesta da Ettore.

Orchestrazione automatica di job multipli in sequenza:
1. Chromakey processing
2. Thumbnail generation
3. Translation
4. YouTube upload

Ogni step può essere attivato/disattivato dinamicamente.
Output di uno step diventa input del successivo.

Esempio Pipeline AUTO completa:
- Upload video + logo
- Chromakey (aggiungi logo call-to-action)
- Genera thumbnail AI
- Traduci video in 3 lingue
- Upload su YouTube con thumbnail

"""

import logging
from typing import Dict, Any, Optional, Callable, List
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.job import Job, JobType, JobStatus
from app.models.pipeline import Pipeline, PipelineStatus
from app.services.chromakey_service import ChromakeyService, ChromakeyParams
from app.services.translation_service import TranslationService, TranslationParams
from app.services.thumbnail_service import ThumbnailService, ThumbnailParams
from app.services.youtube_service import YouTubeService, YouTubeUploadParams

logger = logging.getLogger(__name__)


@dataclass
class PipelineStep:
    """Singolo step pipeline"""
    step_number: int
    job_type: JobType
    enabled: bool
    parameters: Dict[str, Any]


class PipelineOrchestrator:
    """
    Orchestratore pipeline automatiche.

    Gestisce esecuzione sequenziale di job multipli,
    passando output come input tra step.
    """

    def __init__(self, db: Session, config: Optional[Any] = None):
        """
        Inizializza orchestratore

        Args:
            db: Database session per tracking
            config: Configurazione (default: settings globale)
        """
        self.db = db
        self.config = config or settings

        # Inizializza servizi
        self.chromakey_service = ChromakeyService(config)
        self.translation_service = TranslationService(config)
        self.thumbnail_service = ThumbnailService(config)
        self.youtube_service = YouTubeService(config)

        logger.info("✅ PipelineOrchestrator inizializzato")

    def execute_pipeline(
        self,
        pipeline: Pipeline,
        progress_callback: Optional[Callable[[int, str], bool]] = None
    ) -> Dict[str, Any]:
        """
        Esegue pipeline completa

        Args:
            pipeline: Oggetto Pipeline da database
            progress_callback: Callback progresso globale

        Returns:
            dict: Risultato finale pipeline con output di tutti gli step

        Raises:
            RuntimeError: Se pipeline fallisce e stop_on_error=True
        """
        logger.info(f"🚀 Avvio esecuzione pipeline: {pipeline.name} (ID: {pipeline.id})")
        logger.info(f"   Totale step: {pipeline.total_steps}")
        logger.info(f"   Stop on error: {pipeline.stop_on_error}")

        # Aggiorna stato pipeline
        pipeline.status = PipelineStatus.RUNNING
        pipeline.started_at = datetime.utcnow()
        pipeline.message = "Pipeline avviata..."
        self.db.commit()

        if progress_callback:
            progress_callback(0, f"Pipeline {pipeline.name} avviata")

        results = {}
        current_files = pipeline.input_files or {}

        try:
            # Esegui ogni step abilitato
            for step_data in pipeline.enabled_steps:
                step_num = step_data['step_number']
                job_type = JobType(step_data['job_type'])
                params = step_data['parameters']

                logger.info(f"📋 Step {step_num}/{pipeline.total_steps}: {job_type.value}")

                # Aggiorna pipeline
                pipeline.current_step = step_num
                pipeline.message = f"Esecuzione {job_type.value}..."
                self.db.commit()

                # Calcola progress globale
                global_progress = int((step_num / pipeline.total_steps) * 100)
                if progress_callback:
                    progress_callback(global_progress, f"Step {step_num}: {job_type.value}")

                # Crea Job nel database per tracking
                job = self._create_job(pipeline, job_type, params, current_files)

                try:
                    # Esegui step
                    step_result = self._execute_step(
                        job_type,
                        params,
                        current_files,
                        lambda p, m: self._step_progress_callback(job, p, m, progress_callback)
                    )

                    # Aggiorna job success
                    job.status = JobStatus.COMPLETED
                    job.completed_at = datetime.utcnow()
                    job.result = step_result
                    job.output_files = step_result.get('output_files', {})
                    self.db.commit()

                    # Accumula risultati
                    results[job_type.value] = step_result

                    # Output diventa input per prossimo step
                    if step_result.get('output_files'):
                        current_files.update(step_result['output_files'])

                    logger.info(f"✅ Step {step_num} completato: {job_type.value}")

                except Exception as e:
                    # Step fallito
                    logger.error(f"❌ Step {step_num} fallito: {e}")

                    job.status = JobStatus.FAILED
                    job.error = str(e)
                    job.completed_at = datetime.utcnow()
                    self.db.commit()

                    results[job_type.value] = {"success": False, "error": str(e)}

                    if pipeline.stop_on_error:
                        raise RuntimeError(f"Pipeline interrotta: step {step_num} fallito: {e}")

            # Pipeline completata
            pipeline.status = PipelineStatus.COMPLETED
            pipeline.completed_at = datetime.utcnow()
            pipeline.output_files = current_files
            pipeline.result = results
            pipeline.message = "Pipeline completata con successo!"
            self.db.commit()

            if progress_callback:
                progress_callback(100, "✅ Pipeline completata!")

            logger.info(f"✅ Pipeline {pipeline.name} completata con successo")

            return {
                "success": True,
                "pipeline_id": str(pipeline.id),
                "results": results,
                "output_files": current_files
            }

        except Exception as e:
            # Pipeline fallita
            logger.error(f"❌ Pipeline {pipeline.name} fallita: {e}")

            pipeline.status = PipelineStatus.FAILED
            pipeline.error = str(e)
            pipeline.completed_at = datetime.utcnow()
            self.db.commit()

            if progress_callback:
                progress_callback(-1, f"❌ Pipeline fallita: {e}")

            raise

    def _execute_step(
        self,
        job_type: JobType,
        parameters: Dict[str, Any],
        input_files: Dict[str, str],
        progress_callback: Optional[Callable]
    ) -> Dict[str, Any]:
        """
        Esegue singolo step della pipeline

        Args:
            job_type: Tipo di job
            parameters: Parametri specifici job
            input_files: File input da step precedenti
            progress_callback: Callback progresso

        Returns:
            dict: Risultato step con output_files

        Raises:
            ValueError: Se job_type non supportato
            RuntimeError: Se esecuzione fallisce
        """

        if job_type == JobType.CHROMAKEY:
            return self._execute_chromakey(parameters, input_files, progress_callback)

        elif job_type == JobType.THUMBNAIL:
            return self._execute_thumbnail(parameters, input_files, progress_callback)

        elif job_type == JobType.TRANSLATION:
            return self._execute_translation(parameters, input_files, progress_callback)

        elif job_type == JobType.YOUTUBE_UPLOAD:
            return self._execute_youtube_upload(parameters, input_files, progress_callback)

        else:
            raise ValueError(f"Job type non supportato: {job_type}")

    def _execute_chromakey(
        self,
        params: Dict[str, Any],
        input_files: Dict[str, str],
        progress_callback: Optional[Callable]
    ) -> Dict[str, Any]:
        """Esegue chromakey processing"""

        # Resolve paths da input_files
        foreground_path = Path(input_files.get('foreground') or params['foreground_path'])
        background_path = Path(input_files.get('background') or params['background_path'])
        output_path = Path(self.config.output_dir) / f"chromakey_{datetime.now().timestamp()}.mp4"

        # Crea parametri
        chromakey_params = ChromakeyParams(
            foreground_path=foreground_path,
            background_path=background_path,
            output_path=output_path,
            start_time=params.get('start_time', 0.0),
            duration=params.get('duration'),
            lower_hsv=tuple(params.get('lower_hsv', [40, 40, 40])),
            upper_hsv=tuple(params.get('upper_hsv', [80, 255, 255])),
            audio_mode=params.get('audio_mode', 'synced'),
            position=(params.get('x_pos', 0), params.get('y_pos', 0)),
            scale=params.get('scale', 1.0),
            opacity=params.get('opacity', 1.0),
            fast_mode=params.get('fast_mode', True),
            gpu_accel=params.get('gpu_accel', False),
            logo_path=Path(input_files['logo']) if 'logo' in input_files else None,
            logo_position=(params.get('logo_x', 0), params.get('logo_y', 0)) if 'logo' in input_files else None
        )

        # Esegui
        result = self.chromakey_service.process(chromakey_params, progress_callback)

        # Aggiungi output_files per prossimo step
        result['output_files'] = {
            'chromakey_output': str(output_path),
            'video': str(output_path)  # Alias generico
        }

        return result

    def _execute_thumbnail(
        self,
        params: Dict[str, Any],
        input_files: Dict[str, str],
        progress_callback: Optional[Callable]
    ) -> Dict[str, Any]:
        """Esegue thumbnail generation"""

        output_path = Path(self.config.output_dir) / f"thumbnail_{datetime.now().timestamp()}.jpg"

        # Resolve video path se source_type = frame
        video_path = None
        if params.get('source_type') == 'frame':
            video_path = Path(input_files.get('video') or params.get('video_path'))

        upload_image_path = None
        if params.get('source_type') == 'upload':
            upload_image_path = Path(params.get('upload_image_path'))

        thumbnail_params = ThumbnailParams(
            output_path=output_path,
            source_type=params['source_type'],
            ai_description=params.get('ai_description'),
            ai_style=params.get('ai_style'),
            upload_image_path=upload_image_path,
            video_path=video_path,
            frame_timestamp=params.get('frame_timestamp', 0.0),
            text=params.get('text'),
            text_position=params.get('text_position', 'center'),
            text_color=params.get('text_color', '#FFFFFF'),
            text_bg_color=params.get('text_bg_color', '#000000'),
            text_bg_opacity=params.get('text_bg_opacity', 0.7),
            enhance_ctr=params.get('enhance_ctr', True)
        )

        result = self.thumbnail_service.generate(thumbnail_params, progress_callback)

        result['output_files'] = {
            'thumbnail': str(output_path)
        }

        return result

    def _execute_translation(
        self,
        params: Dict[str, Any],
        input_files: Dict[str, str],
        progress_callback: Optional[Callable]
    ) -> Dict[str, Any]:
        """Esegue translation"""

        # Resolve video path
        input_video_path = Path(input_files.get('video') or params['input_video_path'])
        output_path = Path(self.config.output_dir) / f"translated_{params['target_language']}_{datetime.now().timestamp()}.mp4"

        translation_params = TranslationParams(
            input_video_path=input_video_path,
            output_video_path=output_path,
            target_language=params['target_language'],
            source_language=params.get('source_language', 'auto'),
            enable_lipsync=params.get('enable_lipsync', False)
        )

        result = self.translation_service.translate(translation_params, progress_callback)

        result['output_files'] = {
            f'video_{params["target_language"]}': str(output_path)
        }

        return result

    def _execute_youtube_upload(
        self,
        params: Dict[str, Any],
        input_files: Dict[str, str],
        progress_callback: Optional[Callable]
    ) -> Dict[str, Any]:
        """Esegue YouTube upload"""

        # Resolve paths
        video_path = Path(input_files.get('video') or params['video_path'])
        thumbnail_path = Path(input_files['thumbnail']) if 'thumbnail' in input_files else None

        upload_params = YouTubeUploadParams(
            video_path=video_path,
            title=params['title'],
            description=params['description'],
            tags=params.get('tags', []),
            category_id=params.get('category_id', '22'),
            privacy_status=params.get('privacy_status', 'private'),
            thumbnail_path=thumbnail_path
        )

        result = self.youtube_service.upload(upload_params, progress_callback)

        return result

    def _create_job(
        self,
        pipeline: Pipeline,
        job_type: JobType,
        parameters: Dict[str, Any],
        input_files: Dict[str, str]
    ) -> Job:
        """Crea job nel database"""
        job = Job(
            user_id=pipeline.user_id,
            pipeline_id=pipeline.id,
            job_type=job_type,
            status=JobStatus.PROCESSING,
            parameters=parameters,
            input_files=input_files,
            started_at=datetime.utcnow()
        )

        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)

        return job

    def _step_progress_callback(
        self,
        job: Job,
        progress: int,
        message: str,
        global_callback: Optional[Callable]
    ) -> bool:
        """Callback progresso step - aggiorna job e chiama callback globale"""

        # Aggiorna job
        job.progress = progress
        job.message = message
        self.db.commit()

        # Chiama callback globale se presente
        if global_callback:
            return global_callback(progress, message)

        return True  # Continue
