from collections.abc import Callable
from typing import TypeVar

from cqrs import container as cqrs_container

T = TypeVar("T")


class HandlerContainer(cqrs_container.Container[object]):
    """A minimal cqrs ``Container`` backed by a plain resolver callable.

    Resolves handler *classes* into per-request handler *instances*. Each
    resolution calls the resolver, so handlers are built fresh and bound to the
    current request scope — the architecture-sanctioned manual wiring in place
    of a DI framework (see ``social_crm_ddd_architecture.md``).
    """

    def __init__(self, resolver: Callable[[type[T]], T]) -> None:
        self._resolver = resolver
        self._external: object = None

    @property
    def external_container(self) -> object:
        return self._external

    def attach_external_container(self, container: object) -> None:
        self._external = container

    async def resolve(self, type_: type[T]) -> T:
        return self._resolver(type_)
