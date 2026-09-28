from dataclasses import asdict, dataclass
from typing import Self

from cqrs.response import IResponse


@dataclass(frozen=True)
class DTO(IResponse):
    """Frozen dataclass base for application-layer DTOs (query / command results).

    Subclass with ``@dataclass(frozen=True)`` and declare fields (e.g.
    ``ThreadDTO``). ``to_dict`` / ``from_dict`` satisfy cqrs' ``IResponse``
    serialization contract.
    """

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, **kwargs) -> Self:
        return cls(**kwargs)
