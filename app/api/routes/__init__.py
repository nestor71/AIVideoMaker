"""
API Routes
==========
Tutti i router API dell'applicazione
"""

from app.api.routes import auth, chromakey, translation, thumbnail, youtube, pipeline

__all__ = ["auth", "chromakey", "translation", "thumbnail", "youtube", "pipeline"]
