def test_group_list_only_contains_requesting_users_groups(client):
    test_client, group_id, other_group_id, users, _ = client
    response = test_client.get("/groups", headers={"X-User": str(users[0])})
    assert response.status_code == 200
    assert [group["id"] for group in response.json()] == [group_id]
    other_response = test_client.get("/groups", headers={"X-User": str(users[3])})
    assert [group["id"] for group in other_response.json()] == [other_group_id]


def test_get_group_returns_members_and_rejects_nonmember(client):
    test_client, group_id, _, users, _ = client
    response = test_client.get(f"/groups/{group_id}", headers={"X-User": str(users[0])})
    assert response.status_code == 200
    assert {member["id"] for member in response.json()["members"]} == set(users[:3])
    forbidden = test_client.get(
        f"/groups/{group_id}", headers={"X-User": str(users[3])}
    )
    assert forbidden.status_code == 403
