"""Which site an assignment points at — shared by ``AssignEmployeeHandler``
and ``CreateEmployeeHandler`` (the first assignment of a new employee)."""

from ...domain.entities import Directory, Site
from ...domain.errors import DirectoryHasNoSiteError, SiteInactiveError, SiteNotInDirectoryError
from ...domain.repositories import ISiteRepository
from ...domain.value_objects.ids import SiteId


class AssignmentSiteService:
    def __init__(self, *, site_repository: ISiteRepository) -> None:
        self._sites = site_repository

    async def resolve(self, directory: Directory, site_id: str | None) -> Site:
        """The requested site, or the directory's principal site by default.

        The site must belong to ``directory`` and be active.
        """
        if site_id is None:
            site = await self._sites.find_principal(directory.id)
            if site is None:
                raise DirectoryHasNoSiteError(
                    f"Directory {directory.code!r} has no site yet", context=directory.id.value
                )
        else:
            site = await self._sites.get_by_id(SiteId(site_id))
            if site.directory_id != directory.id:
                raise SiteNotInDirectoryError(
                    f"Site {site.name!r} does not belong to directory {directory.code!r}",
                    context=site.id.value,
                )
        if not site.active:
            raise SiteInactiveError(f"Site {site.name!r} is not active", context=site.id.value)
        return site
