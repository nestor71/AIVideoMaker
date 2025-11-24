"""
Rate Limiting Middleware
=========================
Protezione API da abuso con rate limiting semplice in-memory.

In production può essere sostituito con:
- Redis backend per distributed rate limiting
- SlowAPI library per features avanzate
"""

import time
import logging
from typing import Dict, Tuple
from collections import defaultdict
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware rate limiting per protezione API.

    Implementazione in-memory con sliding window.

    Features:
    - Rate limiting per IP address
    - Configurabile da settings
    - Esclude endpoint pubblici (health check, docs)
    - Headers informativi (X-RateLimit-*)
    """

    def __init__(self, app, enabled: bool = True):
        super().__init__(app)
        self.enabled = enabled

        if not self.enabled:
            logger.info("⚠️  Rate limiting DISABILITATO")
            return

        # In-memory storage: {ip: [(timestamp, count)]}
        self.requests: Dict[str, list] = defaultdict(list)

        # Config da settings
        self.max_requests = settings.rate_limit_requests  # Default: 100
        self.window_seconds = settings.rate_limit_window  # Default: 60

        # Endpoint esclusi da rate limiting
        self.excluded_paths = {
            "/",
            "/health",
            "/docs",
            "/redoc",
            "/openapi.json"
        }

        # Prefissi endpoint esclusi (per pattern matching)
        self.excluded_prefixes = [
            "/api/v1/screen-record/screenshot/",  # Preview live screenshot (richieste frequenti)
            "/api/v1/screen-record/active-jobs",  # Polling active jobs
        ]

        logger.info(f"✅ Rate limiting ABILITATO: {self.max_requests} req/{self.window_seconds}s")

    async def dispatch(self, request: Request, call_next):
        """Middleware dispatcher"""

        # Se disabilitato, passa through
        if not self.enabled:
            return await call_next(request)

        # Skippa endpoint esclusi
        if request.url.path in self.excluded_paths:
            return await call_next(request)

        # Skippa endpoint con prefissi esclusi
        for prefix in self.excluded_prefixes:
            if request.url.path.startswith(prefix):
                return await call_next(request)

        # Skippa static files
        if request.url.path.startswith("/static") or request.url.path.startswith("/uploads") or request.url.path.startswith("/outputs"):
            return await call_next(request)

        # Ottieni client IP
        client_ip = self._get_client_ip(request)

        # Check rate limit
        is_allowed, remaining, reset_time = self._check_rate_limit(client_ip)

        if not is_allowed:
            # Rate limit exceeded
            logger.warning(f"🚫 Rate limit exceeded for IP: {client_ip}")

            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "Rate limit exceeded",
                    "message": f"Troppo richieste. Max {self.max_requests} richieste per {self.window_seconds} secondi.",
                    "retry_after": int(reset_time - time.time())
                },
                headers={
                    "X-RateLimit-Limit": str(self.max_requests),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(reset_time)),
                    "Retry-After": str(int(reset_time - time.time()))
                }
            )

        # Processa richiesta
        response = await call_next(request)

        # Aggiungi rate limit headers
        response.headers["X-RateLimit-Limit"] = str(self.max_requests)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(int(reset_time))

        return response

    def _get_client_ip(self, request: Request) -> str:
        """Estrai IP client (gestisce proxy)"""
        # Check proxy headers
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            # Primo IP nella catena
            return forwarded.split(",")[0].strip()

        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip

        # Fallback a client IP diretto
        if request.client:
            return request.client.host

        return "unknown"

    def _check_rate_limit(self, client_ip: str) -> Tuple[bool, int, float]:
        """
        Verifica rate limit per IP

        Returns:
            (is_allowed, remaining_requests, reset_timestamp)
        """
        current_time = time.time()
        window_start = current_time - self.window_seconds

        # Cleanup vecchie richieste (fuori dalla finestra)
        self.requests[client_ip] = [
            timestamp for timestamp in self.requests[client_ip]
            if timestamp > window_start
        ]

        # Conta richieste nella finestra corrente
        request_count = len(self.requests[client_ip])

        # Check se limite superato
        if request_count >= self.max_requests:
            # Reset time = timestamp prima richiesta + window
            oldest_request = min(self.requests[client_ip]) if self.requests[client_ip] else current_time
            reset_time = oldest_request + self.window_seconds

            return False, 0, reset_time

        # Aggiungi richiesta corrente
        self.requests[client_ip].append(current_time)

        # Calcola remaining
        remaining = self.max_requests - (request_count + 1)
        reset_time = current_time + self.window_seconds

        return True, remaining, reset_time

    def clear_ip(self, ip: str):
        """Pulisci rate limit per IP specifico (admin use)"""
        if ip in self.requests:
            del self.requests[ip]
            logger.info(f"Rate limit cleared for IP: {ip}")

    def clear_all(self):
        """Pulisci tutti rate limits (admin use)"""
        self.requests.clear()
        logger.info("All rate limits cleared")
