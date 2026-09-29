"""Application layer of the users bounded context — commands, queries,
handlers, DTOs, and integration-event plumbing."""

from .commands import (
    DeactivateUserCommand,
    RecordUserActivityCommand,
    RegisterUserCommand,
    UpdateDirectoryCommand,
    UpdateUserProfileCommand,
)
from .consumers import (
    DirectoryCreatedConsumer,
    UserDeactivatedConsumer,
    UserRegisteredConsumer,
    UserRoleChangedConsumer,
)
from .dtos import (
    DirectoryDTO,
    UserCredentialsDTO,
    UserDTO,
    UsersPageDTO,
)
from .handlers import (
    DeactivateUserHandler,
    GetDirectoryByIdHandler,
    GetUserByEmailHandler,
    GetUserByIdHandler,
    GetUsersHandler,
    RecordUserActivityHandler,
    RegisterUserHandler,
    UpdateUserProfileHandler,
)
from .notifications import USERS_EVENT_MAPPERS
from .ports import PasswordHasher
from .queries import (
    GetDirectoryByIdQuery,
    GetUserByEmailQuery,
    GetUserByIdQuery,
    GetUsersQuery,
)

__all__ = [
    "USERS_EVENT_MAPPERS",
    "CreateInviteCommand",
    "DeactivateUserCommand",
    "DeactivateUserHandler",
    "DirectoryCreatedConsumer",
    "DirectoryDTO",
    "GetDirectoryByIdHandler",
    "GetDirectoryByIdQuery",
    "GetUserByEmailHandler",
    "GetUserByEmailQuery",
    "GetUserByIdHandler",
    "GetUserByIdQuery",
    "GetUsersHandler",
    "GetUsersQuery",
    "InviteDTO",
    "PasswordHasher",
    "RecordUserActivityCommand",
    "RecordUserActivityHandler",
    "RegisterUserCommand",
    "RegisterUserHandler",
    "UpdateDirectoryCommand",
    "UpdateDirectoryHandler",
    "UpdateUserProfileCommand",
    "UpdateUserProfileHandler",
    "UserCredentialsDTO",
    "UserDTO",
    "UserDeactivatedConsumer",
    "UserRegisteredConsumer",
    "UserRoleChangedConsumer",
    "UsersPageDTO",
]
