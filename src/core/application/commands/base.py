from dataclasses import asdict, dataclass
from typing import Self

from cqrs.requests.request import IRequest


@dataclass(frozen=True)
class Command(IRequest):
    """Frozen dataclass base for write intents (commands).

    Subclass with ``@dataclass(frozen=True)`` and declare fields (e.g.
    ``CreateThreadCommand``). ``to_dict`` / ``from_dict`` satisfy cqrs'
    ``IRequest`` serialization contract.
    """

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, **kwargs) -> Self:
        return cls(**kwargs)
