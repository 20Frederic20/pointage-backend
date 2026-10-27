from core.domain.errors import DomainError, Severity


class PunchAlreadyExistsError(DomainError):
    """Raised when a punch already exists for the given employee and date."""

    code = "PUNCH_ALREADY_EXISTS"
    http_status = 409
    severity = Severity.WARNING


class PunchNotFoundError(DomainError):
    """Raised when a punch is not found for the given employee and date."""

    code = "PUNCH_NOT_FOUND"
    http_status = 404
    severity = Severity.WARNING


class PunchConflictError(DomainError):
    """Raised when there is a conflict with the punch data."""

    code = "PUNCH_CONFLICT"
    http_status = 409
    severity = Severity.WARNING


class EmployeeNotAssignedError(DomainError):
    """Raised when an employee punches without an assignment covering today."""

    code = "EMPLOYEE_NOT_ASSIGNED"
    http_status = 409
    severity = Severity.WARNING


class TooFarFromWorkplaceError(DomainError):
    """Raised when an employee punches too far from the directory of their assignment."""

    code = "TOO_FAR_FROM_WORKPLACE"
    http_status = 422
    severity = Severity.WARNING

    def __init__(self, message: str, *, context: str | None = None, distance_meters: float | None = None) -> None:
        super().__init__(message, context=context)
        self.distance_meters = distance_meters


class TimeEntryNotPendingError(DomainError):
    """Raised when a decision targets a time entry that is not waiting for one."""

    code = "TIME_ENTRY_NOT_PENDING"
    http_status = 409
    severity = Severity.WARNING


class SelfAssistedPunchError(DomainError):
    """Raised when the assisted path targets the caller's own employee number."""

    code = "SELF_ASSISTED_PUNCH"
    http_status = 409
    severity = Severity.WARNING


class InvalidPhotoError(DomainError):
    """Raised when the selfie is missing, empty, too large or not a JPEG / PNG."""

    code = "INVALID_PHOTO"
    http_status = 422
    severity = Severity.WARNING
