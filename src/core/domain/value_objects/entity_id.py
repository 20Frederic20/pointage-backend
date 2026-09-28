from __future__ import annotations

import re
from typing import Annotated, Self

from core.domain.errors import InvalidEntityIdError
from core.domain.providers import IdentityProvider
from core.domain.value_objects.base_vo import ValueObject

type Brand[B: str] = Annotated[str, "entity-id-brand", B]
"""
A raw id string tagged with the id class that owns it.

Python's nominal classes already keep id kinds distinct (``ThreadId("a")``
and ``UserId("a")`` are different types and never equal), which is what the
branded-type trick in structural type systems simulates. ``Brand`` covers
the other half: raw strings *in transit* (DTOs, repository results) can
carry the same tag, e.g. ``def find(id: Brand["ThreadId"]) -> Thread | None``.
The tag is annotation-only — it never appears at runtime.
"""

_ID_PATTERN = re.compile(r"[a-z][a-z0-9]{1,31}")


class EntityId[B: str](ValueObject[Brand[B]]):
    """Base class for branded entity identifiers.

    ``B`` is a phantom brand parameter — see :data: 'Brand`. It is never
    read at runtime; declaring ``class ThreadId(EntityId[Literal["thread"]])``
    ties ``ThreadId`` to the ``Brand["thread"]`` annotation (a plain string
    in the subscript would read as a forward reference, so use
    ``Literal``).

    Ids are 2-32 lowercase letters/digits, letter-first, generated via:
    meth:`IdentityProvider.next` (cuid2 — always valid). Equality is
    identity equality: same concrete id type *and* same value.
    """

    __slots__ = ()

    def __init__(self, value: Brand[B]) -> None:
        type(self)._validate(value)
        super().__init__(value)

    @classmethod
    def generate(cls) -> Self:
        """Build a new id from :meth:`IdentityProvider.next`."""
        return cls(IdentityProvider.next())

    @classmethod
    def _validate(cls, value: object) -> None:
        """Assert the id format. Subclasses may tighten this, never loosen it."""
        if not isinstance(value, str) or not _ID_PATTERN.fullmatch(value):
            raise InvalidEntityIdError(value)

    @property
    def value(self) -> str:
        return self._props

    def to_primitive(self) -> str:
        return self._props

    def get_comparable(self) -> str:
        return self._props
