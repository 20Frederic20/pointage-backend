"""Re-export the users context errors from the package root.

(The module lives at ``errors.errors``; these aliases keep the canonical
import path — ``socialcrm.users.domain.errors`` — short.)
"""

from .errors import (
    AlreadyActiveInCompanyError,
    AssignmentInPastError,
    DirectoryOutsideCompanyError,
    EmployeeInactiveError,
    FutureAssignmentExistsError,
    RoleCeilingError,
    SelfDeactivationError,
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
    "AlreadyActiveInCompanyError",
    "AssignmentInPastError",
    "DirectoryOutsideCompanyError",
    "EmployeeInactiveError",
    "FutureAssignmentExistsError",
    "RoleCeilingError",
    "SelfDeactivationError",
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
