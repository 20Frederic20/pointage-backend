"""Create a site of a directory: principal if it is the directory's first
site, annex otherwise."""

from collections.abc import Sequence

from core.application import CommandHandler, IUnitOfWork
from core.application.outbox import IEventOutbox
from core.domain.entity import AggregateRoot

from ...domain.entities import Site
from ...domain.repositories import IDirectoryRepository, ISiteRepository
from ...domain.value_objects import SiteKind
from ...domain.value_objects.ids import DirectoryId, SiteId
from ..commands import CreateSiteCommand
from ..dtos import SiteDTO


class CreateSiteHandler(CommandHandler[CreateSiteCommand, SiteDTO]):
    def __init__(
        self,
        *,
        unit_of_work: IUnitOfWork,
        site_repository: ISiteRepository,
        directory_repository: IDirectoryRepository,
        event_outbox: IEventOutbox | None = None,
    ) -> None:
        super().__init__(unit_of_work=unit_of_work, event_outbox=event_outbox)
        self._sites = site_repository
        self._directories = directory_repository

    async def _execute(self, request: CreateSiteCommand) -> tuple[SiteDTO, Sequence[AggregateRoot]]:
        directory = await self._directories.get_by_id(DirectoryId(request.directory_id))
        has_principal = await self._sites.find_principal(directory.id) is not None
        site = Site.create(
            SiteId.generate(),
            directory_id=directory.id,
            name=request.name,
            location=request.location,
            kind=SiteKind.ANNEX if has_principal else SiteKind.PRINCIPAL,
            address=request.address,
        )
        return SiteDTO.from_aggregate(site), [site]

    async def _persist(self, aggregate: AggregateRoot) -> None:
        if isinstance(aggregate, Site):
            await self._sites.save(aggregate)
        else:  # pragma: no cover - guarded by the aggregates _execute returns
            raise TypeError(f"Unexpected aggregate {type(aggregate).__name__}")
