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


class EmployeeHasAlreadyPunchedThisTypeOfEntryError(DomainError):
    """Raised when an employee has already punched this type of entry."""

    code = "EMPLOYEE_ALREADY_PUNCHED_ENTRY_TYPE"
    http_status = 409
    severity = Severity.WARNING