"""
SlowAPI Limiter Configuration
==============================
Rate limiting granulare per route specifiche.

Usage:
    from app.core.limiter import limiter

    @router.post("/endpoint")
    @limiter.limit("5/minute")
    async def my_endpoint(request: Request):
        ...
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

# Crea istanza limiter globale
limiter = Limiter(key_func=get_remote_address)
