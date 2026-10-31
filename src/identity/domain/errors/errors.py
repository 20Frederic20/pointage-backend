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


class EmployeeAlreadyActiveError(ConflictError):
    """Raised when reactivating an employee record that is already active."""

    code = "EMPLOYEE_ALREADY_ACTIVE"
    http_status = 409
    severity = Severity.WARNING


class EmployeeAlreadyInactiveError(ConflictError):
    """Raised when deactivating an employee record that is already inactive."""

    code = "EMPLOYEE_ALREADY_INACTIVE"
    http_status = 409
    severity = Severity.WARNING


class AssignmentInPastError(DomainError):
    """Raised when an assignment would start before today."""

    code = "ASSIGNMENT_IN_PAST"
    http_status = 422
    severity = Severity.WARNING


class FutureAssignmentExistsError(DomainError):
    """Raised when a transfer would overwrite an assignment already scheduled later."""

    code = "FUTURE_ASSIGNMENT_EXISTS"
    http_status = 409
    severity = Severity.WARNING


class DirectoryOutsideCompanyError(DomainError):
    """Raised when an assignment targets a directory outside the employee's company."""

    code = "DIRECTORY_OUTSIDE_COMPANY"
    http_status = 422
    severity = Severity.WARNING


class EmployeeInactiveError(DomainError):
    """Raised when an inactive (deactivated) employee record is asked to punch or be assigned."""

    code = "EMPLOYEE_INACTIVE"
    http_status = 409
    severity = Severity.WARNING


class RoleCeilingError(DomainError):
    """Raised when an actor grants, edits or changes a role above their own, or their own role."""

    code = "ROLE_CEILING"
    http_status = 403
    severity = Severity.WARNING


class SelfDeactivationError(DomainError):
    """Raised when an actor tries to deactivate one of their own employee records."""

    code = "SELF_DEACTIVATION"
    http_status = 403
    severity = Severity.WARNING


class AlreadyActiveInCompanyError(ConflictError):
    """Raised when a person would hold two active employee records in the same company."""

    code = "ALREADY_ACTIVE_IN_COMPANY"
    http_status = 409
    severity = Severity.WARNING
