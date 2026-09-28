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
