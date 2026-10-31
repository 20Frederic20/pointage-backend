import asyncio

import pytest

from core.domain.errors import ConflictError, NotFoundError
from identity.application.services.company_service import CompanyService
from identity.domain import DirectoryId
from identity.domain.entities import Directory


class _Directories:
    def __init__(self, *directories):
        self._items = {d.id: d for d in directories}

    async def get_by_id(self, directory_id):
        if directory_id not in self._items:
            raise NotFoundError("missing", context=directory_id.value)
        return self._items[directory_id]


def _directory(n, parent=None):
    return Directory(DirectoryId(f"dir{n}"), name=f"D{n}", code=f"D{n}", parent_directory_id=parent)


def test_root_of_walks_to_root():
    root, child, grandchild, other = _directory(1), _directory(2, DirectoryId("dir1")), _directory(3, DirectoryId("dir2")), _directory(4)
    service = CompanyService(_Directories(root, child, grandchild, other))
    assert asyncio.run(service.root_of(grandchild.id)) == root.id
    assert asyncio.run(service.root_of(root.id)) == root.id
    assert asyncio.run(service.is_within(root.id, grandchild.id))
    assert not asyncio.run(service.is_within(other.id, grandchild.id))


def test_root_of_a_cycle_is_conflict():
    a, b = _directory(1, DirectoryId("dir2")), _directory(2, DirectoryId("dir1"))
    with pytest.raises(ConflictError):
        asyncio.run(CompanyService(_Directories(a, b)).root_of(a.id))
