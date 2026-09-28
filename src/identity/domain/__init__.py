"""Domain layer of the users-bounded context.

Aggregates: class:`User`,class:`Workspace`,class:`UserInvite` — plus
their ids, the role hierarchy, domain events, errors, repository ports and
specifications. Nothing here imports from the application, infrastructure or
interface layers, or from pydantic.
"""

from .errors.errors import (
    EmailAlreadyRegisteredError,
    RegistrationClosedError,
    RolePermissionDeniedError,
)
from .value_objects import DirectoryId, Role, UserId

__all__ = [
    "DirectoryId",
    "EmailAlreadyRegisteredError",
    "RegistrationClosedError",
    "Role",
    "RolePermissionDeniedError",
    "UserId",
]
