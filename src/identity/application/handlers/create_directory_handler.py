"""Renaming the directory."""

from collections.abc import Sequence

from core.application import CommandHandler, IUnitOfWork
from core.application.outbox import IEventOutbox
from core.domain.entity import AggregateRoot
from identity.domain import DirectoryId
from identity.domain.errors.errors import DirectoryAlreadyExistsError

from ...domain.entities import Directory
from ...domain.repositories import IDirectoryRepository
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
        event_outbox: IEventOutbox | None = None,
    ) -> None:
        super().__init__(unit_of_work=unit_of_work, event_outbox=event_outbox)
        self._directories = directory_repository

    async def _execute(
        self, request: CreateDirectoryCommand
    ) -> tuple[DirectoryDTO, Sequence[AggregateRoot]]:
        directory = await self._directories.exists_by_code(request.code)
        if directory:
            raise DirectoryAlreadyExistsError(
                "Une entité portant le même code existe déjà"
            )
        directory = Directory.create(
            directory_id=DirectoryId.generate(),
            code=request.code,
            name=request.name,
            location=request.location
        )
        return DirectoryDTO.from_aggregate(directory), [directory]

    async def _persist(self, aggregate: AggregateRoot) -> None:
        if isinstance(aggregate, Directory):
            await self._directories.save(aggregate)
        else:  # pragma: no cover - guarded by the aggregates _execute returns
            raise TypeError(f"Unexpected aggregate {type(aggregate).__name__}")
