class DomainError(Exception):
    """Base de los errores de negocio; la capa de interfaces los traduce a HTTP."""


class EmailAlreadyRegistered(DomainError):
    pass


class InvalidCredentials(DomainError):
    """Correo inexistente, contraseña incorrecta o cuenta inactiva (no se distingue)."""


class InvalidToken(DomainError):
    pass


class InvalidImage(DomainError):
    """Base de los errores de validación de la imagen subida (RF-09, RF-10)."""


class UnsupportedImageType(InvalidImage):
    pass


class EmptyImage(InvalidImage):
    pass


class ImageTooLarge(InvalidImage):
    pass


class CatalogUnavailable(DomainError):
    """No hay clases activas que predecir (base sin sembrar)."""


class UnknownWasteItem(DomainError):
    """El código de objeto no existe en el catálogo activo."""


class ClassificationNotFound(DomainError):
    """No existe, o no pertenece al usuario: no se distingue para no filtrar información."""
