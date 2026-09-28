"""Application layer of the users bounded context — commands, queries,
handlers, DTOs, and integration-event plumbing."""

from .commands import (
    ChangeUserRoleCommand,
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
    ChangeUserRoleHandler,
    DeactivateUserHandler,
    GetDirectoryByIdHandler,
    GetUserByEmailHandler,
    GetUserByIdHandler,
    GetUsersHandler,
    RecordUserActivityHandler,
    RegisterUserHandler,
    UpdateDirectoryHandler,
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
    "ChangeUserRoleCommand",
    "ChangeUserRoleHandler",
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
