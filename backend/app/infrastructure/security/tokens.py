"""Emisión y validación de JWT firmados con RS256 (RNF-04). Usa PyJWT (ADR-003)."""

import uuid
from datetime import UTC, datetime, timedelta

import jwt

from app.domain.errors import InvalidToken
from app.domain.ports import TokenClaims, TokenType
from app.domain.roles import Role

ALGORITHM = "RS256"
REQUIRED_CLAIMS = ["exp", "iat", "sub", "typ", "iss", "aud"]


class JwtTokenService:
    def __init__(
        self,
        *,
        private_key: str,
        public_key: str,
        access_ttl: timedelta,
        refresh_ttl: timedelta,
        issuer: str = "ecoumb",
        audience: str = "ecoumb-api",
    ) -> None:
        self.private_key = private_key
        self.public_key = public_key
        self._access_ttl = access_ttl
        self._refresh_ttl = refresh_ttl
        self._issuer = issuer
        self._audience = audience

    @property
    def access_ttl_seconds(self) -> int:
        return int(self._access_ttl.total_seconds())

    def create_access_token(self, *, user_id: uuid.UUID, role: Role) -> str:
        return self._encode(user_id, role, "access", self._access_ttl)

    def create_refresh_token(self, *, user_id: uuid.UUID, role: Role) -> str:
        return self._encode(user_id, role, "refresh", self._refresh_ttl)

    def decode_access(self, token: str) -> TokenClaims:
        return self._decode(token, expected="access")

    def decode_refresh(self, token: str) -> TokenClaims:
        return self._decode(token, expected="refresh")

    def _encode(self, user_id: uuid.UUID, role: Role, token_type: TokenType, ttl: timedelta) -> str:
        issued_at = datetime.now(tz=UTC)
        claims = {
            "sub": str(user_id),
            "role": role.value,
            "typ": token_type,
            "jti": uuid.uuid4().hex,
            "iss": self._issuer,
            "aud": self._audience,
            "iat": int(issued_at.timestamp()),
            "exp": int((issued_at + ttl).timestamp()),
        }
        return jwt.encode(claims, self.private_key, algorithm=ALGORITHM)

    def _decode(self, token: str, *, expected: TokenType) -> TokenClaims:
        try:
            payload = jwt.decode(
                token,
                self.public_key,
                algorithms=[ALGORITHM],  # fija el algoritmo: rechaza "none" y HS256
                issuer=self._issuer,
                audience=self._audience,
                options={"require": REQUIRED_CLAIMS},
            )
            if payload["typ"] != expected:
                raise InvalidToken
            return TokenClaims(
                user_id=uuid.UUID(payload["sub"]),
                role=Role(payload["role"]),
                token_type=expected,
                issued_at=datetime.fromtimestamp(payload["iat"], tz=UTC),
                expires_at=datetime.fromtimestamp(payload["exp"], tz=UTC),
            )
        except (jwt.PyJWTError, KeyError, ValueError) as error:
            raise InvalidToken from error
