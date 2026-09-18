from typing import Annotated

from fastapi import APIRouter, Depends

from app.domain.entities.user import User
from app.domain.roles import Role
from app.interfaces.api.deps import CurrentUser, UserRepositoryDep, require_roles
from app.interfaces.schemas.auth import UserResponse

router = APIRouter(prefix="/users", tags=["users"])

AdminUser = Annotated[User, Depends(require_roles(Role.ADMIN))]


@router.get("/me", response_model=UserResponse)
def read_me(user: CurrentUser) -> UserResponse:
    """Perfil del usuario autenticado (RF-04, lectura)."""
    return UserResponse.model_validate(user)


@router.get("", response_model=list[UserResponse])
def list_users(_: AdminUser, repo: UserRepositoryDep) -> list[UserResponse]:
    """Solo administradores (RF-07, lectura). Demuestra el RBAC de S1-09."""
    return [UserResponse.model_validate(u) for u in repo.list_all()]
