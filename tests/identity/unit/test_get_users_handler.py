from identity.application.handlers import GetUsersHandler
from identity.application.queries import GetUsersQuery
from identity.domain import Role


def _page(run, repo, **query):
    return run(GetUsersHandler(user_repository=repo).handle(GetUsersQuery(**query)))


def _users(in_memory, make_user):
    return in_memory(
        [
            make_user(1, role=Role.ADMIN),
            make_user(2),
            make_user(3, is_active=False),
            make_user(4, role=Role.ADMIN, is_active=False),
        ],
        "User",
    )


def test_without_filters_returns_everyone(run, in_memory, make_user):
    page = _page(run, _users(in_memory, make_user))
    assert (page.total, [u.id for u in page.items]) == (4, ["usr1", "usr2", "usr3", "usr4"])


def test_role_filter(run, in_memory, make_user):
    page = _page(run, _users(in_memory, make_user), role=Role.ADMIN)
    assert [u.id for u in page.items] == ["usr1", "usr4"]


def test_status_filter(run, in_memory, make_user):
    page = _page(run, _users(in_memory, make_user), is_active=False)
    assert [u.id for u in page.items] == ["usr3", "usr4"]


def test_role_and_status_filters_combine(run, in_memory, make_user):
    page = _page(run, _users(in_memory, make_user), role=Role.ADMIN, is_active=True)
    assert [u.id for u in page.items] == ["usr1"]


def test_total_counts_every_match_not_just_the_page(run, in_memory, make_user):
    page = _page(run, _users(in_memory, make_user), limit=1, offset=1)
    assert (page.total, [u.id for u in page.items]) == (4, ["usr2"])
