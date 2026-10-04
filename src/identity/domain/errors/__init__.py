"""Re-export the users context errors from the package root.

(The module lives at ``errors.errors``; these aliases keep the canonical
import path — ``socialcrm.users.domain.errors`` — short.)
"""

from .errors import (
    DirectoryAlreadyExistsError,
    EmailAlreadyRegisteredError,
    EmployeeWithThisNumberAlreadyExistsError,
    InvalidEmployeeAssignmentDatesError,
    OverlappingEmployeeAssignmentError,
    RegistrationClosedError,
    RolePermissionDeniedError,
    SiteInactiveError,
)

__all__ = [
    "DirectoryAlreadyExistsError",
    "EmailAlreadyRegisteredError",
    "EmployeeWithThisNumberAlreadyExistsError",
    "InvalidEmployeeAssignmentDatesError",
    "OverlappingEmployeeAssignmentError",
    "RegistrationClosedError",
    "RolePermissionDeniedError",
    "SiteInactiveError",
]
