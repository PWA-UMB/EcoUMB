"""Casos de uso probados sin FastAPI ni base de datos: solo con dobles en memoria."""

import uuid
from datetime import timedelta

import pytest

from app.application.auth.use_cases import login_user, refresh_access_token, register_user
from app.core.keys import generate_rsa_keypair
from app.domain.entities.user import User
from app.domain.errors import EmailAlreadyRegistered, InvalidCredentials, InvalidToken
from app.domain.roles import Role
from app.infrastructure.security.passwords import BcryptPasswordHasher
from app.infrastructure.security.tokens import JwtTokenService


class InMemoryUserRepository:
    def __init__(self) -> None:
        self.users: dict[uuid.UUID, User] = {}

    def get_by_email(self, email: str) -> User | None:
        return next((u for u in self.users.values() if u.email == email), None)

    def get_by_id(self, user_id: uuid.UUID) -> User | None:
        return self.users.get(user_id)

    def add(self, *, email: str, password_hash: str, full_name: str | None) -> User:
        if self.get_by_email(email):
            raise EmailAlreadyRegistered(email)
        user = User(
            id=uuid.uuid4(),
            email=email,
            password_hash=password_hash,
            full_name=full_name,
            role=Role.USER,
            is_active=True,
            total_points=0,
            level=1,
        )
        self.users[user.id] = user
        return user

    def list_all(self) -> list[User]:
        return list(self.users.values())


class SpyHasher(BcryptPasswordHasher):
    def __init__(self) -> None:
        super().__init__(rounds=4)
        self.verify_calls: list[str | None] = []

    def verify(self, password: str, password_hash: str | None) -> bool:
        self.verify_calls.append(password_hash)
        return super().verify(password, password_hash)


@pytest.fixture
def repo() -> InMemoryUserRepository:
    return InMemoryUserRepository()


@pytest.fixture
def hasher() -> SpyHasher:
    return SpyHasher()


@pytest.fixture
def tokens() -> JwtTokenService:
    private, public = generate_rsa_keypair()
    return JwtTokenService(
        private_key=private,
        public_key=public,
        access_ttl=timedelta(minutes=15),
        refresh_ttl=timedelta(days=7),
    )


def test_register_normalizes_email_and_hashes_password(
    repo: InMemoryUserRepository, hasher: SpyHasher
) -> None:
    user = register_user(
        repo, hasher, email="  Ana@UMB.edu.co ", password="Clave-Segura-2026", full_name=None
    )

    assert user.email == "ana@umb.edu.co"
    assert user.password_hash != "Clave-Segura-2026"
    assert user.role is Role.USER


def test_register_duplicate_raises(repo: InMemoryUserRepository, hasher: SpyHasher) -> None:
    register_user(repo, hasher, email="a@umb.edu.co", password="Clave-Segura-2026", full_name=None)

    with pytest.raises(EmailAlreadyRegistered):
        register_user(repo, hasher, email="A@umb.edu.co", password="Otra-Clave-1", full_name=None)


def test_login_returns_token_pair(
    repo: InMemoryUserRepository, hasher: SpyHasher, tokens: JwtTokenService
) -> None:
    register_user(repo, hasher, email="a@umb.edu.co", password="Clave-Segura-2026", full_name=None)

    pair = login_user(repo, hasher, tokens, email="A@umb.edu.co", password="Clave-Segura-2026")

    assert pair.expires_in == 900
    assert tokens.decode_access(pair.access_token).role is Role.USER


def test_login_unknown_user_still_spends_a_hash_verification(
    repo: InMemoryUserRepository, hasher: SpyHasher, tokens: JwtTokenService
) -> None:
    with pytest.raises(InvalidCredentials):
        login_user(repo, hasher, tokens, email="nadie@umb.edu.co", password="Clave-Segura-2026")

    assert hasher.verify_calls == [None]  # se ejecutó verify() aun sin usuario (anti-timing)


def test_refresh_fails_if_user_was_deactivated(
    repo: InMemoryUserRepository, hasher: SpyHasher, tokens: JwtTokenService
) -> None:
    user = register_user(
        repo, hasher, email="a@umb.edu.co", password="Clave-Segura-2026", full_name=None
    )
    pair = login_user(repo, hasher, tokens, email=user.email, password="Clave-Segura-2026")
    repo.users[user.id] = User(**{**user.__dict__, "is_active": False})

    with pytest.raises(InvalidToken):
        refresh_access_token(repo, tokens, refresh_token=pair.refresh_token)
