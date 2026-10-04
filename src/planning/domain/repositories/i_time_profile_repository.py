from abc import abstractmethod

from core.domain.repositories import IRepository

from ..entities import TimeProfile
from ..value_objects import TimeProfileId, TimeProfileVersionId


class ITimeProfileRepository(IRepository[TimeProfile, TimeProfileId]):

    @abstractmethod
    async def find_by_version_id(self, time_profile_version_id: TimeProfileVersionId) -> TimeProfile | None:
        """The profile owning a version, with all its versions loaded."""
        ...
