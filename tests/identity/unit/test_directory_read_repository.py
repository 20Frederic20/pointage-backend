from types import SimpleNamespace

from identity.infrastructure.persistence.directory_repository import DirectoryRepository


class CapturingSession:
    def __init__(self):
        self.statements = []

    async def scalars(self, stmt):
        self.statements.append(stmt)
        return SimpleNamespace(all=lambda: [])

    async def scalar(self, stmt):
        self.statements.append(stmt)
        return 0


def test_find_orders_by_name_and_pages(run):
    session = CapturingSession()
    assert run(DirectoryRepository(session).find(limit=10, offset=20)) == []
    sql = str(session.statements[-1]).upper()
    assert "ORDER BY" in sql and "LIMIT" in sql and "OFFSET" in sql


def test_count_counts_every_directory(run):
    session = CapturingSession()
    assert run(DirectoryRepository(session).count()) == 0
    assert "COUNT" in str(session.statements[-1]).upper()
