from identity.application.handlers import GetDirectoriesHandler
from identity.application.queries import GetDirectoriesQuery


def _page(run, repo, **query):
    return run(GetDirectoriesHandler(directory_repository=repo).handle(GetDirectoriesQuery(**query)))


def test_no_directory_gives_an_empty_page(run, in_memory):
    page = _page(run, in_memory([], "Directory"))
    assert (page.items, page.total) == ((), 0)


def test_pages_with_the_total_of_every_directory(run, in_memory, make_directory):
    repo = in_memory([make_directory(n) for n in range(1, 6)], "Directory")
    page = _page(run, repo, limit=2, offset=2)
    assert page.total == 5
    assert [(d.id, d.name, d.code) for d in page.items] == [("dir3", "Direction 3", "D003"), ("dir4", "Direction 4", "D004")]
