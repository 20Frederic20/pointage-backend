"""Shared fixtures for the punch tests: an in-memory selfie storage."""

import pytest

from core.domain.errors import NotFoundError


class InMemoryPhotoStorage:
    """Test double for ``IPhotoStorage``: a dict key -> (content, content_type)."""

    def __init__(self) -> None:
        self.objects: dict[str, tuple[bytes, str]] = {}

    async def put(self, key: str, content: bytes, content_type: str) -> None:
        self.objects[key] = (content, content_type)

    async def get(self, key: str) -> tuple[bytes, str]:
        try:
            return self.objects[key]
        except KeyError:
            raise NotFoundError(f"Photo {key!r} not found", context=key) from None


@pytest.fixture
def photo_storage() -> InMemoryPhotoStorage:
    return InMemoryPhotoStorage()
