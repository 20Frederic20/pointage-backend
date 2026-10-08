"""The Directory aggregate — an entity / department employees are assigned to."""

from typing import Self

from core.domain.entity import AggregateRoot

from ..events import DirectoryCreated
from ..value_objects.ids import DirectoryId


class Directory(AggregateRoot[DirectoryId]):
    """A directory groups employees. Its places are its sites (one principal,
    any number of annexes): each site carries its own GPS position, the
    directory has none.
    """

    __slots__ = ("_code", "_name", "_parent_directory_id")

    def __init__(
        self,
        directory_id: DirectoryId,
        *,
        name: str,
        code: str,
        parent_directory_id: DirectoryId | None = None,
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
        self._parent_directory_id = parent_directory_id

    @classmethod
    def create(
        cls,
        directory_id: DirectoryId,
        *,
        code: str,
        name: str,
        parent_directory_id: DirectoryId | None = None,
    ) -> Self:
        """
        Factory for a brand-new directory; records: class:`DirectoryCreated`.
        """
        directory = cls(
            directory_id,
            code=code,
            name=name,
            parent_directory_id=parent_directory_id,
        )
        directory.record_event(DirectoryCreated(directory_id))
        return directory

    def update(
        self,
        *,
        code: str | None,
        name: str | None,
    ) -> None:

        if code is not None:
            self._code = code
        if name is not None:
            self._name = name

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
    def parent_directory_id(self) -> DirectoryId | None:
        """The directory this one sits under, if any."""
        return self._parent_directory_id
