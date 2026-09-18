"""Casos de uso de autenticación (RF-01, RF-02, RNF-04). Sin dependencias de frameworks."""

from dataclasses import dataclass

from app.domain.entities.user import User
from app.domain.errors import InvalidCredentials, InvalidToken
from app.domain.ports import PasswordHasher, TokenService, UserRepository


@dataclass(frozen=True)
class TokenPair:
    access_token: str
    refresh_token: str
    expires_in: int
    token_type: str = "bearer"  # noqa: S105 - esquema HTTP, no un secreto


@dataclass(frozen=True)
class AccessToken:
    access_token: str
    expires_in: int
    token_type: str = "bearer"  # noqa: S105 - esquema HTTP, no un secreto


def normalize_email(email: str) -> str:
    return email.strip().lower()


def register_user(
    repo: UserRepository,
    hasher: PasswordHasher,
    *,
    email: str,
    password: str,
    full_name: str | None,
) -> User:
    return repo.add(
        email=normalize_email(email),
        password_hash=hasher.hash(password),
        full_name=full_name,
    )


def login_user(
    repo: UserRepository,
    hasher: PasswordHasher,
    tokens: TokenService,
    *,
    email: str,
    password: str,
) -> TokenPair:
    user = repo.get_by_email(normalize_email(email))
    # verify() se ejecuta siempre, exista o no el usuario, para no filtrar por tiempo de respuesta.
    password_ok = hasher.verify(password, user.password_hash if user else None)
    if user is None or not password_ok or not user.is_active:
        raise InvalidCredentials
    return TokenPair(
        access_token=tokens.create_access_token(user_id=user.id, role=user.role),
        refresh_token=tokens.create_refresh_token(user_id=user.id, role=user.role),
        expires_in=tokens.access_ttl_seconds,
    )


def refresh_access_token(
    repo: UserRepository, tokens: TokenService, *, refresh_token: str
) -> AccessToken:
    claims = tokens.decode_refresh(refresh_token)
    user = repo.get_by_id(claims.user_id)
    if user is None or not user.is_active:
        raise InvalidToken
    return AccessToken(
        access_token=tokens.create_access_token(user_id=user.id, role=user.role),
        expires_in=tokens.access_ttl_seconds,
    )


def get_active_user(repo: UserRepository, tokens: TokenService, *, access_token: str) -> User:
    claims = tokens.decode_access(access_token)
    user = repo.get_by_id(claims.user_id)
    if user is None or not user.is_active:
        raise InvalidToken
    return user
