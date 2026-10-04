"""Persistence port for the Site aggregate."""

from core.domain.repositories import IRepository

from ..entities import Site
from ..value_objects.ids import SiteId


class ISiteRepository(IRepository[Site, SiteId]):
    ...
