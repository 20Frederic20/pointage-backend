from core.domain.errors import DomainError, Severity


class InvalidAbsencePeriodError(DomainError):
    """Raised when the absence ends before (or when) it starts."""

    code = "INVALID_ABSENCE_PERIOD"
    http_status = 422
    severity = Severity.WARNING


class AbsenceTypeInactiveError(DomainError):
    """Raised when an absence is declared with a deactivated absence type."""

    code = "ABSENCE_TYPE_INACTIVE"
    http_status = 409
    severity = Severity.WARNING


class AbsenceNotPendingError(DomainError):
    """Raised when approving or rejecting an absence that is no longer pending."""

    code = "ABSENCE_NOT_PENDING"
    http_status = 409
    severity = Severity.WARNING


class AbsenceNotApprovedError(DomainError):
    """Raised when a non-approved absence tries to neutralize an anomaly."""

    code = "ABSENCE_NOT_APPROVED"
    http_status = 409
    severity = Severity.WARNING


class AnomalyNotCoveredByAbsenceError(DomainError):
    """Raised when the anomaly belongs to another employee or falls outside the absence."""

    code = "ANOMALY_NOT_COVERED_BY_ABSENCE"
    http_status = 409
    severity = Severity.WARNING
