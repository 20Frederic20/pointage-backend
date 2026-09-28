from enum import StrEnum


class Role(StrEnum):
    """Workspace roles, ordered ADMIN > MANAGER > AGENT (PRD §9.1).

    The hierarchy is encoded in :attr:`rank` so the API layer can enforce
    "at least this role" with one comparison instead of per-endpoint rules.
    """
    EMPLOYEE = "EMPLOYEE"
    MANAGER = "MANAGER"
    HR = "HR"
    PAYROLL = "PAYROLL"
    ADMIN = "ADMIN"

    @property
    def rank(self) -> int:
        """Position in the hierarchy (AGENT = 1, MANAGER = 2, ADMIN = 3)."""
        return _ROLE_RANKS[self]

    def at_least(self, minimum: "Role") -> bool:
        """Whether this role satisfies a ``minimum``-role requirement."""
        return self.rank >= minimum.rank


_ROLE_RANKS: dict[Role, int] = {
    Role.EMPLOYEE: 0,
    Role.MANAGER: 1,
    Role.HR: 2,
    Role.PAYROLL: 3,
    Role.ADMIN: 4,
}
