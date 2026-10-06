"""Account creation: the first account is the founding ADMIN; afterwards only
an ADMIN can create accounts."""

from collections.abc import Sequence

from core.application import CommandHandler, IUnitOfWork
from core.application.outbox import IEventOutbox
from core.domain.entity import AggregateRoot

from ...domain.entities import User
from ...domain.errors import EmailAlreadyRegisteredError, RegistrationClosedError
from ...domain.repositories import IUserRepository
from ...domain.value_objects.ids import UserId
from ...domain.value_objects.role import Role
from ..commands import RegisterUserCommand
from ..dtos import UserDTO
from ..ports import PasswordHasher


class RegisterUserHandler(
    CommandHandler[RegisterUserCommand, UserDTO]
):

    def __init__(
        self,
        *,
        unit_of_work: IUnitOfWork,
        user_repository: IUserRepository,
        password_hasher: PasswordHasher,
        event_outbox: IEventOutbox | None = None,
    ) -> None:
        super().__init__(unit_of_work=unit_of_work, event_outbox=event_outbox)
        self._users = user_repository
        self._password_hasher = password_hasher

    async def _execute(
        self, request: RegisterUserCommand
    ) -> tuple[UserDTO, Sequence[AggregateRoot]]:

        if await self._users.exists_any():
            if request.requested_by_role != Role.ADMIN:
                raise RegistrationClosedError(
                    "Registration is closed: an administrator must create the account",
                    context=request.email,
                )
            role = Role(request.role) if request.role else Role.EMPLOYEE
        else:
            # Bootstrap: nobody can log in yet, so the very first account is
            # public and always the founding ADMIN, whatever was requested.
            role = Role.ADMIN

        if await self._users.find_by_email(request.email) is not None:
            raise EmailAlreadyRegisteredError(
                f"Email {request.email.strip().lower()!r} is already registered",
                context=request.email,
            )

        user = User.register_owner(
            UserId.generate(),
            email=request.email,
            password_hash=(
                self._password_hasher.hash(request.password)
                if request.password
                else None
            ),
            role=role,
            first_name=request.first_name,
            last_name=request.last_name,
        )
        return UserDTO.from_aggregate(user), [user]

    async def _persist(self, aggregate: AggregateRoot) -> None:
        if isinstance(aggregate, User):
            await self._users.save(aggregate)
        else:  # pragma: no cover - guarded by the aggregates _execute returns
            raise TypeError(f"Unexpected aggregate {type(aggregate).__name__}")
