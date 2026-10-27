from typing import Protocol


class IPhotoStorage(Protocol):
    """Object storage for assisted-punch selfies."""

    async def put(self, key: str, content: bytes, content_type: str) -> None: ...

    async def get(self, key: str) -> tuple[bytes, str]:
        """Return ``(content, content_type)``; raises ``NotFoundError`` if absent."""
        ...
