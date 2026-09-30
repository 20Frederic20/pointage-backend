"""Deactivating a member — ADMIN-only, never oneself."""

from collections.abc import Sequence

from core.application import CommandHandler, IUnitOfWork
from core.application.outbox import IEventOutbox
from core.domain.entity import AggregateRoot

from ...domain.entities import User
from ...domain.errors import RolePermissionDeniedError
from ...domain.repositories import IUserRepository
from ...domain.value_objects import Role
from ...domain.value_objects.ids import UserId
from ..commands import DeactivateUserCommand
from ..dtos import UserDTO


class DeactivateUserHandler(CommandHandler[DeactivateUserCommand, UserDTO]):
    """Soft-remove a member: they stop authenticating, their history stays."""

    def __init__(
        self,
        *,
        unit_of_work: IUnitOfWork,
        user_repository: IUserRepository,
        event_outbox: IEventOutbox | None = None,
    ) -> None:
        super().__init__(unit_of_work=unit_of_work, event_outbox=event_outbox)
        self._users = user_repository

    async def _execute(
        self, request: DeactivateUserCommand
    ) -> tuple[UserDTO, Sequence[AggregateRoot]]:
        actor = await self._users.get_by_id(UserId(request.actor_id))
        user = await self._users.get_by_id(UserId(request.user_id))

        if actor.id == user.id:
            raise RolePermissionDeniedError(
                "A user cannot deactivate themselves",
                context=str(actor.id),
            )
        if not actor.role.at_least(Role.ADMIN):
            raise RolePermissionDeniedError(
                f"Role {actor.role.value} cannot deactivate members",
                context=str(actor.id),
            )

        user.deactivate()
        return UserDTO.from_aggregate(user), [user]

    async def _persist(self, aggregate: AggregateRoot) -> None:
        if isinstance(aggregate, User):
            await self._users.save(aggregate)
        else:  # pragma: no cover - guarded by the aggregates _execute returns
            raise TypeError(f"Unexpected aggregate {type(aggregate).__name__}")