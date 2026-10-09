from datetime import datetime

from core.domain.entity import AggregateRoot

from ..events import AbsenceTypeCreated, AbsenceTypeImported
from ..value_objects import AbsenceTypeId


class AbsenceType(AggregateRoot[AbsenceTypeId]):
    """A kind of absence (sick leave, paid leave…) and how it is counted.

    The three flags answer the model's ``estRemuneree`` / ``compteCommeTempsTravail``
    / ``deduitSolde`` questions directly.
    """

    __slots__ = ("_active", "_counts_as_work_time", "_deducts_balance", "_name", "_paid")

    def __init__(
        self,
        absence_type_id: AbsenceTypeId,
        *,
        name: str,
        paid: bool,
        counts_as_work_time: bool,
        deducts_balance: bool,
        active: bool = True,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
        version: int = 0,
    ) -> None:
        super().__init__(absence_type_id, created_at=created_at, updated_at=updated_at, version=version)
        self._name = name
        self._paid = paid
        self._counts_as_work_time = counts_as_work_time
        self._deducts_balance = deducts_balance
        self._active = active

    @classmethod
    def create(
        cls,
        absence_type_id: AbsenceTypeId,
        *,
        name: str,
        paid: bool,
        counts_as_work_time: bool,
        deducts_balance: bool,
    ) -> "AbsenceType":
        absence_type = cls.rehydrate(absence_type_id, [])
        absence_type._raise(
            AbsenceTypeCreated(
                absence_type_id,
                name=name.strip(),
                paid=paid,
                counts_as_work_time=counts_as_work_time,
                deducts_balance=deducts_balance,
            )
        )
        return absence_type

    def _apply(self, event) -> None:
        match event:
            case AbsenceTypeCreated() | AbsenceTypeImported():
                self._name = event.name
                self._paid = event.paid
                self._counts_as_work_time = event.counts_as_work_time
                self._deducts_balance = event.deducts_balance
                if isinstance(event, AbsenceTypeImported):
                    self._active = event.active
                    self._created_at = event.created_at
                else:
                    self._active = True
            case _:
                super()._apply(event)

    @property
    def name(self) -> str:
        return self._name

    @property
    def paid(self) -> bool:
        return self._paid

    @property
    def counts_as_work_time(self) -> bool:
        return self._counts_as_work_time

    @property
    def deducts_balance(self) -> bool:
        return self._deducts_balance

    @property
    def active(self) -> bool:
        return self._active
