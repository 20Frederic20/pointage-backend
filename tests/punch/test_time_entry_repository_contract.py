"""Every ``ITimeEntryRepository`` must implement the idempotency-key reservation:
a repository that silently inherits a no-op would let a retried punch through twice."""

from punch.domain.repositories import ITimeEntryRepository
from punch.infrastructure.persistence.event_sourced_time_entry_repository import (
    EventSourcedTimeEntryRepository,
)
from punch.infrastructure.persistence.time_entry_repository import TimeEntryRepository


def test_reserve_idempotency_key_is_abstract_and_implemented():
    assert "reserve_idempotency_key" in ITimeEntryRepository.__abstractmethods__
    for implementation in (EventSourcedTimeEntryRepository, TimeEntryRepository):
        assert not implementation.__abstractmethods__, implementation.__name__
