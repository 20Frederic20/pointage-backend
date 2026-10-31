import asyncio

import pytest

from core.domain.errors import NotFoundError
from punch.domain import TimeEntryId
from punch.infrastructure.photo_storage import photo_key_for


def test_photo_key_for_jpeg_and_png():
    entry_id = TimeEntryId("te1abc")
    assert photo_key_for(entry_id, "image/jpeg") == "time-entries/te1abc.jpg"
    assert photo_key_for(entry_id, "image/png") == "time-entries/te1abc.png"


def test_in_memory_storage_round_trip(photo_storage):
    asyncio.run(photo_storage.put("k", b"data", "image/png"))
    assert asyncio.run(photo_storage.get("k")) == (b"data", "image/png")


def test_in_memory_storage_missing_key_raises_not_found(photo_storage):
    with pytest.raises(NotFoundError):
        asyncio.run(photo_storage.get("nope"))
