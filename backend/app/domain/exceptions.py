class DomainError(Exception):
    """Base de errores de dominio."""

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class NotFoundError(DomainError):
    pass


class ConflictError(DomainError):
    pass


class BusinessRuleError(DomainError):
    pass


class AuthenticationError(DomainError):
    pass
