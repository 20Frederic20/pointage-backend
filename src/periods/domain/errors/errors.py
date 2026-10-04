from core.domain.errors import DomainError, Severity


class InvalidPeriodDatesError(DomainError):
    """Raised when a period ends before it starts."""

    code = "INVALID_PERIOD_DATES"
    http_status = 422
    severity = Severity.WARNING


class OverlappingPeriodError(DomainError):
    """Raised when a new period overlaps an existing one."""

    code = "OVERLAPPING_PERIOD"
    http_status = 409
    severity = Severity.WARNING


class PeriodNotOpenError(DomainError):
    """Raised when locking a period that is not open."""

    code = "PERIOD_NOT_OPEN"
    http_status = 409
    severity = Severity.WARNING


class PeriodAlreadyClosedError(DomainError):
    """Raised when closing a period that is already closed."""

    code = "PERIOD_ALREADY_CLOSED"
    http_status = 409
    severity = Severity.WARNING


class PeriodHasBlockingAnomaliesError(DomainError):
    """Raised when closing a period that still has open blocking anomalies."""

    code = "PERIOD_HAS_BLOCKING_ANOMALIES"
    http_status = 409
    severity = Severity.WARNING
