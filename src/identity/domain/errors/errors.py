"""Domain errors of the users bounded context.

Each subclass sets ``code`` / ``http_status`` per the core convention; the
single FastAPI exception handler maps the whole hierarchy onto the camelCase
``DomainErrorSchema`` wire shape.
"""

from core.domain.errors import ConflictError, DomainError, Severity


class EmailAlreadyRegisteredError(ConflictError):
    """Raised when an email that must be unique is taken."""

    code = "EMAIL_ALREADY_REGISTERED"


class RegistrationClosedError(DomainError):
    """Raised on public signup after the first workspace exists.

    Signup bootstraps the very first workspace + owner; afterwards new
    users join exclusively by invitation.
    """

    code = "REGISTRATION_CLOSED"
    http_status = 403
    severity = Severity.WARNING


class RolePermissionDeniedError(DomainError):
    """Raised when a role is not allowed to perform the action."""

    code = "ROLE_PERMISSION_DENIED"
    http_status = 403
    severity = Severity.WARNING
