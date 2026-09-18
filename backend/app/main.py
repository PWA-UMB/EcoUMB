"""Punto de entrada: ``uvicorn app.main:create_app --factory``."""

import logging
import time
from collections.abc import Awaitable, Callable
from datetime import timedelta

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import Settings, get_settings
from app.core.keys import generate_rsa_keypair
from app.core.logging import configure_logging
from app.core.rate_limit import SlidingWindowRateLimiter
from app.domain.errors import EmailAlreadyRegistered, InvalidCredentials, InvalidToken
from app.infrastructure.persistence.session import create_db_engine, create_session_factory
from app.infrastructure.security.passwords import BcryptPasswordHasher
from app.infrastructure.security.tokens import JwtTokenService
from app.interfaces.api import health
from app.interfaces.api.v1 import auth, users

logger = logging.getLogger("ecoumb")

API_PREFIX = "/api/v1"
SECURITY_HEADERS = {"X-Content-Type-Options": "nosniff", "Referrer-Policy": "no-referrer"}


def _resolve_jwt_keys(settings: Settings) -> tuple[str, str]:
    private, public = settings.jwt_private_key, settings.jwt_public_key
    if private and public:
        # Los .env suelen guardar los saltos de línea del PEM como "\n" literales.
        return private.replace("\\n", "\n"), public.replace("\\n", "\n")
    if private or public:
        raise ValueError("Configura JWT_PRIVATE_KEY y JWT_PUBLIC_KEY juntas, o ninguna")
    logger.warning(
        "JWT sin claves configuradas: se usa un par efímero; los tokens se invalidan al reiniciar"
    )
    return generate_rsa_keypair()


def _install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(EmailAlreadyRegistered)
    async def _conflict(_: Request, __: EmailAlreadyRegistered) -> JSONResponse:
        return JSONResponse({"detail": "El correo ya está registrado"}, status_code=409)

    @app.exception_handler(InvalidCredentials)
    async def _bad_credentials(_: Request, __: InvalidCredentials) -> JSONResponse:
        return JSONResponse(
            {"detail": "Credenciales inválidas"},
            status_code=401,
            headers={"WWW-Authenticate": "Bearer"},
        )

    @app.exception_handler(InvalidToken)
    async def _bad_token(_: Request, __: InvalidToken) -> JSONResponse:
        return JSONResponse(
            {"detail": "Token inválido o expirado"},
            status_code=401,
            headers={"WWW-Authenticate": "Bearer"},
        )


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level)

    private_key, public_key = _resolve_jwt_keys(settings)
    engine = create_db_engine(settings.database_url)

    app = FastAPI(
        title="EcoUMB API",
        version=settings.app_version,
        description="Clasificación y trazabilidad de residuos sólidos — UMB sede Bogotá.",
    )
    app.state.settings = settings
    app.state.engine = engine
    app.state.session_factory = create_session_factory(engine)
    app.state.password_hasher = BcryptPasswordHasher(rounds=settings.bcrypt_rounds)
    app.state.token_service = JwtTokenService(
        private_key=private_key,
        public_key=public_key,
        access_ttl=timedelta(minutes=settings.access_token_minutes),
        refresh_ttl=timedelta(days=settings.refresh_token_days),
        issuer=settings.jwt_issuer,
        audience=settings.jwt_audience,
    )
    app.state.rate_limiter = SlidingWindowRateLimiter(limit=settings.auth_rate_limit_per_minute)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
        allow_credentials=False,
    )

    @app.middleware("http")
    async def _log_and_harden(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        started = time.perf_counter()
        response = await call_next(request)
        response.headers.update(SECURITY_HEADERS)
        logger.info(
            "request",
            extra={
                "method": request.method,
                "path": request.url.path,  # sin query string ni cabeceras: no filtra credenciales
                "status": response.status_code,
                "duration_ms": round((time.perf_counter() - started) * 1000, 1),
            },
        )
        return response

    _install_error_handlers(app)
    app.include_router(health.router)
    app.include_router(auth.router, prefix=API_PREFIX)
    app.include_router(users.router, prefix=API_PREFIX)
    return app
