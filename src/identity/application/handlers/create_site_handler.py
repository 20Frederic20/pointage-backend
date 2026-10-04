"""Create a site."""

from collections.abc import Sequence

from core.application import CommandHandler, IUnitOfWork
from core.application.outbox import IEventOutbox
from core.domain.entity import AggregateRoot

from ...domain.entities import Site
from ...domain.repositories import ISiteRepository
from ...domain.value_objects.ids import SiteId
from ..commands import CreateSiteCommand
from ..dtos import SiteDTO


class CreateSiteHandler(CommandHandler[CreateSiteCommand, SiteDTO]):
    def __init__(
        self,
        *,
        unit_of_work: IUnitOfWork,
        site_repository: ISiteRepository,
        event_outbox: IEventOutbox | None = None,
    ) -> None:
        super().__init__(unit_of_work=unit_of_work, event_outbox=event_outbox)
        self._sites = site_repository

    async def _execute(self, request: CreateSiteCommand) -> tuple[SiteDTO, Sequence[AggregateRoot]]:
        site = Site.create(SiteId.generate(), name=request.name, address=request.address)
        return SiteDTO.from_aggregate(site), [site]

    async def _persist(self, aggregate: AggregateRoot) -> None:
        if isinstance(aggregate, Site):
            await self._sites.save(aggregate)
        else:  # pragma: no cover - guarded by the aggregates _execute returns
            raise TypeError(f"Unexpected aggregate {type(aggregate).__name__}")
