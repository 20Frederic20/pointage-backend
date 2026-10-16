from identity.domain import Role


def test_list_users_returns_the_page_contract(identity_api, make_user):
    identity_api.users.items.extend([make_user(1, first_name="Ana", last_name="Dossou"), make_user(2)])
    res = identity_api.client.get("/users", params={"limit": 1})
    assert res.status_code == 200
    body = res.json()
    assert body["total"] == 2
    [user] = body["items"]
    # createdAt / updatedAt are filled by the entity itself: only their presence is checked.
    assert {k: user[k] for k in ("id", "email", "role", "isActive", "firstName", "lastName")} == {
        "id": "usr1",
        "email": "user1@pointage.bj",
        "role": "EMPLOYEE",
        "isActive": True,
        "firstName": "Ana",
        "lastName": "Dossou",
    }
    assert "createdAt" in user and "updatedAt" in user


def test_list_users_filters_by_role(identity_api, make_user):
    identity_api.users.items.extend([make_user(1, role=Role.HR), make_user(2)])
    body = identity_api.client.get("/users", params={"role": "HR"}).json()
    assert [u["id"] for u in body["items"]] == ["usr1"]


def test_list_users_rejects_invalid_paging(identity_api):
    assert identity_api.client.get("/users", params={"limit": 0}).status_code == 422
    assert identity_api.client.get("/users", params={"offset": -1}).status_code == 422
    assert identity_api.client.get("/users", params={"role": "BOSS"}).status_code == 422
