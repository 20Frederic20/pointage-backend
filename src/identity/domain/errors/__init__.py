"""Re-export the users context errors from the package root.

(The module lives at ``errors.errors``; these aliases keep the canonical
import path — ``socialcrm.users.domain.errors`` — short.)
"""

from .errors import (
    EmailAlreadyRegisteredError,
    EmployeeWithThisNumberAlreadyExistsError,
    RegistrationClosedError,
    RolePermissionDeniedError,
)

__all__ = [
    "EmailAlreadyRegisteredError",
    "EmployeeWithThisNumberAlreadyExistsError",
    "RegistrationClosedError",
    "RolePermissionDeniedError",
]
