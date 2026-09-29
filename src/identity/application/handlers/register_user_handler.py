"""Bootstrap registration: first signup creates the directory and its ADMIN."""

from collections.abc import Sequence

from core.application import CommandHandler, IUnitOfWork
from core.application.outbox import IEventOutbox
from core.domain.entity import AggregateRoot

from ...domain.entities import Directory, User
from ...domain.errors import (  # noqa
    EmailAlreadyRegisteredError,
    RegistrationClosedError,
)
from ...domain.repositories import IDirectoryRepository, IUserRepository
from ...domain.value_objects.ids import DirectoryId, UserId
from ..commands import RegisterUserCommand
from ..dtos import UserDTO
from ..ports import PasswordHasher


class RegisterUserHandler(
    CommandHandler[RegisterUserCommand, UserDTO]
):
    """The public signup endpoint — open only until the first directory exists.

    Once any directory exists, registration closes (D6): new members join
    through the invite flow instead.
    """

    def __init__(
        self,
        *,
        unit_of_work: IUnitOfWork,
        user_repository: IUserRepository,
        directory_repository: IDirectoryRepository,
        password_hasher: PasswordHasher,
        event_outbox: IEventOutbox | None = None,
    ) -> None:
        super().__init__(unit_of_work=unit_of_work, event_outbox=event_outbox)
        self._users = user_repository
        self._directorys = directory_repository
        self._password_hasher = password_hasher

    async def _execute(
        self, request: RegisterUserCommand
    ) -> tuple[UserDTO, Sequence[AggregateRoot]]:
        if await self._directorys.exists_any():
            raise RegistrationClosedError(
                "Signup is closed — join an existing directory via an invite",
            )

        if await self._users.find_by_email(request.email) is not None:
            raise EmailAlreadyRegisteredError(
                f"Email {request.email.strip().lower()!r} is already registered",
                context=request.email,
            )

        user_id = UserId.generate()
        directory = Directory.create(
            name=(
                request.directory_name
                or f"{request.email.split('@')[0]}'s directory"
            ),
        )
        user = User.register_owner(
            user_id,
            email=request.email,
            password_hash=self._password_hasher.hash(request.password),
            first_name=request.first_name,
            last_name=request.last_name,
        )
        return UserDTO.from_aggregate(user), [directory, user]

    async def _persist(self, aggregate: AggregateRoot) -> None:
        if isinstance(aggregate, Directory):
            await self._directorys.save(aggregate)
        elif isinstance(aggregate, User):
            await self._users.save(aggregate)
        else:  # pragma: no cover - guarded by the aggregates _execute returns
            raise TypeError(f"Unexpected aggregate {type(aggregate).__name__}")
