"""A company is a root directory; its sub-directories are its departments."""

from core.domain.errors import ConflictError
from identity.domain import DirectoryId

# A directory tree deeper than this is a cycle in the data, not a real company.
_MAX_DEPTH = 32


class CompanyService:
    def __init__(self, directory_repository) -> None:
        self._directories = directory_repository

    async def root_of(self, directory_id: DirectoryId) -> DirectoryId:
        """The company of a directory: walk ``parent_directory_id`` up to the root."""
        current = directory_id
        for _ in range(_MAX_DEPTH):
            directory = await self._directories.get_by_id(current)
            if directory.parent_directory_id is None:
                return current
            current = directory.parent_directory_id
        raise ConflictError(f"Directory {directory_id.value} has no root (cycle?)", context=directory_id.value)

    async def is_within(self, company_id: DirectoryId, directory_id: DirectoryId) -> bool:
        """``directory_id`` is the company itself or one of its descendants."""
        return await self.root_of(directory_id) == company_id
