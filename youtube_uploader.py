"""
YouTube Uploader Module
Gestisce autenticazione OAuth2 e upload video su YouTube
"""

import os
import pickle
import logging
from pathlib import Path
from typing import Optional, Dict, List, Callable
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

logger = logging.getLogger(__name__)

# Scopes richiesti per YouTube Data API
SCOPES = ['https://www.googleapis.com/auth/youtube.upload']

# File per salvare le credenziali utente
CREDENTIALS_DIR = Path("credentials")
CREDENTIALS_DIR.mkdir(exist_ok=True)
TOKEN_FILE = CREDENTIALS_DIR / "youtube_token.pickle"


class YouTubeUploader:
    """
    Gestisce l'autenticazione OAuth2 e l'upload di video su YouTube
    """

    def __init__(self, client_secrets_file: str = "client_secrets.json"):
        """
        Inizializza l'uploader

        Args:
            client_secrets_file: Path al file JSON con le credenziali OAuth2
                                Ottienilo da: https://console.cloud.google.com/apis/credentials
        """
        self.client_secrets_file = client_secrets_file
        self.credentials: Optional[Credentials] = None
        self.youtube = None

    def is_authenticated(self) -> bool:
        """Verifica se l'utente è già autenticato"""
        return TOKEN_FILE.exists() and self._load_credentials()

    def _load_credentials(self) -> bool:
        """Carica credenziali salvate"""
        try:
            if TOKEN_FILE.exists():
                with open(TOKEN_FILE, 'rb') as token:
                    self.credentials = pickle.load(token)

                # Verifica se le credenziali sono valide
                if self.credentials and self.credentials.valid:
                    logger.info("Credenziali YouTube caricate con successo")
                    return True

                # Se scadute, prova a rinnovarle
                if self.credentials and self.credentials.expired and self.credentials.refresh_token:
                    logger.info("Rinnovo credenziali YouTube...")
                    self.credentials.refresh(Request())
                    self._save_credentials()
                    return True

            return False
        except Exception as e:
            logger.error(f"Errore caricamento credenziali: {e}")
            return False

    def _save_credentials(self):
        """Salva credenziali su disco"""
        try:
            with open(TOKEN_FILE, 'wb') as token:
                pickle.dump(self.credentials, token)
            logger.info("Credenziali YouTube salvate")
        except Exception as e:
            logger.error(f"Errore salvataggio credenziali: {e}")

    def get_auth_url(self, redirect_uri: str = "http://localhost:8000/api/youtube/oauth2callback") -> str:
        """
        Genera URL per OAuth2 authorization

        Args:
            redirect_uri: URL di callback dopo autorizzazione

        Returns:
            URL da aprire nel browser per autorizzare l'app
        """
        try:
            # Verifica che il file client_secrets.json esista
            if not os.path.exists(self.client_secrets_file):
                raise FileNotFoundError(
                    f"File {self.client_secrets_file} non trovato.\n"
                    "Crea un progetto su Google Cloud Console:\n"
                    "1. Vai su https://console.cloud.google.com/\n"
                    "2. Crea un nuovo progetto\n"
                    "3. Abilita YouTube Data API v3\n"
                    "4. Crea credenziali OAuth 2.0\n"
                    "5. Scarica il JSON e salvalo come client_secrets.json"
                )

            flow = Flow.from_client_secrets_file(
                self.client_secrets_file,
                scopes=SCOPES,
                redirect_uri=redirect_uri
            )

            auth_url, _ = flow.authorization_url(
                access_type='offline',
                include_granted_scopes='true',
                prompt='consent'
            )

            # Salva il flow per usarlo nel callback
            self._current_flow = flow

            logger.info(f"URL autorizzazione generato: {auth_url}")
            return auth_url

        except Exception as e:
            logger.error(f"Errore generazione URL auth: {e}")
            raise

    def handle_oauth_callback(self, authorization_response: str) -> bool:
        """
        Completa il flusso OAuth2 con il codice di autorizzazione

        Args:
            authorization_response: URL completo di callback con il code

        Returns:
            True se autenticazione completata con successo
        """
        try:
            if not hasattr(self, '_current_flow'):
                raise Exception("Flow OAuth2 non inizializzato. Chiama get_auth_url() prima.")

            # Completa il flow
            self._current_flow.fetch_token(authorization_response=authorization_response)
            self.credentials = self._current_flow.credentials

            # Salva credenziali
            self._save_credentials()

            logger.info("Autenticazione YouTube completata")
            return True

        except Exception as e:
            logger.error(f"Errore callback OAuth: {e}")
            return False

    def disconnect(self):
        """Disconnette l'account YouTube rimuovendo le credenziali salvate"""
        try:
            if TOKEN_FILE.exists():
                TOKEN_FILE.unlink()
            self.credentials = None
            self.youtube = None
            logger.info("Account YouTube disconnesso")
            return True
        except Exception as e:
            logger.error(f"Errore disconnessione: {e}")
            return False

    def _initialize_youtube_service(self):
        """Inizializza il servizio YouTube API"""
        if not self.credentials:
            if not self._load_credentials():
                raise Exception("Credenziali non trovate. Esegui autenticazione prima.")

        if not self.youtube:
            self.youtube = build('youtube', 'v3', credentials=self.credentials)
            logger.info("Servizio YouTube API inizializzato")

    def upload_video(
        self,
        video_path: str,
        title: str,
        description: str = "",
        tags: List[str] = None,
        category_id: str = "22",  # 22 = People & Blogs
        privacy_status: str = "private",  # private, unlisted, public
        progress_callback: Optional[Callable[[int], bool]] = None
    ) -> Dict:
        """
        Carica un video su YouTube

        Args:
            video_path: Path del file video da caricare
            title: Titolo del video
            description: Descrizione del video
            tags: Lista di tag/parole chiave
            category_id: ID categoria YouTube (22=People & Blogs, 28=Science & Technology)
            privacy_status: Visibilità ('private', 'unlisted', 'public')
            progress_callback: Funzione callback per progress (0-100)

        Returns:
            Dict con informazioni sul video caricato (video_id, url, etc.)
        """
        try:
            # Verifica che il file esista
            if not os.path.exists(video_path):
                raise FileNotFoundError(f"Video non trovato: {video_path}")

            # Inizializza servizio YouTube
            self._initialize_youtube_service()

            # Prepara metadata video
            body = {
                'snippet': {
                    'title': title,
                    'description': description,
                    'tags': tags or [],
                    'categoryId': category_id
                },
                'status': {
                    'privacyStatus': privacy_status,
                    'selfDeclaredMadeForKids': False
                }
            }

            # Prepara upload
            media = MediaFileUpload(
                video_path,
                mimetype='video/*',
                resumable=True,
                chunksize=1024*1024  # 1MB chunks
            )

            logger.info(f"Avvio upload video: {title}")

            # Esegui upload
            request = self.youtube.videos().insert(
                part=','.join(body.keys()),
                body=body,
                media_body=media
            )

            response = None
            while response is None:
                status, response = request.next_chunk()

                if status and progress_callback:
                    progress = int(status.progress() * 100)

                    # Chiama callback, se ritorna False interrompi
                    if not progress_callback(progress):
                        logger.info("Upload interrotto dall'utente")
                        return {
                            'success': False,
                            'error': 'Upload interrotto dall\'utente'
                        }

            # Upload completato
            video_id = response['id']
            video_url = f"https://www.youtube.com/watch?v={video_id}"

            logger.info(f"Video caricato con successo: {video_url}")

            return {
                'success': True,
                'video_id': video_id,
                'video_url': video_url,
                'title': title,
                'privacy_status': privacy_status
            }

        except Exception as e:
            logger.error(f"Errore upload video: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def get_channel_info(self) -> Dict:
        """
        Ottiene informazioni sul canale YouTube autenticato

        Returns:
            Dict con info canale (nome, subscribers, etc.)
        """
        try:
            self._initialize_youtube_service()

            # Richiedi info canale
            request = self.youtube.channels().list(
                part='snippet,statistics',
                mine=True
            )

            response = request.execute()

            if not response.get('items'):
                return {
                    'success': False,
                    'error': 'Nessun canale trovato'
                }

            channel = response['items'][0]
            snippet = channel['snippet']
            stats = channel['statistics']

            return {
                'success': True,
                'channel_id': channel['id'],
                'title': snippet['title'],
                'description': snippet.get('description', ''),
                'thumbnail': snippet['thumbnails']['default']['url'],
                'subscriber_count': stats.get('subscriberCount', '0'),
                'video_count': stats.get('videoCount', '0'),
                'view_count': stats.get('viewCount', '0')
            }

        except Exception as e:
            logger.error(f"Errore get channel info: {e}")
            return {
                'success': False,
                'error': str(e)
            }


# ============================================================================
# ISTRUZIONI PER CONFIGURAZIONE GOOGLE CLOUD
# ============================================================================

"""
SETUP GOOGLE CLOUD CONSOLE PER YOUTUBE API:

1. Vai su https://console.cloud.google.com/

2. Crea un nuovo progetto:
   - Clicca "Seleziona un progetto" in alto
   - Clicca "Nuovo progetto"
   - Nome: "AIVideoMaker YouTube Uploader"
   - Clicca "Crea"

3. Abilita YouTube Data API v3:
   - Menu ≡ → "API e servizi" → "Libreria"
   - Cerca "YouTube Data API v3"
   - Clicca "Abilita"

4. Crea credenziali OAuth 2.0:
   - Menu ≡ → "API e servizi" → "Credenziali"
   - Clicca "+ CREA CREDENZIALI" → "ID client OAuth"
   - Tipo applicazione: "Applicazione web"
   - Nome: "AIVideoMaker"
   - URI di reindirizzamento autorizzati:
     * http://localhost:8000/api/youtube/oauth2callback
   - Clicca "Crea"

5. Scarica il JSON:
   - Clicca sull'icona download (⬇️) accanto al client OAuth appena creato
   - Rinomina il file in "client_secrets.json"
   - Posizionalo nella root del progetto AIVideoMaker1/

6. Configura schermata consenso OAuth:
   - Menu ≡ → "API e servizi" → "Schermata consenso OAuth"
   - Tipo utente: "Esterno" (per test)
   - Compila i campi obbligatori:
     * Nome app: "AIVideoMaker"
     * Email assistenza utenti: tua email
     * Email contatto sviluppatore: tua email
   - Ambiti: aggiungi YouTube Data API v3 scope
   - Salva

7. Aggiungi utenti test (se in modalità test):
   - Nella schermata consenso OAuth
   - Sezione "Utenti test"
   - Aggiungi il tuo account Google/Gmail

NOTA: In modalità "Test", solo gli utenti aggiunti esplicitamente potranno
autorizzare l'app. Per uso pubblico, richiedi la verifica di Google.
"""
