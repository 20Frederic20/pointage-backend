from types import SimpleNamespace

from identity.domain import Role
from identity.domain.specifications import UserRoleIs
from identity.infrastructure.persistence.user_repository import UserRepository


class CapturingSession:
    """Records the statements a repository sends; returns empty results."""

    def __init__(self):
        self.statements = []

    async def scalars(self, stmt):
        self.statements.append(stmt)
        return SimpleNamespace(all=lambda: [])

    async def scalar(self, stmt):
        self.statements.append(stmt)
        return 0


def _sql(session):
    return str(session.statements[-1]).upper()


def test_find_without_spec_has_no_where_and_a_stable_order(run):
    session = CapturingSession()
    assert run(UserRepository(session).find(None, limit=10, offset=20)) == []
    sql = _sql(session)
    assert "WHERE" not in sql
    assert "ORDER BY" in sql


def test_find_with_spec_filters_at_the_database(run):
    session = CapturingSession()
    run(UserRepository(session).find(UserRoleIs(Role.ADMIN)))
    assert "WHERE" in _sql(session)


def test_count_without_spec_counts_every_row(run):
    session = CapturingSession()
    assert run(UserRepository(session).count(None)) == 0
    assert "WHERE" not in _sql(session)
