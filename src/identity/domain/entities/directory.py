"""The Directory aggregate — an entity / department employees are assigned to."""

from typing import Self

from core.domain.entity import AggregateRoot

from ..events.user_events import DirectoryCreated, DirectoryImported, DirectoryUpdated
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
        directory = cls.rehydrate(directory_id, [])
        directory._raise(
            DirectoryCreated(
                directory_id,
                code=code,
                name=name.strip(),
                parent_directory_id=parent_directory_id,
            )
        )
        return directory

    def update(
        self,
        *,
        code: str | None,
        name: str | None,
    ) -> None:
        """Change the code and/or the name; nothing changed: nothing recorded."""
        self._change(
            code=code if code is not None else self._code,
            name=name if name is not None else self._name,
        )

    def rename(self, name: str) -> None:
        """Set the display name."""
        self._change(code=self._code, name=name.strip())

    def _change(self, *, code: str, name: str) -> None:
        if (code, name) != (self._code, self._name):
            self._raise(DirectoryUpdated(self.id, code=code, name=name))

    def _apply(self, event) -> None:
        match event:
            case DirectoryCreated() | DirectoryImported():
                self._code = event.code
                self._name = event.name
                self._parent_directory_id = event.parent_directory_id
                if isinstance(event, DirectoryImported):
                    self._created_at = event.created_at
            case DirectoryUpdated():
                self._code = event.code
                self._name = event.name
            case _:
                super()._apply(event)

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
