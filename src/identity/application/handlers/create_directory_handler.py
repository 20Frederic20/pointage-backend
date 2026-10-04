"""Create a directory under a site, optionally inside a parent directory."""

from collections.abc import Sequence

from core.application import CommandHandler, IUnitOfWork
from core.application.outbox import IEventOutbox
from core.domain.entity import AggregateRoot
from core.domain.errors import NotFoundError
from identity.domain import DirectoryId
from identity.domain.errors.errors import DirectoryAlreadyExistsError, SiteInactiveError

from ...domain.entities import Directory
from ...domain.repositories import IDirectoryRepository, ISiteRepository
from ...domain.value_objects.ids import SiteId
from ..commands import CreateDirectoryCommand
from ..dtos import DirectoryDTO


class CreateDirectoryHandler(
    CommandHandler[CreateDirectoryCommand, DirectoryDTO]
):
    def __init__(
        self,
        *,
        unit_of_work: IUnitOfWork,
        directory_repository: IDirectoryRepository,
        site_repository: ISiteRepository,
        event_outbox: IEventOutbox | None = None,
    ) -> None:
        super().__init__(unit_of_work=unit_of_work, event_outbox=event_outbox)
        self._directories = directory_repository
        self._sites = site_repository

    async def _execute(
        self, request: CreateDirectoryCommand
    ) -> tuple[DirectoryDTO, Sequence[AggregateRoot]]:
        if await self._directories.exists_by_code(request.code):
            raise DirectoryAlreadyExistsError(
                f"A directory with code {request.code!r} already exists",
                context=request.code,
            )
        site = await self._sites.get_by_id(SiteId(request.site_id))
        if not site.active:
            raise SiteInactiveError(f"Site {site.name!r} is not active", context=site.id.value)
        parent_directory_id = (
            DirectoryId(request.parent_directory_id) if request.parent_directory_id else None
        )
        if parent_directory_id is not None and not await self._directories.exists(parent_directory_id):
            raise NotFoundError(
                f"Parent directory {parent_directory_id.value} not found",
                context=parent_directory_id.value,
            )
        directory = Directory.create(
            directory_id=DirectoryId.generate(),
            code=request.code,
            name=request.name,
            location=request.location,
            site_id=site.id,
            parent_directory_id=parent_directory_id,
        )
        return DirectoryDTO.from_aggregate(directory), [directory]

    async def _persist(self, aggregate: AggregateRoot) -> None:
        if isinstance(aggregate, Directory):
            await self._directories.save(aggregate)
        else:  # pragma: no cover - guarded by the aggregates _execute returns
            raise TypeError(f"Unexpected aggregate {type(aggregate).__name__}")
