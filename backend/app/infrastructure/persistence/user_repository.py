import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.domain.entities.user import User
from app.domain.errors import EmailAlreadyRegistered
from app.infrastructure.persistence.models import UserModel


def _to_entity(model: UserModel) -> User:
    return User(
        id=model.id,
        email=model.email,
        password_hash=model.password_hash,
        full_name=model.full_name,
        role=model.role,
        is_active=model.is_active,
        total_points=model.total_points,
        level=model.level,
    )


class SqlAlchemyUserRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_email(self, email: str) -> User | None:
        model = self._session.scalars(select(UserModel).where(UserModel.email == email)).first()
        return _to_entity(model) if model else None

    def get_by_id(self, user_id: uuid.UUID) -> User | None:
        model = self._session.get(UserModel, user_id)
        return _to_entity(model) if model else None

    def add(self, *, email: str, password_hash: str, full_name: str | None) -> User:
        model = UserModel(email=email, password_hash=password_hash, full_name=full_name)
        self._session.add(model)
        try:
            self._session.commit()
        except IntegrityError:
            # La restricción UNIQUE es la fuente de verdad: evita la condición de carrera
            # entre "consultar si existe" e "insertar".
            self._session.rollback()
            raise EmailAlreadyRegistered(email) from None
        return _to_entity(model)

    def list_all(self) -> list[User]:
        rows = self._session.scalars(select(UserModel).order_by(UserModel.email)).all()
        return [_to_entity(row) for row in rows]
