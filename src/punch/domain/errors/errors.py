from core.domain.errors import DomainError, Severity


class PunchAlreadyExistsError(DomainError):
    """Raised when a punch already exists for the given employee and date."""

    code = "PUNCH_ALREADY_EXISTS"
    http_status = 409
    severity = Severity.WARNING