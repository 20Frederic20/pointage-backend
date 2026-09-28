from dataclasses import asdict, dataclass
from typing import Self

from cqrs.requests.request import IRequest


@dataclass(frozen=True)
class Query(IRequest):
    """Frozen dataclass base for read intents (queries).

    Subclass with ``@dataclass(frozen=True)`` and declare fields (e.g.
    ``GetThreadQuery``). ``to_dict`` / ``from_dict`` satisfy cqrs' ``IRequest``
    serialization contract.
    """

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, **kwargs) -> Self:
        return cls(**kwargs)
