"""The users context's composition root — request-scope wiring.

One container per request: repositories and the unit of work share one
``AsyncSession``, and the resolver builds handler instances bound to that
scope. This is the architecture-sanctioned manual DI (no framework) — see
``social_crm_ddd_architecture.md``.
"""

from dataclasses import dataclass, field

from cqrs.requests.map import RequestMap
from sqlalchemy.ext.asyncio import AsyncSession

from core.application import (
    ApplicationMediator,
    HandlerContainer,
    IUnitOfWork,
)
from core.domain.events import BaseEvent, IEventBus
from core.infrastructure.database import SQLAlchemyUnitOfWork
from core.infrastructure.events import EventBusEmitter
from core.infrastructure.outbox import TransactionalOutbox
from identity.application.commands.create_directory import CreateDirectoryCommand
from identity.application.handlers.create_directory_handler import (
    CreateDirectoryHandler,
)
from identity.infrastructure.persistence.employee_repository import EmployeeRepository

from ..application import (
    USERS_EVENT_MAPPERS,
    ActivateSiteCommand,
    ActivateSiteHandler,
    AssignEmployeeCommand,
    AssignEmployeeHandler,
    ClearUserPasswordCommand,
    ClearUserPasswordHandler,
    CreateEmployeeCommand,
    CreateEmployeeHandler,
    CreateSiteCommand,
    CreateSiteHandler,
    DeactivateSiteCommand,
    DeactivateSiteHandler,
    DeactivateUserCommand,
    DeactivateUserHandler,
    EndEmployeeAssignmentCommand,
    EndEmployeeAssignmentHandler,
    GetDirectoryByIdHandler,
    GetDirectoryByIdQuery,
    GetEmployeeAssignmentsHandler,
    GetEmployeeAssignmentsQuery,
    GetSiteByIdHandler,
    GetSiteByIdQuery,
    GetUserByEmailHandler,
    GetUserByEmailQuery,
    GetUserByIdHandler,
    GetUserByIdQuery,
    GetUsersHandler,
    GetUsersQuery,
    RecordUserActivityCommand,
    RecordUserActivityHandler,
    RegisterUserCommand,
    RegisterUserHandler,
    UpdateUserProfileCommand,
    UpdateUserProfileHandler,
)
from ..application.ports import PasswordHasher
from .persistence.directory_repository import DirectoryRepository
from .persistence.employee_assignment_repository import EmployeeAssignmentRepository
from .persistence.site_repository import SiteRepository
from .persistence.user_repository import UserRepository


