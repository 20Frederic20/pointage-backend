from typing import Protocol

from punch.domain import TimeEntryId

PHOTO_EXTENSIONS = {"image/jpeg": "jpg", "image/png": "png"}
"""Accepted selfie content types and the extension of their object key."""

MAX_PHOTO_BYTES = 5 * 1024 * 1024


def photo_key_for(time_entry_id: TimeEntryId, content_type: str) -> str:
    """Object key of a time entry's selfie; ``KeyError`` for a type not in ``PHOTO_EXTENSIONS``."""
    return f"time-entries/{time_entry_id}.{PHOTO_EXTENSIONS[content_type]}"


class IPhotoStorage(Protocol):
    """Object storage for assisted-punch selfies."""

    async def put(self, key: str, content: bytes, content_type: str) -> None: ...

    async def get(self, key: str) -> tuple[bytes, str]:
        """Return ``(content, content_type)``; raises ``NotFoundError`` if absent."""
        ...
