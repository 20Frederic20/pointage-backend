from abc import ABC, abstractmethod
from types import MappingProxyType
from typing import Any

Primitive = str | int | float | bool


def deep_freeze(obj: Any) -> Any:
    """
    Recursively freeze dicts/lists/sets into immutable equivalents.
    Unlike Object.freeze, this returns a NEW frozen structure rather than
    mutating in place — Python has no way to freeze an arbitrary object.

    Freezing is container-level: a custom mutable object nested inside the
    structure is returned as-is.
    """
    if isinstance(obj, dict):
        return MappingProxyType({k: deep_freeze(v) for k, v in obj.items()})
    if isinstance(obj, (list, tuple)):
        return tuple(deep_freeze(v) for v in obj)
    if isinstance(obj, set):
        return frozenset(deep_freeze(v) for v in obj)
    return obj


class ValueObject[T](ABC):
    """Base class for immutable value objects.

    Two VOs are equal when they are the same type and their
    :meth:`get_comparable` values are equal. ``props`` is frozen at
    construction: dicts become ``MappingProxyType``, lists become tuples, sets
    become frozensets, so the stored form is always immutable (note: the
    declared ``props`` type is the *input* type; the stored form is the frozen
    one).
    """

    __slots__ = ("_props",)

    def __init__(self, props: T) -> None:
        self._props: T = deep_freeze(props)

    @property
    def props(self) -> T:
        """The frozen props (dict→MappingProxyType, list→tuple, set→frozenset)."""
        return self._props

    # ---- equality ----

    def equals(self, other: object) -> bool:
        """Structural equality against another VO of the same type."""
        if other is None or not isinstance(other, ValueObject):
            return False
        if type(other) is not type(self):
            return False
        return self.get_comparable() == other.get_comparable()

    def __eq__(self, other: object) -> bool:
        if other is None or type(other) is not type(self):
            return NotImplemented
        return self.equals(other)

    def __hash__(self) -> int:
        comparable = self.get_comparable()
        _ensure_hashable(comparable, type(self))
        return hash((type(self), comparable))

    @abstractmethod
    def get_comparable(self) -> Any:
        """
        The value used for structural equality and hashing.

        Must be hashable (e.g. a primitive or a tuple of primitives) — object
        references are never equal across instances. An unhashable return
        raises ``TypeError`` when the VO is hashed, so violations fail loudly
        instead of silently breaking equality.
        """
        ...

    # ---- persistence ----

    @abstractmethod
    def to_primitive(self) -> str | int | float | bool | dict | None:
        """
        Canonical form for persistence, cache, and event payloads.
        Not used for equality — see get_comparable().
        """
        ...

    # ---- serialization ----

    def __str__(self) -> str:
        import json

        primitive = self.to_primitive()
        return primitive if isinstance(primitive, str) else json.dumps(primitive)

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self.to_primitive()!r})"


def _ensure_hashable(value: Any, cls: type) -> None:
    try:
        hash(value)
    except TypeError as exc:
        raise TypeError(
            f"{cls.__name__}.get_comparable() must return a hashable value "
            f"(e.g. a primitive or tuple of primitives), got {value!r}"
        ) from exc