@dataclass
class UsersContainer:
    """Request-scope wiring for the users bounded context."""

    user_repository: UserRepository
    directory_repository: DirectoryRepository
    employee_repository: EmployeeRepository
    site_repository: SiteRepository
    employee_assignment_repository: EmployeeAssignmentRepository
    unit_of_work: IUnitOfWork
    event_bus: IEventBus[BaseEvent]
    password_hasher: PasswordHasher
    event_outbox: TransactionalOutbox | None = None
    _mediator: ApplicationMediator = field(init=False, repr=False)

    def __post_init__(self) -> None:
        request_map = RequestMap()
        request_map.bind(CreateDirectoryCommand, CreateDirectoryHandler)
        request_map.bind(CreateEmployeeCommand, CreateEmployeeHandler)
        request_map.bind(CreateSiteCommand, CreateSiteHandler)
        request_map.bind(ActivateSiteCommand, ActivateSiteHandler)
        request_map.bind(DeactivateSiteCommand, DeactivateSiteHandler)
        request_map.bind(AssignEmployeeCommand, AssignEmployeeHandler)
        request_map.bind(EndEmployeeAssignmentCommand, EndEmployeeAssignmentHandler)
        request_map.bind(RegisterUserCommand, RegisterUserHandler)
        request_map.bind(UpdateUserProfileCommand, UpdateUserProfileHandler)
        request_map.bind(DeactivateUserCommand, DeactivateUserHandler)
        request_map.bind(ClearUserPasswordCommand, ClearUserPasswordHandler)
        request_map.bind(RecordUserActivityCommand, RecordUserActivityHandler)
        request_map.bind(GetUserByEmailQuery, GetUserByEmailHandler)
        request_map.bind(GetUserByIdQuery, GetUserByIdHandler)
        request_map.bind(GetUsersQuery, GetUsersHandler)
        request_map.bind(GetDirectoryByIdQuery, GetDirectoryByIdHandler)
        request_map.bind(GetSiteByIdQuery, GetSiteByIdHandler)
        request_map.bind(GetEmployeeAssignmentsQuery, GetEmployeeAssignmentsHandler)

        self._mediator = ApplicationMediator(
            request_map=request_map,
            container=HandlerContainer(self._resolve_handler),
            event_emitter=EventBusEmitter(self.event_bus),
        )

    def _resolve_handler(self, handler_type: type):
        """Build a handler bound to this request scope."""
        if handler_type is RegisterUserHandler:
            return RegisterUserHandler(
                unit_of_work=self.unit_of_work,
                user_repository=self.user_repository,
                password_hasher=self.password_hasher,
                event_outbox=self.event_outbox,
            )
        if handler_type in (
            ClearUserPasswordHandler,
            DeactivateUserHandler,
            RecordUserActivityHandler,
            UpdateUserProfileHandler,
        ):
            return handler_type(
                unit_of_work=self.unit_of_work,
                user_repository=self.user_repository,
                event_outbox=self.event_outbox,
            )
        if handler_type is CreateDirectoryHandler:
            return CreateDirectoryHandler(
                unit_of_work=self.unit_of_work,
                directory_repository=self.directory_repository,
                site_repository=self.site_repository,
                event_outbox=self.event_outbox,
            )
        if handler_type is CreateEmployeeHandler:
            return CreateEmployeeHandler(
                unit_of_work=self.unit_of_work,
                employee_repository=self.employee_repository,
                employee_assignment_repository=self.employee_assignment_repository,
                directory_repository=self.directory_repository,
                site_repository=self.site_repository,
                event_outbox=self.event_outbox,
            )
        if handler_type in (CreateSiteHandler, ActivateSiteHandler, DeactivateSiteHandler):
            return handler_type(
                unit_of_work=self.unit_of_work,
                site_repository=self.site_repository,
                event_outbox=self.event_outbox,
            )
        if handler_type is AssignEmployeeHandler:
            return AssignEmployeeHandler(
                unit_of_work=self.unit_of_work,
                employee_assignment_repository=self.employee_assignment_repository,
                employee_repository=self.employee_repository,
                directory_repository=self.directory_repository,
                site_repository=self.site_repository,
                event_outbox=self.event_outbox,
            )
        if handler_type is EndEmployeeAssignmentHandler:
            return EndEmployeeAssignmentHandler(
                unit_of_work=self.unit_of_work,
                employee_assignment_repository=self.employee_assignment_repository,
                event_outbox=self.event_outbox,
            )
        if handler_type is GetUserByEmailHandler:
            return GetUserByEmailHandler(user_repository=self.user_repository)
        if handler_type is GetUserByIdHandler:
            return GetUserByIdHandler(user_repository=self.user_repository)
        if handler_type is GetUsersHandler:
            return GetUsersHandler(user_repository=self.user_repository)
        if handler_type is GetDirectoryByIdHandler:
            return GetDirectoryByIdHandler(
                directory_repository=self.directory_repository
            )
        if handler_type is GetSiteByIdHandler:
            return GetSiteByIdHandler(site_repository=self.site_repository)
        if handler_type is GetEmployeeAssignmentsHandler:
            return GetEmployeeAssignmentsHandler(
                employee_assignment_repository=self.employee_assignment_repository
            )
        raise TypeError(
            f"No users-scope wiring for handler {handler_type.__name__}"
        )

    async def send(self, request):
        """Dispatch a users command/query and return its result."""
        return await self._mediator.send(request)


def build_users_container(
    *,
    session: AsyncSession,
    event_bus: IEventBus[BaseEvent],
    password_hasher: PasswordHasher,
    event_outbox: TransactionalOutbox | None = None,
) -> UsersContainer:
    """Wire the real adapters over one request-scoped session."""
    return UsersContainer(
        user_repository=UserRepository(session),
        directory_repository=DirectoryRepository(session),
        employee_repository=EmployeeRepository(session),
        site_repository=SiteRepository(session),
        employee_assignment_repository=EmployeeAssignmentRepository(session),
        unit_of_work=SQLAlchemyUnitOfWork(session),
        event_bus=event_bus,
        password_hasher=password_hasher,
        event_outbox=event_outbox
        or TransactionalOutbox(session=session, mappers=USERS_EVENT_MAPPERS),
    )
