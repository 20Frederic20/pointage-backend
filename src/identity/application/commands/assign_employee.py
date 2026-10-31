from dataclasses import dataclass
from datetime import date

from core.application import Command


@dataclass(frozen=True)
class AssignEmployeeCommand(Command):
    """Assign an employee to one site of a directory from ``start_date``.

    ``site_id`` defaults to the directory's principal site.
    """

    employee_id: str
    directory_id: str
    start_date: date
    end_date: date | None = None
    site_id: str | None = None
    # Who acts (from the access token): responsible roles only, capped by rank.
    actor_user_id: str = ""
    actor_role: str = ""
