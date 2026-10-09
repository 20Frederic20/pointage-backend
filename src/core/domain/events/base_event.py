import secrets
import string
import time
from abc import abstractmethod
from datetime import UTC, datetime
from typing import Self

from cqrs.events.event import IEvent

_EVENT_ID_ALPHABET = string.ascii_lowercase + string.digits


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _generate_event_id() -> str:
    random_part = "".join(secrets.choice(_EVENT_ID_ALPHABET) for _ in range(9))
    return f"{int(time.time() * 1000)}-{random_part}"


class BaseEvent[ID](IEvent):
    """Base class for domain events.

    An event is an immutable record of something that happened. Each occurrence
    is unique (``event_id``) — equality is intentionally identity-based, so the
    same logical event raised twice produces two distinct occurrences.

    Implements cqrs' ``IEvent`` (``to_dict``/``from_dict``) so recorded events
    flow through the cqrs mediator unchanged. Deserialization is not supported
    in-process — events are subscribed to by type, never rehydrated.

    Event sourcing: an event carries the data of the change it records
    (``to_payload`` / ``from_payload``), so the event store can replay an
    aggregate from its events alone.
    """

    def __init__(self) -> None:
        self._occurred_at = _utcnow()
        self._event_id = _generate_event_id()

    @property
    def occurred_at(self) -> datetime:
        return self._occurred_at

    @property
    def event_id(self) -> str:
        return self._event_id

    @abstractmethod
    def get_aggregate_id(self) -> ID:
        """Identity of the aggregate this event belongs to."""
        ...

    @abstractmethod
    def get_event_name(self) -> str:
        """Stable event name used for routing / storage / handler lookup."""
        ...

    # ---- cqrs IEvent (serialization contract) ----

    def to_dict(self) -> dict:
        """Identity metadata for routing / storage / auditing."""
        aggregate_id = self.get_aggregate_id()
        to_primitive = getattr(aggregate_id, "to_primitive", None)
        return {
            "event_name": self.get_event_name(),
            "event_id": self.event_id,
            "occurred_at": self.occurred_at.isoformat(),
            "aggregate_id": (
                to_primitive() if callable(to_primitive) else str(aggregate_id)
            ),
        }

    @classmethod
    def from_dict(cls, **kwargs) -> Self:
        raise NotImplementedError(
            "In-process domain events are not deserialized; "
            "subscribe by event type instead."
        )

    # ---- event store (serialization of the event's own data) ----

    def to_payload(self) -> dict:
        """The event's data as JSON-ready primitives, stored in the event store.

        Everything the aggregate's ``_apply`` needs to replay the change must
        be in here — the stored payload is the only source of truth.
        """
        raise NotImplementedError(f"{type(self).__name__} is not stored in the event store")

    @classmethod
    def from_payload(cls, payload: dict) -> Self:
        """Rebuild the event from :meth:`to_payload` output (event store load)."""
        raise NotImplementedError(f"{cls.__name__} is not stored in the event store")

    def restore_identity(self, event_id: str, occurred_at: datetime) -> None:
        """Event store hook: give a loaded event its stored id and timestamp."""
        self._event_id = event_id
        self._occurred_at = occurred_at
