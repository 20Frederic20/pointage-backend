"""The auth context's composition root — request-scope wiring."""

from dataclasses import dataclass, field

from cqrs.requests.map import RequestMap
from sqlalchemy.ext.asyncio import AsyncSession

from core.application import ApplicationMediator, HandlerContainer, IUnitOfWork
from core.domain.events import BaseEvent, IEventBus
from core.infrastructure.database import SQLAlchemyUnitOfWork
from core.infrastructure.events import EventBusEmitter
from core.infrastructure.outbox import TransactionalOutbox
from identity.application.ports import PasswordHasher

from ..application import (
    LoginCommand,
    LogoutCommand,
    RefreshSessionCommand,
    RequestLoginCodeCommand,
    SelectEmployeeCommand,
    VerifyLoginCodeCommand,
)
from ..application.handlers import (
    LoginHandler,
    LogoutHandler,
    RefreshSessionHandler,
    RequestLoginCodeHandler,
    SelectEmployeeHandler,
    VerifyLoginCodeHandler,
)
from ..application.ports import TokenIssuer, UserAccounts
from .persistence.login_code_repository import LoginCodeRepository
from .persistence.refresh_token_repository import RefreshTokenRepository


@dataclass
class AuthContainer:
    """Request-scope wiring for the auth bounded context."""

    refresh_token_repository: RefreshTokenRepository
    login_code_repository: LoginCodeRepository
    unit_of_work: IUnitOfWork
    event_bus: IEventBus[BaseEvent]
    user_accounts: UserAccounts
    password_hasher: PasswordHasher
    token_issuer: TokenIssuer
    event_outbox: TransactionalOutbox | None = None
    _mediator: ApplicationMediator = field(init=False, repr=False)

    def __post_init__(self) -> None:
        request_map = RequestMap()
        request_map.bind(LoginCommand, LoginHandler)
        request_map.bind(RefreshSessionCommand, RefreshSessionHandler)
        request_map.bind(LogoutCommand, LogoutHandler)
        request_map.bind(RequestLoginCodeCommand, RequestLoginCodeHandler)
        request_map.bind(VerifyLoginCodeCommand, VerifyLoginCodeHandler)
        request_map.bind(SelectEmployeeCommand, SelectEmployeeHandler)

        self._mediator = ApplicationMediator(
            request_map=request_map,
            container=HandlerContainer(self._resolve_handler),
            event_emitter=EventBusEmitter(self.event_bus),
        )

    def _resolve_handler(self, handler_type: type):
        """Build a handler bound to this request scope."""
        if handler_type is LoginHandler:
            return LoginHandler(
                unit_of_work=self.unit_of_work,
                refresh_token_repository=self.refresh_token_repository,
                user_accounts=self.user_accounts,
                password_hasher=self.password_hasher,
                token_issuer=self.token_issuer,
                event_outbox=self.event_outbox,
            )
        if handler_type is RefreshSessionHandler:
            return RefreshSessionHandler(
                unit_of_work=self.unit_of_work,
                refresh_token_repository=self.refresh_token_repository,
                user_accounts=self.user_accounts,
                token_issuer=self.token_issuer,
                event_outbox=self.event_outbox,
            )
        if handler_type is LogoutHandler:
            return LogoutHandler(
                unit_of_work=self.unit_of_work,
                refresh_token_repository=self.refresh_token_repository,
                token_issuer=self.token_issuer,
                event_outbox=self.event_outbox,
            )
        if handler_type is RequestLoginCodeHandler:
            return RequestLoginCodeHandler(
                unit_of_work=self.unit_of_work,
                login_code_repository=self.login_code_repository,
                user_accounts=self.user_accounts,
                token_issuer=self.token_issuer,
                event_outbox=self.event_outbox,
            )
        if handler_type is VerifyLoginCodeHandler:
            return VerifyLoginCodeHandler(
                unit_of_work=self.unit_of_work,
                login_code_repository=self.login_code_repository,
                refresh_token_repository=self.refresh_token_repository,
                user_accounts=self.user_accounts,
                token_issuer=self.token_issuer,
                event_outbox=self.event_outbox,
            )
        if handler_type is SelectEmployeeHandler:
            return SelectEmployeeHandler(
                unit_of_work=self.unit_of_work,
                refresh_token_repository=self.refresh_token_repository,
                user_accounts=self.user_accounts,
                token_issuer=self.token_issuer,
                event_outbox=self.event_outbox,
            )
        raise TypeError(
            f"No auth-scope wiring for handler {handler_type.__name__}"
        )

    async def send(self, request):
        """Dispatch an auth command and return its result."""
        return await self._mediator.send(request)


def build_auth_container(
    *,
    session: AsyncSession,
    event_bus: IEventBus[BaseEvent],
    user_accounts: UserAccounts,
    password_hasher: PasswordHasher,
    token_issuer: TokenIssuer,
    event_outbox: TransactionalOutbox | None = None,
) -> AuthContainer:
    """Build a request-scoped auth container."""
    return AuthContainer(
        refresh_token_repository=RefreshTokenRepository(session),
        login_code_repository=LoginCodeRepository(session),
        unit_of_work=SQLAlchemyUnitOfWork(session),
        event_bus=event_bus,
        user_accounts=user_accounts,
        password_hasher=password_hasher,
        token_issuer=token_issuer,
        # No auth event is published yet: an empty mapper table makes the
        # outbox fail loudly if one is recorded before its mapper exists.
        event_outbox=event_outbox
        or TransactionalOutbox(session=session, mappers={}),
    )
