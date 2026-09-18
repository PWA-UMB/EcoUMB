"""Puertos: contratos que el dominio necesita y que la infraestructura implementa."""

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Protocol

from app.domain.entities.user import User
from app.domain.roles import Role

TokenType = Literal["access", "refresh"]


@dataclass(frozen=True)
class TokenClaims:
    user_id: uuid.UUID
    role: Role
    token_type: TokenType
    issued_at: datetime
    expires_at: datetime


class UserRepository(Protocol):
    def get_by_email(self, email: str) -> User | None: ...

    def get_by_id(self, user_id: uuid.UUID) -> User | None: ...

    def add(self, *, email: str, password_hash: str, full_name: str | None) -> User:
        """Persiste un usuario nuevo. Lanza ``EmailAlreadyRegistered`` si el correo existe."""
        ...

    def list_all(self) -> list[User]: ...


class PasswordHasher(Protocol):
    def hash(self, password: str) -> str: ...

    def verify(self, password: str, password_hash: str | None) -> bool:
        """Con ``password_hash=None`` debe gastar el mismo trabajo y devolver ``False``."""
        ...


class TokenService(Protocol):
    @property
    def access_ttl_seconds(self) -> int: ...

    def create_access_token(self, *, user_id: uuid.UUID, role: Role) -> str: ...

    def create_refresh_token(self, *, user_id: uuid.UUID, role: Role) -> str: ...

    def decode_access(self, token: str) -> TokenClaims: ...

    def decode_refresh(self, token: str) -> TokenClaims: ...
