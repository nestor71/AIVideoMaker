"""
ElevenLabs Integration Module - AIVideoMaker
============================================
Integrazione con ElevenLabs API per:
- Dubbing video con lip-sync professionale
- Text-to-Speech di alta qualità
- Clonazione voce (voice cloning)

Documentazione: https://elevenlabs.io/docs/
"""

import os
import requests
import logging
from pathlib import Path
from typing import Optional, Dict, Any
import time

logger = logging.getLogger(__name__)


class ElevenLabsClient:
    """
    Client per ElevenLabs API
    """

    BASE_URL = "https://api.elevenlabs.io/v1"

    def __init__(self, api_key: Optional[str] = None):
        """
        Inizializza client ElevenLabs

        Args:
            api_key: API key ElevenLabs (se None, cerca in .env)
        """
        self.api_key = api_key or os.getenv('ELEVENLABS_API_KEY')

        if not self.api_key:
            raise ValueError(
                "ElevenLabs API key non trovata. "
                "Aggiungi ELEVENLABS_API_KEY nel file .env o passa come parametro"
            )

        self.headers = {
            "xi-api-key": self.api_key,
            "Content-Type": "application/json"
        }

    def dub_video(
        self,
        video_path: str,
        target_language: str,
        output_path: str,
        source_language: str = "auto"
    ) -> bool:
        """
        Doppia un video in un'altra lingua con lip-sync automatico

        Args:
            video_path: Path del video da doppiare
            target_language: Codice lingua target (es. 'it', 'en', 'es')
            output_path: Path del video output
            source_language: Codice lingua sorgente ('auto' per rilevamento automatico)

        Returns:
            True se successo, False altrimenti
        """
        try:
            logger.info(f"Avvio dubbing ElevenLabs: {video_path} -> {target_language}")

            # STEP 1: Upload video
            dubbing_id = self._upload_video_for_dubbing(
                video_path,
                target_language,
                source_language
            )

            logger.info(f"Video caricato, dubbing ID: {dubbing_id}")

            # STEP 2: Poll status fino a completamento
            dubbed_video_url = self._wait_for_dubbing_completion(dubbing_id)

            if not dubbed_video_url:
                raise Exception("Dubbing fallito o timeout")

            logger.info(f"Dubbing completato: {dubbed_video_url}")

            # STEP 3: Download video doppiato
            self._download_video(dubbed_video_url, output_path)

            logger.info(f"Video doppiato salvato: {output_path}")
            return True

        except Exception as e:
            logger.error(f"Errore dubbing ElevenLabs: {e}")
            return False

    def _upload_video_for_dubbing(
        self,
        video_path: str,
        target_language: str,
        source_language: str = "auto"
    ) -> str:
        """
        Upload video per dubbing

        Returns:
            Dubbing ID
        """
        url = f"{self.BASE_URL}/dubbing"

        # Mappa codici lingua ai codici ElevenLabs
        language_map = {
            'it': 'italian',
            'en': 'english',
            'es': 'spanish',
            'fr': 'french',
            'de': 'german',
            'pt': 'portuguese',
            'ru': 'russian',
            'ja': 'japanese',
            'zh-CN': 'chinese',
            'ar': 'arabic',
            'hi': 'hindi',
            'ko': 'korean',
            'nl': 'dutch',
            'tr': 'turkish',
            'pl': 'polish'
        }

        target_lang_name = language_map.get(target_language, target_language)

        # Prepara file upload
        with open(video_path, 'rb') as video_file:
            files = {
                'file': (Path(video_path).name, video_file, 'video/mp4')
            }

            data = {
                'target_lang': target_lang_name,
                'mode': 'automatic',  # automatic dubbing con lip-sync
                'num_speakers': 1  # numero di speaker da doppiare
            }

            if source_language != 'auto':
                source_lang_name = language_map.get(source_language, source_language)
                data['source_lang'] = source_lang_name

            response = requests.post(
                url,
                headers={"xi-api-key": self.api_key},
                files=files,
                data=data,
                timeout=300  # 5 minuti timeout per upload
            )

            response.raise_for_status()
            result = response.json()

            return result['dubbing_id']

    def _wait_for_dubbing_completion(
        self,
        dubbing_id: str,
        max_wait_time: int = 1800  # 30 minuti max
    ) -> Optional[str]:
        """
        Aspetta che il dubbing sia completato

        Args:
            dubbing_id: ID del job di dubbing
            max_wait_time: Tempo massimo di attesa in secondi

        Returns:
            URL del video doppiato o None se timeout/errore
        """
        url = f"{self.BASE_URL}/dubbing/{dubbing_id}"

        start_time = time.time()

        while True:
            # Check timeout
            if time.time() - start_time > max_wait_time:
                logger.error("Timeout dubbing ElevenLabs")
                return None

            try:
                response = requests.get(url, headers=self.headers)
                response.raise_for_status()
                result = response.json()

                status = result.get('status')
                logger.info(f"Dubbing status: {status}")

                if status == 'dubbed':
                    # Completato!
                    return result.get('target_video_url') or result.get('output_video_url')

                elif status == 'failed':
                    logger.error(f"Dubbing fallito: {result.get('error')}")
                    return None

                elif status in ['dubbing', 'processing', 'pending']:
                    # In corso, attendi
                    time.sleep(10)  # Polling ogni 10 secondi

                else:
                    logger.warning(f"Status sconosciuto: {status}")
                    time.sleep(10)

            except Exception as e:
                logger.error(f"Errore polling status: {e}")
                time.sleep(10)

    def _download_video(self, video_url: str, output_path: str):
        """
        Scarica il video doppiato

        Args:
            video_url: URL del video da scaricare
            output_path: Path dove salvare il video
        """
        response = requests.get(video_url, stream=True, timeout=600)
        response.raise_for_status()

        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)

        logger.info(f"Video scaricato: {output_path}")

    def get_available_voices(self) -> Dict[str, Any]:
        """
        Ottiene la lista delle voci disponibili

        Returns:
            Dict con voci disponibili
        """
        url = f"{self.BASE_URL}/voices"

        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Errore get voices: {e}")
            return {}

    def check_api_key(self) -> bool:
        """
        Verifica se la API key è valida

        Returns:
            True se valida, False altrimenti
        """
        try:
            url = f"{self.BASE_URL}/user"
            response = requests.get(url, headers=self.headers)
            return response.status_code == 200
        except:
            return False


def test_elevenlabs_integration():
    """
    Test rapido dell'integrazione ElevenLabs
    """
    try:
        client = ElevenLabsClient()

        if client.check_api_key():
            print("✅ API key ElevenLabs valida!")
            print("\nVoci disponibili:")
            voices = client.get_available_voices()
            for voice in voices.get('voices', [])[:5]:  # Mostra solo prime 5
                print(f"  - {voice.get('name')} ({voice.get('language')})")
        else:
            print("❌ API key ElevenLabs non valida")

    except Exception as e:
        print(f"❌ Errore test: {e}")


if __name__ == "__main__":
    test_elevenlabs_integration()
