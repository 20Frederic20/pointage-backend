"""The Workspace aggregate — the top-level tenant all data is scoped by."""

from typing import Self

from core.domain.entity import AggregateRoot

from ..events import DirectoryCreated
from ..value_objects.ids import DirectoryId
from ..value_objects.location import Location


class Directory(AggregateRoot[DirectoryId]):
    """One tenant (an agency or company account); every row in the system
    carries its ``directory_id`` (PRD §6.1, §10). Holds the subscription
    code and the seat limit that caps how many members can be invited.
    """

    __slots__ = ("_code", "_location", "_name")

    def __init__(
        self,
        directory_id: DirectoryId,
        *,
        name: str,
        code: str,
        location: Location,
        created_at=None,
        updated_at=None,
        version: int = 0,
    ) -> None:
        super().__init__(
            directory_id, created_at=created_at, updated_at=updated_at,
            version=version
        )
        self._name = name.strip()
        self._code = code
        self._location = location

    @classmethod
    def create(
        cls,
        directory_id: DirectoryId,
        *,
        code: str,
        name: str,
        location: str
    ) -> Self:
        """
        Factory for a brand-new workspace; records: class:`DirectoryCreated`.
        """
        workspace = cls(directory_id, code=code, name=name, location=location)
        workspace.record_event(DirectoryCreated(directory_id))
        return workspace

    def rename(self, name: str) -> None:
        """Set the display name."""
        self._name = name.strip()
        self.touch()

    @property
    def name(self) -> str:
        return self._name

    @property
    def code(self) -> str:
        return self._code

    @property
    def location(self) -> int:
        return self._location
