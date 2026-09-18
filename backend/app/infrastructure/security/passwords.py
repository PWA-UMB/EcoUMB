"""Hash de contraseñas con bcrypt (RNF-04/05). Se usa ``bcrypt`` directo: ``passlib`` es
incompatible con bcrypt >= 4.1 (ADR-004)."""

import bcrypt

BCRYPT_MAX_BYTES = 72


class BcryptPasswordHasher:
    def __init__(self, rounds: int = 12) -> None:
        self._rounds = rounds
        # Hash señuelo: permite gastar el mismo trabajo cuando el usuario no existe.
        self._decoy_hash = self.hash("decoy-password-not-a-real-credential")

    def hash(self, password: str) -> str:
        raw = password.encode("utf-8")
        if len(raw) > BCRYPT_MAX_BYTES:
            raise ValueError("La contraseña excede los 72 bytes que admite bcrypt")
        return bcrypt.hashpw(raw, bcrypt.gensalt(rounds=self._rounds)).decode("ascii")

    def verify(self, password: str, password_hash: str | None) -> bool:
        raw = password.encode("utf-8")
        target = (password_hash or self._decoy_hash).encode("ascii")
        if len(raw) > BCRYPT_MAX_BYTES:
            return False
        matches = bcrypt.checkpw(raw, target)
        return matches and password_hash is not None
