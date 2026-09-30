"""Application layer of the users bounded context — commands, queries,
handlers, DTOs, and integration-event plumbing."""

from .commands import (
    CreateEmployeeCommand,
    DeactivateUserCommand,
    RecordUserActivityCommand,
    RegisterUserCommand,
    UpdateDirectoryCommand,
    UpdateUserProfileCommand,
)
from .consumers import (
    DirectoryCreatedConsumer,
    EmployeeCreatedConsumer,
    UserDeactivatedConsumer,
    UserRegisteredConsumer,
    UserRoleChangedConsumer,
)
from .dtos import (
    DirectoryDTO,
    EmployeeDTO,
    EmployeesPageDTO,
    UserCredentialsDTO,
    UserDTO,
    UsersPageDTO,
)
from .handlers import (
    CreateEmployeeHandler,
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
    GetEmployeeByEmployeeNumberQuery,
    GetEmployeeByIdQuery,
    GetEmployeesQuery,
    GetUserByEmailQuery,
    GetUserByIdQuery,
    GetUsersQuery,
)

__all__ = [
    "USERS_EVENT_MAPPERS",
    "CreateEmployeeCommand",
    "CreateEmployeeHandler",
    "DeactivateUserCommand",
    "DeactivateUserHandler",
    "DirectoryCreatedConsumer",
    "DirectoryDTO",
    "EmployeeCreatedConsumer",
    "EmployeeDTO",
    "EmployeesPageDTO",
    "GetDirectoryByIdHandler",
    "GetDirectoryByIdQuery",
    "GetEmployeeByEmployeeNumberQuery",
    "GetEmployeeByIdQuery",
    "GetEmployeesQuery",
    "GetUserByEmailHandler",
    "GetUserByEmailQuery",
    "GetUserByIdHandler",
    "GetUserByIdQuery",
    "GetUsersHandler",
    "GetUsersQuery",
    "PasswordHasher",
    "RecordUserActivityCommand",
    "RecordUserActivityHandler",
    "RegisterUserCommand",
    "RegisterUserHandler",
    "UpdateDirectoryCommand",
    "UpdateUserProfileCommand",
    "UpdateUserProfileHandler",
    "UserCredentialsDTO",
    "UserDTO",
    "UserDeactivatedConsumer",
    "UserRegisteredConsumer",
    "UserRoleChangedConsumer",
    "UsersPageDTO",
]
