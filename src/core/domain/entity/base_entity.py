from datetime import UTC, datetime


def _utcnow() -> datetime:
    return datetime.now(UTC)


class Entity[ID]:
    """Base class for domain entities.

    DDD identity rule: two entities with the same ``id`` are the same entity,
    regardless of field values — equality and hashing are defined on ``id``
    only.

    This base is deliberately persistence-agnostic: audit timestamps live here
    because they can drive domain rules, but soft-delete and other storage
    strategies belong in repositories / ORM mixins (see ``SoftDeleteMixin``),
    not in the domain layer.
    """

    __slots__ = ("_created_at", "_id", "_updated_at")

    def __init__(
        self,
        entity_id: ID,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
    ) -> None:
        now = _utcnow()
        self._id = entity_id
        self._created_at = created_at if created_at is not None else now
        self._updated_at = updated_at if updated_at is not None else self._created_at

    @property
    def id(self) -> ID:
        return self._id

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @property
    def updated_at(self) -> datetime:
        return self._updated_at

    def touch(self) -> None:
        """Bump ``updated_at``. Used by callers that mutate the entity in place."""
        self._updated_at = _utcnow()

    def __eq__(self, other: object) -> bool:
        if other is None or type(other) is not type(self):
            return NotImplemented
        return self._id == other._id

    def __hash__(self) -> int:
        return hash(self._id)
