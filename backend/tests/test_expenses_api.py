from models import Expense, ExpenseShare
from sqlalchemy import func, select
from sqlalchemy.orm import Session


def _payload(user_ids):
    return {
        "description": "Dinner",
        "amount": "12.00",
        "paid_by": user_ids[0],
        "split_type": "equal",
        "user_ids": user_ids[:3],
    }


def test_create_expense_and_idempotent_replay(client):
    test_client, group_id, _, users, engine = client
    headers = {"X-User": str(users[0]), "Idempotency-Key": "dinner-once"}
    first = test_client.post(
        f"/groups/{group_id}/expenses", headers=headers, json=_payload(users)
    )
    replay = test_client.post(
        f"/groups/{group_id}/expenses", headers=headers, json=_payload(users)
    )
    assert first.status_code == 201
    assert replay.status_code == 201
    assert replay.json() == first.json()
    with Session(engine) as session:
        assert session.scalar(select(func.count()).select_from(Expense)) == 1
        assert session.scalar(select(func.count()).select_from(ExpenseShare)) == 3


def test_idempotency_key_conflict_for_different_payload(client):
    test_client, group_id, _, users, _ = client
    headers = {"X-User": str(users[0]), "Idempotency-Key": "same-key"}
    assert (
        test_client.post(
            f"/groups/{group_id}/expenses", headers=headers, json=_payload(users)
        ).status_code
        == 201
    )
    changed = {**_payload(users), "description": "Different dinner"}
    response = test_client.post(
        f"/groups/{group_id}/expenses", headers=headers, json=changed
    )
    assert response.status_code == 409


def test_create_rejects_nonmember_share_and_exact_mismatch(client):
    test_client, group_id, _, users, _ = client
    headers = {"X-User": str(users[0]), "Idempotency-Key": "invalid-share"}
    nonmember_payload = {**_payload(users), "user_ids": [users[0], users[3]]}
    assert (
        test_client.post(
            f"/groups/{group_id}/expenses", headers=headers, json=nonmember_payload
        ).status_code
        == 422
    )
    exact_payload = {
        "description": "Mismatch",
        "amount": "10.00",
        "paid_by": users[0],
        "split_type": "exact",
        "shares": [{"user_id": users[0], "amount": "9.99"}],
    }
    headers["Idempotency-Key"] = "exact-mismatch"
    response = test_client.post(
        f"/groups/{group_id}/expenses", headers=headers, json=exact_payload
    )
    assert response.status_code == 422
    assert "shares total" in response.json()["detail"]


def test_list_expenses_reverse_chronological_and_hide_deleted(client):
    test_client, group_id, _, users, _ = client
    expenses = []
    for key, description in (("first", "First"), ("second", "Second")):
        payload = {**_payload(users), "description": description}
        response = test_client.post(
            f"/groups/{group_id}/expenses",
            headers={"X-User": str(users[0]), "Idempotency-Key": key},
            json=payload,
        )
        assert response.status_code == 201
        expenses.append(response.json())
    listing = test_client.get(
        f"/groups/{group_id}/expenses", headers={"X-User": str(users[0])}
    )
    assert [expense["description"] for expense in listing.json()] == ["Second", "First"]
    deleted = test_client.delete(
        f"/groups/{group_id}/expenses/{expenses[0]['id']}",
        headers={"X-User": str(users[0])},
    )
    assert deleted.status_code == 204
    listing = test_client.get(
        f"/groups/{group_id}/expenses", headers={"X-User": str(users[0])}
    )
    assert [expense["description"] for expense in listing.json()] == ["Second"]


def test_only_payer_can_soft_delete(client):
    test_client, group_id, _, users, engine = client
    created = test_client.post(
        f"/groups/{group_id}/expenses",
        headers={"X-User": str(users[0]), "Idempotency-Key": "payer-delete"},
        json=_payload(users),
    )
    expense_id = created.json()["id"]
    forbidden = test_client.delete(
        f"/groups/{group_id}/expenses/{expense_id}", headers={"X-User": str(users[1])}
    )
    assert forbidden.status_code == 403
    with Session(engine) as session:
        expense = session.get(Expense, expense_id)
        assert expense is not None and not expense.is_deleted


def test_missing_idempotency_header_is_rejected(client):
    test_client, group_id, _, users, _ = client
    response = test_client.post(
        f"/groups/{group_id}/expenses",
        headers={"X-User": str(users[0])},
        json=_payload(users),
    )
    assert response.status_code == 422
