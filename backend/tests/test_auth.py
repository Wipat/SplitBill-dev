def test_missing_x_user_is_unauthorized(auth_client):
    client, _, _, _ = auth_client
    response = client.get("/users/me")
    assert response.status_code == 401
    assert response.json()["detail"] == "X-User header is required"


def test_invalid_x_user_is_unauthorized(auth_client):
    client, _, _, _ = auth_client
    for value in ("not-an-id", "0", "-3"):
        response = client.get("/users/me", headers={"X-User": value})
        assert response.status_code == 401


def test_group_member_is_authorized(auth_client):
    client, alice_id, _, group_id = auth_client
    response = client.get(f"/groups/{group_id}", headers={"X-User": str(alice_id)})
    assert response.status_code == 200
    assert response.json() == {"id": group_id, "name": "Alice and Bob"}


def test_non_member_is_forbidden(auth_client):
    client, _, bob_id, group_id = auth_client
    response = client.get(f"/groups/{group_id}", headers={"X-User": str(bob_id)})
    assert response.status_code == 403
    assert response.json()["detail"] == "User is not a member of this group"


def test_missing_group_is_not_found(auth_client):
    client, alice_id, _, _ = auth_client
    response = client.get("/groups/999", headers={"X-User": str(alice_id)})
    assert response.status_code == 404


def test_non_positive_group_id_is_rejected(auth_client):
    client, alice_id, _, _ = auth_client
    response = client.get("/groups/0", headers={"X-User": str(alice_id)})
    assert response.status_code == 422
