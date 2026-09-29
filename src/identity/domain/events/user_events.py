"""Domain events of the users bounded context."""

from core.domain.events import BaseEvent

from ..value_objects.ids import DirectoryId, UserId
from ..value_objects.role import Role


class DirectoryCreated(BaseEvent[DirectoryId]):
    """A new directory (tenant) was created."""

    def __init__(self, directory_id: DirectoryId) -> None:
        super().__init__()
        self._directory_id = directory_id

    def get_aggregate_id(self) -> DirectoryId:
        return self._directory_id

    def get_event_name(self) -> str:
        return "users.directory.created"


class UserRegistered(BaseEvent[UserId]):
    """A user joined a directory — as the founding owner or via an invite."""

    def __init__(self, user_id: UserId) -> None:
        super().__init__()
        self._user_id = user_id

    def get_aggregate_id(self) -> UserId:
        return self._user_id

    def get_event_name(self) -> str:
        return "users.user.registered"


class UserRoleChanged(BaseEvent[UserId]):
    """A user's role changed inside their directory."""

    def __init__(
        self, user_id: UserId, *, old_role: Role, new_role: Role
    ) -> None:
        super().__init__()
        self._user_id = user_id
        self._old_role = old_role
        self._new_role = new_role

    def get_aggregate_id(self) -> UserId:
        return self._user_id

    def get_event_name(self) -> str:
        return "users.user.role_changed"

    @property
    def old_role(self) -> Role:
        return self._old_role

    @property
    def new_role(self) -> Role:
        return self._new_role


class UserDeactivated(BaseEvent[UserId]):
    """A user was deactivated and can no longer authenticate."""

    def __init__(self, user_id: UserId) -> None:
        super().__init__()
        self._user_id = user_id

    def get_aggregate_id(self) -> UserId:
        return self._user_id

    def get_event_name(self) -> str:
        return "users.user.deactivated"
