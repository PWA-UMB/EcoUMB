"""Dependencias de FastAPI: sesión, adaptadores, límite de tasa, usuario actual y RBAC."""

import math
from collections.abc import Callable, Iterator
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.application.auth.use_cases import get_active_user
from app.domain.entities.user import User
from app.domain.errors import InvalidToken
from app.domain.ports import PasswordHasher, TokenService, UserRepository
from app.domain.roles import Role
from app.infrastructure.persistence.user_repository import SqlAlchemyUserRepository

_bearer = HTTPBearer(auto_error=False)


def get_session(request: Request) -> Iterator[Session]:
    with request.app.state.session_factory() as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]


def get_user_repository(session: SessionDep) -> UserRepository:
    return SqlAlchemyUserRepository(session)


def get_password_hasher(request: Request) -> PasswordHasher:
    hasher: PasswordHasher = request.app.state.password_hasher
    return hasher


def get_token_service(request: Request) -> TokenService:
    service: TokenService = request.app.state.token_service
    return service


UserRepositoryDep = Annotated[UserRepository, Depends(get_user_repository)]
PasswordHasherDep = Annotated[PasswordHasher, Depends(get_password_hasher)]
TokenServiceDep = Annotated[TokenService, Depends(get_token_service)]


def auth_rate_limit(request: Request) -> None:
    """Máximo N solicitudes por minuto e IP en los endpoints de autenticación (RNF-04)."""
    client_ip = request.client.host if request.client else "unknown"
    wait = request.app.state.rate_limiter.retry_after(client_ip)
    if wait is not None:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Demasiadas solicitudes. Intenta de nuevo en un momento.",
            headers={"Retry-After": str(max(1, math.ceil(wait)))},
        )


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    repo: UserRepositoryDep,
    tokens: TokenServiceDep,
) -> User:
    if credentials is None:
        raise InvalidToken
    return get_active_user(repo, tokens, access_token=credentials.credentials)


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_roles(*allowed: Role) -> Callable[[User], User]:
    """RBAC (RF-06, RF-08, RNF-06). El rol se lee de la base de datos, no del token, para que
    un cambio de rol o una baja surta efecto de inmediato."""

    def checker(user: CurrentUser) -> User:
        if user.role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="No tienes permisos para esta acción"
            )
        return user

    return checker
