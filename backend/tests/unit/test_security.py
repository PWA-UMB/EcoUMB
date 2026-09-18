import uuid
from collections.abc import Mapping
from datetime import timedelta

import pytest

from app.core.keys import generate_rsa_keypair
from app.domain.errors import InvalidToken
from app.domain.roles import Role
from app.infrastructure.security.passwords import BcryptPasswordHasher
from app.infrastructure.security.tokens import JwtTokenService


@pytest.fixture(scope="module")
def keypair() -> tuple[str, str]:
    return generate_rsa_keypair()


def _service(keypair: tuple[str, str], **overrides: timedelta) -> JwtTokenService:
    private, public = keypair
    return JwtTokenService(
        private_key=private,
        public_key=public,
        access_ttl=overrides.get("access_ttl", timedelta(minutes=15)),
        refresh_ttl=overrides.get("refresh_ttl", timedelta(days=7)),
    )


# ----------------------------------------------------------------------- bcrypt
def test_hash_uses_bcrypt_with_requested_cost() -> None:
    hasher = BcryptPasswordHasher(rounds=12)

    hashed = hasher.hash("Clave-Segura-2026")

    assert hashed.startswith("$2b$12$")
    assert hasher.verify("Clave-Segura-2026", hashed)
    assert not hasher.verify("otra-clave", hashed)


def test_verify_without_stored_hash_is_false_but_still_runs() -> None:
    hasher = BcryptPasswordHasher(rounds=4)

    assert hasher.verify("cualquiera", None) is False


def test_verify_rejects_passwords_longer_than_bcrypt_limit() -> None:
    hasher = BcryptPasswordHasher(rounds=4)
    hashed = hasher.hash("a" * 72)

    assert hasher.verify("a" * 73, hashed) is False
    with pytest.raises(ValueError):
        hasher.hash("a" * 73)


# -------------------------------------------------------------------------- JWT
def test_access_and_refresh_tokens_carry_their_type_and_role(keypair: tuple[str, str]) -> None:
    service = _service(keypair)
    user_id = uuid.uuid4()

    access = service.decode_access(service.create_access_token(user_id=user_id, role=Role.CLEANER))
    refresh = service.decode_refresh(
        service.create_refresh_token(user_id=user_id, role=Role.CLEANER)
    )

    assert (access.user_id, access.role, access.token_type) == (user_id, Role.CLEANER, "access")
    assert (refresh.user_id, refresh.token_type) == (user_id, "refresh")


def test_refresh_token_is_not_accepted_as_access(keypair: tuple[str, str]) -> None:
    service = _service(keypair)
    refresh = service.create_refresh_token(user_id=uuid.uuid4(), role=Role.USER)

    with pytest.raises(InvalidToken):
        service.decode_access(refresh)


def test_expired_token_is_rejected(keypair: tuple[str, str]) -> None:
    service = _service(keypair, access_ttl=timedelta(seconds=-1))
    token = service.create_access_token(user_id=uuid.uuid4(), role=Role.USER)

    with pytest.raises(InvalidToken):
        service.decode_access(token)


def test_token_signed_with_another_key_is_rejected(keypair: tuple[str, str]) -> None:
    attacker = _service(generate_rsa_keypair())
    forged = attacker.create_access_token(user_id=uuid.uuid4(), role=Role.ADMIN)

    with pytest.raises(InvalidToken):
        _service(keypair).decode_access(forged)


def test_tampered_token_is_rejected(keypair: tuple[str, str]) -> None:
    service = _service(keypair)
    token = service.create_access_token(user_id=uuid.uuid4(), role=Role.USER)
    header, payload, signature = token.split(".")

    with pytest.raises(InvalidToken):
        service.decode_access(f"{header}.{payload[:-2]}AA.{signature}")


def test_unsigned_token_is_rejected(keypair: tuple[str, str]) -> None:
    import base64
    import json

    def b64(data: Mapping[str, object]) -> str:
        return base64.urlsafe_b64encode(json.dumps(data).encode()).rstrip(b"=").decode()

    payload = {"sub": str(uuid.uuid4()), "role": "admin", "typ": "access", "iss": "ecoumb"}
    unsigned = f"{b64({'alg': 'none', 'typ': 'JWT'})}.{b64(payload)}."

    with pytest.raises(InvalidToken):
        _service(keypair).decode_access(unsigned)
