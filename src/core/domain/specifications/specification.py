from __future__ import annotations

from abc import ABC, abstractmethod


class Specification[T](ABC):
    """A predicate over a domain object, composable into larger predicates.

    One tree, two evaluation modes:

    * :meth:`is_satisfied_by` — in-memory evaluation against a candidate.
      The domain layer (services, invariants) and in-memory test fakes use
      this; no storage involved.
    * infrastructure translators walk the same tree and rewrite it into a
      storage query (e.g. a SQLAlchemy where-clause via
      :class:`~socialcrm.core.infrastructure.specifications.SqlAlchemySpecificationTranslator`)
      so repositories can filter at the database instead of loading
      everything and filtering in Python.

    Subclass per bounded context for leaf predicates (e.g. ``ThreadStatusIs``);
    combine leaves with :meth:`and_` / :meth:`or_` / :meth:`not_` — or the
    ``&`` / ``|`` / ``~`` operators. Combinator methods return new
    specification objects; nothing is mutated.
    """

    __slots__ = ()

    @abstractmethod
    def is_satisfied_by(self, candidate: T) -> bool:
        """Whether ``candidate`` satisfies this predicate."""
        ...

    # ---- combinators ----

    def and_(self, other: Specification[T]) -> Specification[T]:
        return AndSpecification(self, other)

    def or_(self, other: Specification[T]) -> Specification[T]:
        return OrSpecification(self, other)

    def not_(self) -> Specification[T]:
        return NotSpecification(self)

    def __and__(self, other: object) -> Specification[T]:
        if not isinstance(other, Specification):
            return NotImplemented
        return self.and_(other)

    def __or__(self, other: object) -> Specification[T]:
        if not isinstance(other, Specification):
            return NotImplemented
        return self.or_(other)

    def __invert__(self) -> Specification[T]:
        return self.not_()


class AndSpecification[T](Specification[T]):
    """Conjunction — satisfied when both sides are (short-circuits)."""

    __slots__ = ("_left", "_right")

    def __init__(self, left: Specification[T], right: Specification[T]) -> None:
        self._left = left
        self._right = right

    @property
    def left(self) -> Specification[T]:
        return self._left

    @property
    def right(self) -> Specification[T]:
        return self._right

    def is_satisfied_by(self, candidate: T) -> bool:
        return self._left.is_satisfied_by(candidate) and self._right.is_satisfied_by(
            candidate
        )

    def __repr__(self) -> str:
        return f"({self._left!r} & {self._right!r})"


class OrSpecification[T](Specification[T]):
    """Disjunction — satisfied when either side is."""

    __slots__ = ("_left", "_right")

    def __init__(self, left: Specification[T], right: Specification[T]) -> None:
        self._left = left
        self._right = right

    @property
    def left(self) -> Specification[T]:
        return self._left

    @property
    def right(self) -> Specification[T]:
        return self._right

    def is_satisfied_by(self, candidate: T) -> bool:
        return self._left.is_satisfied_by(candidate) or self._right.is_satisfied_by(
            candidate
        )

    def __repr__(self) -> str:
        return f"({self._left!r} | {self._right!r})"


class NotSpecification[T](Specification[T]):
    """Negation — satisfied when the inner specification is not."""

    __slots__ = ("_inner",)

    def __init__(self, inner: Specification[T]) -> None:
        self._inner = inner

    @property
    def inner(self) -> Specification[T]:
        return self._inner

    def is_satisfied_by(self, candidate: T) -> bool:
        return not self._inner.is_satisfied_by(candidate)

    def __repr__(self) -> str:
        return f"(~{self._inner!r})"
