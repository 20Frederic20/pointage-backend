def test_list_directories_returns_the_page_contract(identity_api, make_directory):
    identity_api.directories.items.extend([make_directory(1, name="Direction générale"), make_directory(2)])
    res = identity_api.client.get("/directories", params={"limit": 1})
    assert res.status_code == 200
    body = res.json()
    assert body["total"] == 2
    assert body["items"][0]["id"] == "dir1"
    assert body["items"][0]["name"] == "Direction générale"
    assert body["items"][0]["code"] == "D001"
    assert "parentDirectoryId" in body["items"][0]


def test_list_directories_rejects_invalid_paging(identity_api):
    assert identity_api.client.get("/directories", params={"limit": 500}).status_code == 422
    assert identity_api.client.get("/directories", params={"offset": -1}).status_code == 422
