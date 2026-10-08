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


class DirectoryAlreadyExistsError(DomainError):

    code = "DIRECTORY_ALREADY_EXISTS"
    http_status = 409
    severity = Severity.WARNING


class SiteInactiveError(DomainError):
    """Raised when an assignment targets a deactivated site."""

    code = "SITE_INACTIVE"
    http_status = 409
    severity = Severity.WARNING


class InvalidEmployeeAssignmentDatesError(DomainError):
    """Raised when an assignment ends before it starts."""

    code = "INVALID_EMPLOYEE_ASSIGNMENT_DATES"
    http_status = 422
    severity = Severity.WARNING


class OverlappingEmployeeAssignmentError(DomainError):
    """Raised when an employee would have two assignments on the same date."""

    code = "OVERLAPPING_EMPLOYEE_ASSIGNMENT"
    http_status = 409
    severity = Severity.WARNING


class EmployeeWithThisNumberAlreadyExistsError(DomainError):

    code = "EMPLOYEE_WITH_THIS_NUMBER_ALREADY_EXISTS"
    http_status = 409
    severity = Severity.WARNING


class SiteNotInDirectoryError(DomainError):
    """Raised when an assignment names a site of another directory."""

    code = "SITE_NOT_IN_DIRECTORY"
    http_status = 422
    severity = Severity.WARNING


class DirectoryHasNoSiteError(DomainError):
    """Raised when assigning to a directory that has no site yet."""

    code = "DIRECTORY_HAS_NO_SITE"
    http_status = 409
    severity = Severity.WARNING


class PrincipalSiteCannotBeDeactivatedError(DomainError):
    """Raised when deactivating a principal site: make another site principal first."""

    code = "PRINCIPAL_SITE_CANNOT_BE_DEACTIVATED"
    http_status = 409
    severity = Severity.WARNING
