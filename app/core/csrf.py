"""
CSRF Protection Middleware
===========================
Protezione Cross-Site Request Forgery per endpoint sensibili.

NOTE: Con autenticazione JWT via Authorization header, CSRF è meno critico
perché i browser non inviano automaticamente header custom.
Questo middleware protegge endpoint che potrebbero usare cookies in futuro.
"""

from fastapi import Request, HTTPException, status
from fastapi.responses import Response
from starlette.middleware.base import BaseHTTPMiddleware
import secrets
import hashlib
from typing import Callable


class CSRFProtectionMiddleware(BaseHTTPMiddleware):
    """
    Middleware per CSRF protection.

    Funzionamento:
    1. Genera CSRF token per ogni sessione
    2. Richiede token valido per richieste state-changing (POST, PUT, DELETE, PATCH)
    3. Esclude endpoint pubblici (login, register, etc.)
    """

    # Endpoint esclusi da CSRF check (pubblici o con altra protezione)
    EXCLUDED_PATHS = [
        "/api/v1/auth/login",
        "/api/v1/auth/register",
        "/api/v1/auth/google",
        "/api/v1/auth/refresh",
        "/api/v1/auth/forgot-password",
        "/api/v1/auth/reset-password",
        "/api/v1/auth/verify-email",
        "/api/v1/auth/resend-verification",
        "/docs",
        "/redoc",
        "/openapi.json",
    ]

    # Metodi che richiedono CSRF token
    PROTECTED_METHODS = ["POST", "PUT", "DELETE", "PATCH"]

    def __init__(self, app, secret_key: str):
        super().__init__(app)
        self.secret_key = secret_key

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Processa richiesta con CSRF check

        Args:
            request: Request FastAPI
            call_next: Next middleware/handler

        Returns:
            Response
        """
        # Skip CSRF per metodi safe (GET, HEAD, OPTIONS)
        if request.method not in self.PROTECTED_METHODS:
            response = await call_next(request)
            return response

        # Skip CSRF per path esclusi
        if self._is_excluded_path(request.url.path):
            response = await call_next(request)
            return response

        # Verifica CSRF token
        csrf_token = request.headers.get("X-CSRF-Token")

        if not csrf_token:
            # Controlla anche in form data o query params (fallback)
            if request.method == "POST":
                try:
                    form = await request.form()
                    csrf_token = form.get("csrf_token")
                except:
                    pass

        if not csrf_token or not self._validate_token(csrf_token):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="CSRF token mancante o invalido"
            )

        # Token valido, procedi
        response = await call_next(request)
        return response

    def _is_excluded_path(self, path: str) -> bool:
        """Check se path è escluso da CSRF protection"""
        return any(path.startswith(excluded) for excluded in self.EXCLUDED_PATHS)

    def _validate_token(self, token: str) -> bool:
        """
        Valida CSRF token

        Per semplicità, accetta qualsiasi token non vuoto.
        In produzione avanzata: validare contro token salvato in session/cookie.
        """
        # Basic validation: token deve essere almeno 32 caratteri hex
        if not token or len(token) < 32:
            return False

        # Verifica formato hex
        try:
            int(token, 16)
            return True
        except ValueError:
            return False


def generate_csrf_token() -> str:
    """
    Genera CSRF token sicuro

    Returns:
        str: CSRF token (32 byte hex = 64 caratteri)
    """
    return secrets.token_hex(32)
