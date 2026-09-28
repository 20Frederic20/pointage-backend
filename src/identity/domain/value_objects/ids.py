"""Branded identifiers for the users bounded context."""

from typing import Literal

from core.domain.value_objects import EntityId


class UserId(EntityId[Literal["user"]]):
    """Identity of a directory member."""


class DirectoryId(EntityId[Literal["directory"]]):
    """Identity of a directory (top-level tenant)."""
