"""Re-export the users context errors from the package root.

(The module lives at ``errors.errors``; these aliases keep the canonical
import path — ``socialcrm.users.domain.errors`` — short.)
"""

from .errors import (
    DirectoryAlreadyExistsError,
    DirectoryHasNoSiteError,
    EmailAlreadyRegisteredError,
    EmployeeAlreadyActiveError,
    EmployeeAlreadyInactiveError,
    EmployeeWithThisNumberAlreadyExistsError,
    InvalidEmployeeAssignmentDatesError,
    OverlappingEmployeeAssignmentError,
    PrincipalSiteCannotBeDeactivatedError,
    RegistrationClosedError,
    RolePermissionDeniedError,
    SiteInactiveError,
    SiteNotInDirectoryError,
)

__all__ = [
    "DirectoryAlreadyExistsError",
    "DirectoryHasNoSiteError",
    "EmailAlreadyRegisteredError",
    "EmployeeAlreadyActiveError",
    "EmployeeAlreadyInactiveError",
    "EmployeeWithThisNumberAlreadyExistsError",
    "InvalidEmployeeAssignmentDatesError",
    "OverlappingEmployeeAssignmentError",
    "PrincipalSiteCannotBeDeactivatedError",
    "RegistrationClosedError",
    "RolePermissionDeniedError",
    "SiteInactiveError",
    "SiteNotInDirectoryError",
]
