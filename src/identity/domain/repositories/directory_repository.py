"""Persistence port for the Directory aggregate."""

from abc import abstractmethod

from core.domain.repositories import IRepository

from ..entities import Directory
from ..value_objects.ids import DirectoryId


class IDirectoryRepository(IRepository[Directory, DirectoryId]):
    @abstractmethod
    async def exists_any(self) -> bool:
        """Whether at least one Directory exists — the signup gate."""
        ...
