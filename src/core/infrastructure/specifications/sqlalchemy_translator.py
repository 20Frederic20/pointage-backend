from __future__ import annotations

from abc import ABC, abstractmethod

from sqlalchemy import ColumnElement, and_, not_, or_

from core.domain.specifications import (
    AndSpecification,
    NotSpecification,
    OrSpecification,
    Specification,
)


class SqlAlchemySpecificationTranslator(ABC):
    """Rewrites a domain :class:`~socialcrm.core.domain.specifications.Specification`
    tree as a SQLAlchemy where-clause.

    Combinators (``And`` / ``Or`` / ``Not``) are core-generic and translated
    here once, recursively. Leaf specifications are context-specific — each
    bounded context subclasses this translator and maps its own leaves to
    columns in :meth:`translate_leaf`. That subclass is the only place where
    a domain term (e.g. ``ThreadStatusIs``) meets a column (e.g.
    ``ThreadModel.status``): the domain tree stays storage-agnostic, and
    repositories get a ``where`` clause that filters at the database.
    """

    __slots__ = ()

    def translate[T](self, spec: Specification[T]) -> ColumnElement[bool]:
        if isinstance(spec, AndSpecification):
            return and_(self.translate(spec.left), self.translate(spec.right))
        if isinstance(spec, OrSpecification):
            return or_(self.translate(spec.left), self.translate(spec.right))
        if isinstance(spec, NotSpecification):
            return not_(self.translate(spec.inner))
        return self.translate_leaf(spec)

    @abstractmethod
    def translate_leaf[T](self, spec: Specification[T]) -> ColumnElement[bool]:
        """Translate a leaf predicate. Combinators never reach this method."""
        ...
