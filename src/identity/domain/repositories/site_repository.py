"""Persistence port for the Site aggregate."""

from abc import abstractmethod

from core.domain.repositories import IRepository

from ..entities import Site
from ..value_objects.ids import DirectoryId, SiteId


class ISiteRepository(IRepository[Site, SiteId]):

    @abstractmethod
    async def find_by_directory(self, directory_id: DirectoryId) -> list[Site]:
        """The directory's sites, principal first."""
        ...

    @abstractmethod
    async def find_principal(self, directory_id: DirectoryId) -> Site | None:
        """The directory's principal site, or ``None`` while it has no site."""
        ...
