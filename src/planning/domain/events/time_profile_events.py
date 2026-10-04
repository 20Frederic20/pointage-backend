from core.domain.events import BaseEvent

from ..value_objects import TimeProfileId, TimeProfileVersionId


class TimeProfileCreated(BaseEvent[TimeProfileId]):
    """A time profile was created."""

    def __init__(self, time_profile_id: TimeProfileId) -> None:
        super().__init__()
        self._time_profile_id = time_profile_id

    def get_aggregate_id(self) -> TimeProfileId:
        return self._time_profile_id

    def get_event_name(self) -> str:
        return "planning.time_profile.created"


class TimeProfileVersionAdded(BaseEvent[TimeProfileId]):
    """A new version was added to a time profile."""

    def __init__(
        self, time_profile_id: TimeProfileId, *, time_profile_version_id: TimeProfileVersionId
    ) -> None:
        super().__init__()
        self._time_profile_id = time_profile_id
        self._time_profile_version_id = time_profile_version_id

    def get_aggregate_id(self) -> TimeProfileId:
        return self._time_profile_id

    def get_event_name(self) -> str:
        return "planning.time_profile.version_added"

    @property
    def time_profile_version_id(self) -> TimeProfileVersionId:
        return self._time_profile_version_id
