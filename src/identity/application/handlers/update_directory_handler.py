"""Renaming the directory."""

from collections.abc import Sequence

from core.application import CommandHandler, IUnitOfWork
from core.application.outbox import IEventOutbox
from core.domain.entity import AggregateRoot

from ...domain.entities import Directory
from ...domain.repositories import IDirectoryRepository
from ...domain.value_objects.ids import DirectoryId
from ..commands import UpdateDirectoryCommand
from ..dtos import DirectoryDTO


class UpdateDirectoryHandler(
    CommandHandler[UpdateDirectoryCommand, DirectoryDTO]
):
    def __init__(
        self,
        *,
        unit_of_work: IUnitOfWork,
        directory_repository: IDirectoryRepository,
        event_outbox: IEventOutbox | None = None,
    ) -> None:
        super().__init__(unit_of_work=unit_of_work, event_outbox=event_outbox)
        self._directories = directory_repository

    async def _execute(
        self, request: UpdateDirectoryCommand
    ) -> tuple[DirectoryDTO, Sequence[AggregateRoot]]:
        directory = await self._directories.get_by_id(
            DirectoryId(request.directory_id)
        )
        directory.rename(request.name)
        return DirectoryDTO.from_aggregate(directory), [directory]

    async def _persist(self, aggregate: AggregateRoot) -> None:
        if isinstance(aggregate, Directory):
            await self._directories.save(aggregate)
        else:  # pragma: no cover - guarded by the aggregates _execute returns
            raise TypeError(f"Unexpected aggregate {type(aggregate).__name__}")
