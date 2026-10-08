"""Make a site the principal site of its directory; the previous principal
becomes an annex, in the same transaction."""

from collections.abc import Sequence

from core.application import CommandHandler, IUnitOfWork
from core.application.outbox import IEventOutbox
from core.domain.entity import AggregateRoot

from ...domain.entities import Site
from ...domain.repositories import ISiteRepository
from ...domain.value_objects.ids import SiteId
from ..commands import MakeSitePrincipalCommand
from ..dtos import SiteDTO


class MakeSitePrincipalHandler(CommandHandler[MakeSitePrincipalCommand, SiteDTO]):
    def __init__(
        self,
        *,
        unit_of_work: IUnitOfWork,
        site_repository: ISiteRepository,
        event_outbox: IEventOutbox | None = None,
    ) -> None:
        super().__init__(unit_of_work=unit_of_work, event_outbox=event_outbox)
        self._sites = site_repository

    async def _execute(self, request: MakeSitePrincipalCommand) -> tuple[SiteDTO, Sequence[AggregateRoot]]:
        site = await self._sites.get_by_id(SiteId(request.site_id))
        if site.is_principal():
            return SiteDTO.from_aggregate(site), []
        previous = await self._sites.find_principal(site.directory_id)
        site.make_principal()
        if previous is None:
            return SiteDTO.from_aggregate(site), [site]
        previous.make_annex()
        # Demotion is saved first: the one-principal-per-directory index
        # never sees two principals at once.
        return SiteDTO.from_aggregate(site), [previous, site]

    async def _persist(self, aggregate: AggregateRoot) -> None:
        if isinstance(aggregate, Site):
            await self._sites.save(aggregate)
        else:  # pragma: no cover - guarded by the aggregates _execute returns
            raise TypeError(f"Unexpected aggregate {type(aggregate).__name__}")
