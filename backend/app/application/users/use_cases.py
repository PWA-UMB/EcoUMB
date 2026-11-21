"""Casos de uso del perfil de usuario (RF-04)."""

import uuid

from app.domain.entities.user import User
from app.domain.ports import UserRepository


def update_profile(repo: UserRepository, user_id: uuid.UUID, *, full_name: str | None) -> User:
    """Cambia el nombre visible. Correo, rol y puntos no se editan desde aquí."""
    return repo.update_full_name(user_id, full_name)
