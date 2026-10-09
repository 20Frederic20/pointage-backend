"""Event-store adapter for the Directory aggregate (write side)."""

from core.domain.errors import NotFoundError
from core.infrastructure.event_store import EventStore

from ...domain.entities import Directory
from ...domain.events import DirectoryCreated, DirectoryImported, DirectoryUpdated
from ...domain.repositories import IDirectoryRepository
from ...domain.value_objects.ids import DirectoryId

DIRECTORY_STREAM = "identity.directory"

DIRECTORY_EVENT_TYPES = {
    "users.directory.created": DirectoryCreated,
    "users.directory.updated": DirectoryUpdated,
    "users.directory.imported": DirectoryImported,
}


class EventSourcedDirectoryRepository(IDirectoryRepository):
    """A directory is the replay of its stream.

    The code is checked, not reserved: ``directories.code`` was never unique
    in the database, so existing rows may share one.
    """

    def __init__(self, event_store: EventStore) -> None:
        self._store = event_store

    async def get_by_id(self, directory_id: DirectoryId) -> Directory:
        events = await self._store.load(directory_id.value, DIRECTORY_EVENT_TYPES)
        if not events:
            raise NotFoundError(f"Directory {directory_id} not found", context=directory_id.value)
        return Directory.rehydrate(directory_id, events)

    async def exists(self, directory_id: DirectoryId) -> bool:
        return await self._store.exists(directory_id.value, DIRECTORY_STREAM)

    async def exists_any(self) -> bool:
        return await self._store.any_stream(DIRECTORY_STREAM)

    async def exists_by_code(self, value) -> bool:
        # Candidates: every directory that ever had this code; keep the current ones.
        return any(directory.code == value for directory in await self._candidates({"code": value}))

    async def exists_by_code_or_name(self, value) -> bool:
        candidates = [*await self._candidates({"code": value}), *await self._candidates({"name": value})]
        return any(value in (directory.code, directory.name) for directory in candidates)

    async def _candidates(self, contains: dict) -> list[Directory]:
        ids = await self._store.find_stream_ids(DIRECTORY_STREAM, contains)
        streams = await self._store.load_streams(ids, DIRECTORY_EVENT_TYPES)
        return [Directory.rehydrate(DirectoryId(stream_id), events) for stream_id, events in streams.items()]

    async def save(self, directory: Directory) -> None:
        events = directory.domain_events
        await self._store.append(
            stream_type=DIRECTORY_STREAM,
            stream_id=directory.id.value,
            expected_version=directory.version,
            events=events,
        )
        directory._advance_version(len(events))

    async def delete(self, directory_id: DirectoryId) -> None:
        raise NotImplementedError("Event-sourced directories are never deleted")
