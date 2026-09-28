from datetime import UTC, datetime
from enum import Enum


class Severity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class DomainError(Exception):
    """Base class for domain errors.

    ``name`` and ``occurred_at`` are populated automatically; ``message`` is
    the human-readable text (so ``str(err)`` / ``err.args`` work like any
    exception). Subclasses set their own ``code`` / ``severity`` / ``http_status``
    class defaults.

    Example:
        class SeatLimitExceeded(DomainError):
            code = "SEAT_LIMIT_EXCEEDED"
            http_status = 409
            severity = Severity.WARNING
    """

    code: str = "DOMAIN_ERROR"
    severity: Severity = Severity.ERROR
    http_status: int = 400

    def __init__(self, message: str, *, context: str | None = None) -> None:
        self.name = type(self).__name__
        self.message = message
        self.context = context
        self.occurred_at = datetime.now(UTC)
        super().__init__(message)


class InvalidEntityIdError(DomainError):
    """Raised when an entity id does not match the EntityId format."""

    code = "INVALID_ENTITY_ID"

    def __init__(self, value: object) -> None:
        super().__init__(
            f"Invalid entity id {value!r}: expected a lowercase letter "
            f"followed by 1-31 lowercase letters or digits",
            context=str(value),
        )


class NotFoundError(DomainError):
    """Raised when an aggregate/entity that should exist was not found."""

    code = "NOT_FOUND"
    http_status = 404


class ConflictError(DomainError):
    """Raised on a state conflict, e.g. optimistic-concurrency or uniqueness violation."""

    code = "CONFLICT"
    http_status = 409
