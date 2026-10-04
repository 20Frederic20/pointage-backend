from core.domain.errors import DomainError, Severity


class InvalidTimezoneError(DomainError):
    """Raised when a time profile uses an unknown IANA timezone."""

    code = "INVALID_TIMEZONE"
    http_status = 422
    severity = Severity.WARNING


class InvalidTimeProfileDayError(DomainError):
    """Raised when a profile day ends before it starts or has a negative duration."""

    code = "INVALID_TIME_PROFILE_DAY"
    http_status = 422
    severity = Severity.WARNING


class DuplicateDayOfWeekError(DomainError):
    """Raised when a profile version defines the same day of week twice."""

    code = "DUPLICATE_DAY_OF_WEEK"
    http_status = 422
    severity = Severity.WARNING


class InvalidVersionEffectiveDateError(DomainError):
    """Raised when a new profile version does not start after the previous one."""

    code = "INVALID_VERSION_EFFECTIVE_DATE"
    http_status = 422
    severity = Severity.WARNING


class TimeProfileVersionNotFoundError(DomainError):
    """Raised when a schedule references an unknown time profile version."""

    code = "TIME_PROFILE_VERSION_NOT_FOUND"
    http_status = 404
    severity = Severity.WARNING


class InvalidScheduleDatesError(DomainError):
    """Raised when a schedule ends before it starts."""

    code = "INVALID_SCHEDULE_DATES"
    http_status = 422
    severity = Severity.WARNING


class OverlappingEmployeeScheduleError(DomainError):
    """Raised when an employee would have two schedules on the same date."""

    code = "OVERLAPPING_EMPLOYEE_SCHEDULE"
    http_status = 409
    severity = Severity.WARNING
