from decimal import Decimal
from typing import Annotated

from dependencies.auth import require_group_member
from dependencies.database import get_db
from fastapi import APIRouter, Depends, HTTPException, status
from models.expense import Expense
from models.group import Group
from models.group_member import GroupMember
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

router = APIRouter()
ZERO = Decimal("0.00")


class UserBalance(BaseModel):
    user_id: int
    balance: Decimal


@router.get("/groups/{group_id}/balances", response_model=list[UserBalance])
def get_group_balances(
    group: Annotated[Group, Depends(require_group_member)],
    db: Annotated[Session, Depends(get_db)],
) -> list[UserBalance]:
    balances = {
        user_id: ZERO
        for user_id in db.scalars(
            select(GroupMember.user_id).where(GroupMember.group_id == group.id)
        )
    }
    expenses = db.scalars(
        select(Expense)
        .options(selectinload(Expense.shares))
        .where(Expense.group_id == group.id, Expense.is_deleted.is_(False))
    ).all()

    for expense in expenses:
        share_total = sum((share.share_amount for share in expense.shares), ZERO)
        if share_total != expense.amount:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Expense {expense.id} has shares that do not equal its total",
            )
        balances[expense.paid_by] = balances.get(expense.paid_by, ZERO) + expense.amount
        for share in expense.shares:
            balances[share.user_id] = (
                balances.get(share.user_id, ZERO) - share.share_amount
            )

    if sum(balances.values(), ZERO) != ZERO:
        raise HTTPException(status_code=500, detail="Group balances do not sum to zero")
    return [
        UserBalance(user_id=user_id, balance=balance.quantize(Decimal("0.01")))
        for user_id, balance in sorted(balances.items())
    ]
