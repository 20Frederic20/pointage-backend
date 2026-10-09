"""Adapter for the :class:`UserAccounts` port, over identity's public API.

Auth only sends identity's own queries and commands through its container;
it never reads the ``users`` table. Each call opens its own sessions (write:
event store, read: read models), so identity's unit of work
(``RecordUserActivityCommand`` commits) can never commit or roll back auth's
transaction.

Lookups go through identity's queries, i.e. the read models: an account
created a moment ago can log in once the projection has caught up (~0.2 s).
"""

import logging

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from core.domain.events import BaseEvent, IEventBus
from identity.application import (
    GetEmployeeByEmployeeNumberQuery,
    GetUserByEmailQuery,
    GetUserByIdQuery,
    PasswordHasher,
    RecordUserActivityCommand,
)
from identity.infrastructure import build_users_container

from ..application.dtos import AccountCredentialsDTO, AccountDTO
from ..application.ports import UserAccounts

logger = logging.getLogger(__name__)


class IdentityUserAccounts(UserAccounts):
    def __init__(
        self,
        *,
        session_factory: async_sessionmaker[AsyncSession],
        read_session_factory: async_sessionmaker[AsyncSession],
        event_bus: IEventBus[BaseEvent],
        password_hasher: PasswordHasher,
    ) -> None:
        self._session_factory = session_factory
        self._read_session_factory = read_session_factory
        self._event_bus = event_bus
        self._password_hasher = password_hasher

    async def _send(self, request):
        async with self._session_factory() as write_session, self._read_session_factory() as read_session:
            users = build_users_container(
                write_session=write_session,
                read_session=read_session,
                event_bus=self._event_bus,
                password_hasher=self._password_hasher,
            )
            return await users.send(request)

    async def find_credentials(self, identifier: str) -> AccountCredentialsDTO | None:
        """An identifier with ``@`` is an email; anything else is an employee number."""
        email = identifier if "@" in identifier else await self._email_of_employee(identifier)
        if email is None:
            return None
        dto = await self._send(GetUserByEmailQuery(email=email))
        if dto is None:
            return None
        return AccountCredentialsDTO(
            id=dto.id,
            email=dto.email,
            role=str(dto.role),
            is_active=dto.is_active,
            password_hash=dto.password_hash,
        )

    async def _email_of_employee(self, employee_number: str) -> str | None:
        employee = await self._send(GetEmployeeByEmployeeNumberQuery(employee_number=employee_number))
        if employee is None:
            return None
        user = await self._send(GetUserByIdQuery(user_id=employee.user_id))
        return user.email if user is not None else None

    async def get_account(self, user_id: str) -> AccountDTO | None:
        dto = await self._send(GetUserByIdQuery(user_id=user_id))
        if dto is None:
            return None
        return AccountDTO(id=dto.id, role=str(dto.role), is_active=dto.is_active)

    async def record_activity(self, user_id: str) -> None:
        try:
            await self._send(RecordUserActivityCommand(user_id=user_id))
        except Exception:
            # Presence telemetry: a concurrent login bumping the user's version
            # (ConflictError) must not turn a valid login into an error.
            logger.warning("auth: could not record activity for user %s", user_id, exc_info=True)
