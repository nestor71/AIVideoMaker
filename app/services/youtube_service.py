"""
YouTube Service - Video Upload
================================
Servizio indipendente per upload video su YouTube con:
- Autenticazione OAuth2
- Upload video con metadata
- Upload thumbnail custom
- Gestione privacy settings

Completamente testabile, nessuna dipendenza da FastAPI.
"""

import logging
from pathlib import Path
from typing import Optional, Callable, Dict, Any
from dataclasses import dataclass
import pickle
import os

from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class YouTubeUploadParams:
    """Parametri upload YouTube"""
    video_path: Path
    title: str
    description: str
    tags: list
    category_id: str = "22"  # People & Blogs default
    privacy_status: str = "private"  # private, public, unlisted
    thumbnail_path: Optional[Path] = None


class YouTubeService:
    """
    Servizio upload YouTube professionale.

    Gestisce OAuth2, upload video, thumbnail, metadata.
    """

    SCOPES = ['https://www.googleapis.com/auth/youtube.upload']

    def __init__(self, config: Optional[Any] = None):
        """Inizializza service"""
        self.config = config or settings
        self.client_secrets_file = self.config.youtube_client_secrets_file
        self.credentials = None
        self.youtube = None

        self._load_credentials()

    def _load_credentials(self):
        """Carica o genera credentials OAuth2"""
        token_file = Path('youtube_token.pickle')

        # Carica token salvato se esiste
        if token_file.exists():
            with open(token_file, 'rb') as token:
                self.credentials = pickle.load(token)

        # Se token non valido, rigenera
        if not self.credentials or not self.credentials.valid:
            if self.credentials and self.credentials.expired and self.credentials.refresh_token:
                # Refresh token
                self.credentials.refresh(Request())
            else:
                # Flow OAuth2 completo
                if not self.client_secrets_file.exists():
                    raise FileNotFoundError(
                        f"File client_secrets.json non trovato: {self.client_secrets_file}. "
                        "Scaricalo da Google Cloud Console."
                    )

                flow = InstalledAppFlow.from_client_secrets_file(
                    str(self.client_secrets_file),
                    self.SCOPES
                )
                self.credentials = flow.run_local_server(port=0)

            # Salva token per prossima volta
            with open(token_file, 'wb') as token:
                pickle.dump(self.credentials, token)

        # Build YouTube API client
        self.youtube = build('youtube', 'v3', credentials=self.credentials)
        logger.info("✅ YouTube API autenticato")

    def upload(
        self,
        params: YouTubeUploadParams,
        progress_callback: Optional[Callable[[int, str], bool]] = None
    ) -> Dict[str, Any]:
        """
        Upload video su YouTube

        Args:
            params: Parametri upload
            progress_callback: Callback progresso

        Returns:
            dict: Risultato con 'success', 'video_id', 'url'

        Raises:
            ValueError: Se parametri invalidi
            RuntimeError: Se upload fallisce
        """
        logger.info(f"📤 Avvio upload YouTube")
        logger.info(f"   Video: {params.video_path}")
        logger.info(f"   Titolo: {params.title}")
        logger.info(f"   Privacy: {params.privacy_status}")

        self._validate_params(params)

        if progress_callback:
            progress_callback(5, "Preparazione upload...")

        try:
            # Step 1: Upload video
            if progress_callback:
                progress_callback(10, "Upload video su YouTube...")

            video_id = self._upload_video(params, progress_callback)
            logger.info(f"✅ Video uploaded: ID={video_id}")

            # Step 2: Upload thumbnail se fornito
            if params.thumbnail_path:
                if progress_callback:
                    progress_callback(90, "Upload thumbnail...")

                self._upload_thumbnail(video_id, params.thumbnail_path)
                logger.info(f"✅ Thumbnail uploaded")

            if progress_callback:
                progress_callback(100, "✅ Upload completato!")

            video_url = f"https://www.youtube.com/watch?v={video_id}"

            return {
                "success": True,
                "video_id": video_id,
                "url": video_url,
                "privacy_status": params.privacy_status
            }

        except Exception as e:
            logger.error(f"❌ Errore upload YouTube: {e}")
            raise

    def _validate_params(self, params: YouTubeUploadParams):
        """Valida parametri"""
        if not params.video_path.exists():
            raise ValueError(f"Video non trovato: {params.video_path}")

        if not params.title:
            raise ValueError("Titolo richiesto")

        if params.privacy_status not in ["private", "public", "unlisted"]:
            raise ValueError("privacy_status deve essere 'private', 'public' o 'unlisted'")

        if params.thumbnail_path and not params.thumbnail_path.exists():
            raise ValueError(f"Thumbnail non trovata: {params.thumbnail_path}")

    def _upload_video(
        self,
        params: YouTubeUploadParams,
        progress_callback: Optional[Callable]
    ) -> str:
        """Upload video con metadata"""
        body = {
            'snippet': {
                'title': params.title,
                'description': params.description,
                'tags': params.tags,
                'categoryId': params.category_id
            },
            'status': {
                'privacyStatus': params.privacy_status,
                'selfDeclaredMadeForKids': False
            }
        }

        # Prepare media file
        media = MediaFileUpload(
            str(params.video_path),
            chunksize=-1,  # Upload in singolo chunk
            resumable=True
        )

        # Insert video
        request = self.youtube.videos().insert(
            part=','.join(body.keys()),
            body=body,
            media_body=media
        )

        response = None
        while response is None:
            status, response = request.next_chunk()

            if status and progress_callback:
                progress_pct = int(10 + (status.progress() * 75))  # 10-85%
                progress_callback(
                    progress_pct,
                    f"Upload in corso: {int(status.progress() * 100)}%"
                )

        video_id = response['id']
        return video_id

    def _upload_thumbnail(self, video_id: str, thumbnail_path: Path):
        """Upload thumbnail custom"""
        media = MediaFileUpload(
            str(thumbnail_path),
            mimetype='image/jpeg',
            resumable=True
        )

        request = self.youtube.thumbnails().set(
            videoId=video_id,
            media_body=media
        )

        response = request.execute()
        return response

    def get_video_info(self, video_id: str) -> Dict[str, Any]:
        """Ottieni info video"""
        request = self.youtube.videos().list(
            part='snippet,status,statistics',
            id=video_id
        )

        response = request.execute()

        if not response['items']:
            raise ValueError(f"Video non trovato: {video_id}")

        return response['items'][0]

    def delete_video(self, video_id: str) -> bool:
        """Elimina video"""
        try:
            request = self.youtube.videos().delete(id=video_id)
            request.execute()
            logger.info(f"✅ Video eliminato: {video_id}")
            return True
        except Exception as e:
            logger.error(f"Errore eliminazione video: {e}")
            return False

    def update_privacy(self, video_id: str, privacy_status: str) -> bool:
        """Aggiorna privacy video"""
        try:
            body = {
                'id': video_id,
                'status': {
                    'privacyStatus': privacy_status
                }
            }

            request = self.youtube.videos().update(
                part='status',
                body=body
            )

            request.execute()
            logger.info(f"✅ Privacy aggiornata: {video_id} -> {privacy_status}")
            return True

        except Exception as e:
            logger.error(f"Errore aggiornamento privacy: {e}")
            return False
