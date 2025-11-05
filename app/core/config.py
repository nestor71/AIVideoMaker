"""
Configuration Management - Centralizzato
========================================
Gestione configurazione con Pydantic Settings e validazione.
Tutte le configurazioni da environment variables.
"""

from typing import Optional, List
from pydantic_settings import BaseSettings
from pydantic import Field, validator
import os
from pathlib import Path


class Settings(BaseSettings):
    """Configurazione centralizzata applicazione"""

    # ==================== APP SETTINGS ====================
    app_name: str = "AIVideoMaker Professional"
    app_version: str = "2.0.0"
    debug: bool = Field(default=False, description="Debug mode")
    environment: str = Field(default="development", description="Environment: development, staging, production")

    # ==================== API SETTINGS ====================
    api_host: str = Field(default="0.0.0.0", description="API host")
    api_port: int = Field(default=8000, description="API port")
    api_prefix: str = Field(default="/api/v1", description="API prefix")

    # ==================== SECURITY ====================
    secret_key: str = Field(..., description="Secret key per JWT (MUST BE RANDOM)")
    access_token_expire_minutes: int = Field(default=60 * 24, description="Token expiry (minuti)")
    algorithm: str = Field(default="HS256", description="JWT algorithm")

    # API Keys per servizi
    openai_api_key: Optional[str] = Field(default=None, description="OpenAI API key")
    elevenlabs_api_key: Optional[str] = Field(default=None, description="ElevenLabs API key")

    # Rate limiting
    rate_limit_enabled: bool = Field(default=True, description="Abilita rate limiting")
    rate_limit_requests: int = Field(default=100, description="Richieste max per finestra")
    rate_limit_window: int = Field(default=60, description="Finestra temporale (secondi)")

    # ==================== DATABASE ====================
    database_url: str = Field(
        default="postgresql://aivideomaker:password@localhost:5432/aivideomaker",
        description="PostgreSQL connection string"
    )
    database_echo: bool = Field(default=False, description="Log SQL queries")

    # ==================== REDIS ====================
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection string"
    )
    redis_cache_ttl: int = Field(default=3600, description="Cache TTL default (secondi)")

    # ==================== CELERY ====================
    celery_broker_url: str = Field(
        default="redis://localhost:6379/1",
        description="Celery broker URL"
    )
    celery_result_backend: str = Field(
        default="redis://localhost:6379/2",
        description="Celery result backend"
    )
    celery_task_time_limit: int = Field(default=3600, description="Task timeout (secondi)")

    # ==================== FILE STORAGE ====================
    upload_dir: Path = Field(default=Path("uploads"), description="Directory upload")
    output_dir: Path = Field(default=Path("outputs"), description="Directory output")
    temp_dir: Path = Field(default=Path("temp"), description="Directory temporanea")

    max_upload_size: int = Field(default=500 * 1024 * 1024, description="Max file size (bytes)")
    file_retention_days: int = Field(default=7, description="Giorni ritenzione file")

    # ==================== VIDEO PROCESSING ====================
    max_concurrent_jobs: int = Field(default=3, description="Max job concorrenti")
    ffmpeg_path: str = Field(default="ffmpeg", description="Path FFmpeg binary")
    ffprobe_path: str = Field(default="ffprobe", description="Path FFprobe binary")

    # Formati supportati
    allowed_video_formats: List[str] = Field(
        default=[".mp4", ".avi", ".mov", ".mkv", ".webm"],
        description="Formati video supportati"
    )
    allowed_image_formats: List[str] = Field(
        default=[".jpg", ".jpeg", ".png", ".gif", ".webp"],
        description="Formati immagine supportati"
    )

    # ==================== CHROMAKEY SETTINGS ====================
    chromakey_default_lower_hsv: List[int] = Field(default=[40, 40, 40], description="HSV lower bound")
    chromakey_default_upper_hsv: List[int] = Field(default=[80, 255, 255], description="HSV upper bound")
    chromakey_blur_kernel: int = Field(default=5, description="Blur kernel size")

    # ==================== TRANSLATION SETTINGS ====================
    translation_supported_languages: List[str] = Field(
        default=['en', 'es', 'fr', 'de', 'pt', 'ru', 'ja', 'zh-CN', 'ar', 'hi', 'it'],
        description="Lingue supportate traduzione"
    )
    translation_default_target: str = Field(default="en", description="Lingua target default")

    # ==================== THUMBNAIL SETTINGS ====================
    thumbnail_width: int = Field(default=1280, description="Larghezza miniatura YouTube")
    thumbnail_height: int = Field(default=720, description="Altezza miniatura YouTube")
    thumbnail_quality: int = Field(default=90, description="Qualità JPEG")
    thumbnail_max_size_mb: float = Field(default=2.0, description="Max size MB YouTube")

    # ==================== YOUTUBE SETTINGS ====================
    youtube_client_secrets_file: Path = Field(
        default=Path("client_secrets.json"),
        description="Path file secrets YouTube API"
    )
    youtube_default_privacy: str = Field(default="private", description="Privacy default upload")

    # ==================== CORS ====================
    cors_origins: List[str] = Field(
        default=["http://localhost:8000", "http://localhost:3000"],
        description="CORS allowed origins"
    )

    # ==================== LOGGING ====================
    log_level: str = Field(default="INFO", description="Logging level")
    log_file: Path = Field(default=Path("logs/app.log"), description="Log file path")

    @validator('secret_key')
    def validate_secret_key(cls, v):
        if v and len(v) < 32:
            raise ValueError("secret_key deve essere almeno 32 caratteri")
        return v

    @validator('environment')
    def validate_environment(cls, v):
        allowed = ['development', 'staging', 'production']
        if v not in allowed:
            raise ValueError(f"environment deve essere uno di: {allowed}")
        return v

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Crea directory se non esistono
        self.upload_dir.mkdir(exist_ok=True)
        self.output_dir.mkdir(exist_ok=True)
        self.temp_dir.mkdir(exist_ok=True)
        self.log_file.parent.mkdir(exist_ok=True)

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Singleton instance
settings = Settings()
