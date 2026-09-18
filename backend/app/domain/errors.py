class DomainError(Exception):
    """Base de los errores de negocio; la capa de interfaces los traduce a HTTP."""


class EmailAlreadyRegistered(DomainError):
    pass


class InvalidCredentials(DomainError):
    """Correo inexistente, contraseña incorrecta o cuenta inactiva (no se distingue)."""


class InvalidToken(DomainError):
    pass
