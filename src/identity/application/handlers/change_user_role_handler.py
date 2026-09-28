"""Role changes: the actor must outrank the role they grant."""

from collections.abc import Sequence

from core.application import CommandHandler, IUnitOfWork
from core.application.outbox import IEventOutbox
from core.domain.entity import AggregateRoot
from core.domain.errors import NotFoundError

from ...domain.entities import User
from ...domain.repositories import IUserRepository
from ...domain.value_objects.ids import DirectoryId, UserId
from ..commands import ChangeUserRoleCommand
from ..dtos import UserDTO


class ChangeUserRoleHandler(CommandHandler[ChangeUserRoleCommand, UserDTO]):
    """Promote or demote a member of the actor's directory.

    The interface layer's ``require_role`` guard runs first (ADMIN-only
    route); this handler re-checks the domain invariant — an actor cannot
    grant a role they do not strictly outrank — so the rule holds no matter
    who calls.
    """

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
        self, request: ChangeUserRoleCommand
    ) -> tuple[UserDTO, Sequence[AggregateRoot]]:
        actor = await self._users.get_by_id(UserId(request.changed_by))
        user = await self._users.get_by_id(UserId(request.user_id))

        directory_id = DirectoryId(request.directory_id)
        self._require_same_directory(actor, directory_id)
        user = self._require_same_directory(user, directory_id)

        actor.ensure_can_invite(request.role)
        user.change_role(request.role)
        return UserDTO.from_aggregate(user), [user]

    @staticmethod
    def _require_same_directory(user: User, directory_id: DirectoryId) -> User:
        """
        A member of another directory reads as missing — no cross-tenant leak.
        """
        if user.directory_id != directory_id:
            raise NotFoundError(
                f"No user {user.id} in directory {directory_id}",
                context=str(user.id),
            )
        return user

    async def _persist(self, aggregate: AggregateRoot) -> None:
        if isinstance(aggregate, User):
            await self._users.save(aggregate)
        else:  # pragma: no cover - guarded by the aggregates _execute returns
            raise TypeError(f"Unexpected aggregate {type(aggregate).__name__}")
