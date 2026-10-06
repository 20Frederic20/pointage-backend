"""Adapter for the :class:`UserAccounts` port, over identity's public API.

Auth only sends identity's own queries and commands through its container;
it never reads the ``users`` table. Each call opens its own session, so
identity's unit of work (``RecordUserActivityCommand`` commits) can never
commit or roll back auth's transaction.
"""

import logging

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from core.domain.events import BaseEvent, IEventBus
from identity.application import (
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
        event_bus: IEventBus[BaseEvent],
        password_hasher: PasswordHasher,
    ) -> None:
        self._session_factory = session_factory
        self._event_bus = event_bus
        self._password_hasher = password_hasher

    async def _send(self, request):
        async with self._session_factory() as session:
            users = build_users_container(
                session=session,
                event_bus=self._event_bus,
                password_hasher=self._password_hasher,
            )
            return await users.send(request)

    async def find_credentials(self, email: str) -> AccountCredentialsDTO | None:
        dto = await self._send(GetUserByEmailQuery(email=email))
        if dto is None:
            return None
        return AccountCredentialsDTO(
            id=dto.id,
            role=str(dto.role),
            is_active=dto.is_active,
            password_hash=dto.password_hash,
        )

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
