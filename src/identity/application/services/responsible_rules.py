"""Who may act on an employee record: responsible roles, capped by their own rank."""

from ...domain.errors import RoleCeilingError, RolePermissionDeniedError
from ...domain.value_objects.role import Role


def ensure_responsible(actor_role: str) -> Role:
    """The actor's role, if it is MANAGER or above; ``RolePermissionDeniedError`` otherwise."""
    try:
        role = Role(actor_role)
    except ValueError:
        role = None
    if role is None or not role.at_least(Role.MANAGER):
        raise RolePermissionDeniedError(f"Role {actor_role} cannot act on employees", context=actor_role)
    return role


def ensure_can_manage(actor_role: Role, target_role: Role) -> None:
    """Nobody acts on a record whose role is above their own."""
    if not actor_role.at_least(target_role):
        raise RoleCeilingError(f"{actor_role} cannot act on a {target_role} record", context=target_role.value)


def ensure_can_grant(actor_role: Role, new_role: Role) -> None:
    """Nobody grants a role above their own."""
    if not actor_role.at_least(new_role):
        raise RoleCeilingError(f"{actor_role} cannot grant {new_role}", context=new_role.value)
