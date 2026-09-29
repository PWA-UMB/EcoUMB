"""Puertos: contratos que el dominio necesita y que la infraestructura implementa."""

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Protocol

from app.domain.confidence import ConfidenceBand
from app.domain.entities.classification import Classification, Prediction, WasteItem
from app.domain.entities.education import WasteCategory
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

    def update_full_name(self, user_id: uuid.UUID, full_name: str | None) -> User:
        """Cambia el nombre visible (RF-04). Lanza ``InvalidToken`` si el usuario ya no existe."""
        ...


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


class WasteCatalog(Protocol):
    def list_active(self) -> list[WasteItem]: ...


class CategoryCatalog(Protocol):
    def list_categories(self) -> list[WasteCategory]: ...


class ImageClassifier(Protocol):
    """Contrato del clasificador: hoy lo cumple el simulado y luego el modelo real (RNF-17)."""

    def predict(self, image: bytes, items: Sequence[WasteItem]) -> Prediction: ...


class ImageStorage(Protocol):
    def save(self, key: str, data: bytes) -> None: ...

    def read(self, key: str) -> bytes:
        """Lanza ``FileNotFoundError`` si la clave no existe."""
        ...

    def delete(self, key: str) -> None:
        """No falla si la clave ya no existe."""
        ...


class ClassificationRepository(Protocol):
    def add(
        self, *, user_id: uuid.UUID, prediction: Prediction, band: ConfidenceBand, image_key: str
    ) -> Classification: ...

    def list_for_user(
        self, user_id: uuid.UUID, *, limit: int, offset: int
    ) -> tuple[list[Classification], int]:
        """Registros del usuario, del más nuevo al más antiguo, y el total."""
        ...

    def get_for_user(
        self, user_id: uuid.UUID, classification_id: uuid.UUID
    ) -> Classification | None: ...

    def set_feedback(
        self, user_id: uuid.UUID, classification_id: uuid.UUID, item_id: uuid.UUID
    ) -> Classification | None:
        """Guarda lo que el usuario dice que era el residuo. None si no existe o no es suyo."""
        ...
