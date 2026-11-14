from decimal import Decimal

from models import Expense
from sqlalchemy.orm import Session


def test_balances_are_zero_sum_and_exclude_soft_deleted_expenses(client):
    test_client, group_id, _, users, engine = client
    created = test_client.post(
        f"/groups/{group_id}/expenses",
        headers={"X-User": str(users[0]), "Idempotency-Key": "balance-expense"},
        json={
            "description": "Shared bill",
            "amount": "100.00",
            "paid_by": users[0],
            "split_type": "equal",
            "user_ids": users[:3],
        },
    )
    assert created.status_code == 201
    shares_by_user = {
        share["user_id"]: Decimal(share["share_amount"])
        for share in created.json()["shares"]
    }
    assert [shares_by_user[user_id] for user_id in users[:3]] == [
        Decimal("33.34"),
        Decimal("33.33"),
        Decimal("33.33"),
    ]
    balances_response = test_client.get(
        f"/groups/{group_id}/balances", headers={"X-User": str(users[0])}
    )
    balances = {
        item["user_id"]: Decimal(item["balance"]) for item in balances_response.json()
    }
    assert balances == {
        users[0]: Decimal("66.66"),
        users[1]: Decimal("-33.33"),
        users[2]: Decimal("-33.33"),
    }
    assert sum(balances.values(), Decimal("0.00")) == Decimal("0.00")

    deleted = test_client.delete(
        f"/groups/{group_id}/expenses/{created.json()['id']}",
        headers={"X-User": str(users[0])},
    )
    assert deleted.status_code == 204
    balances_response = test_client.get(
        f"/groups/{group_id}/balances", headers={"X-User": str(users[0])}
    )
    assert all(
        Decimal(item["balance"]) == Decimal("0.00") for item in balances_response.json()
    )
    with Session(engine) as session:
        expense = session.get(Expense, created.json()["id"])
        assert expense is not None and expense.is_deleted
