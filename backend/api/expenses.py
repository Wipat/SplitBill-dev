import hashlib
import json
from decimal import Decimal
from typing import Annotated, Literal

from dependencies.auth import get_current_user_id, require_group_member
from dependencies.database import get_db
from fastapi import APIRouter, Depends, Header, HTTPException, Path, status
from models.expense import Expense
from models.expense_share import ExpenseShare
from models.group import Group
from models.group_member import GroupMember
from pydantic import BaseModel, ConfigDict, Field, model_validator
from services.split import calculate_equal_split, calculate_exact_split
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

router = APIRouter()


class ExactShare(BaseModel):
    user_id: int = Field(gt=0)
    amount: Decimal = Field(ge=0, max_digits=12, decimal_places=2)


class ExpenseCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    description: str = Field(min_length=1)
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    paid_by: int = Field(gt=0)
    split_type: Literal["equal", "exact"]
    user_ids: list[int] | None = Field(default=None, min_length=1)
    shares: list[ExactShare] | None = Field(default=None, min_length=1)

    @model_validator(mode="after")
    def validate_split_fields(self) -> "ExpenseCreate":
        if self.split_type == "equal":
            if self.user_ids is None or self.shares is not None:
                raise ValueError(
                    "Equal split requires user_ids and does not accept shares"
                )
            if any(user_id <= 0 for user_id in self.user_ids):
                raise ValueError("User IDs must be positive integers")
            if len(set(self.user_ids)) != len(self.user_ids):
                raise ValueError("User IDs must be unique")
        else:
            if self.shares is None or self.user_ids is not None:
                raise ValueError(
                    "Exact split requires shares and does not accept user_ids"
                )
            if len({share.user_id for share in self.shares}) != len(self.shares):
                raise ValueError("Share user IDs must be unique")
        return self


class ExpenseShareResponse(BaseModel):
    user_id: int
    share_amount: Decimal


class ExpenseResponse(BaseModel):
    id: int
    group_id: int
    description: str
    amount: Decimal
    paid_by: int
    split_type: str
    shares: list[ExpenseShareResponse]


def _to_response(expense: Expense) -> ExpenseResponse:
    return ExpenseResponse(
        id=expense.id,
        group_id=expense.group_id,
        description=expense.description,
        amount=expense.amount,
        paid_by=expense.paid_by,
        split_type=expense.split_type,
        shares=[
            ExpenseShareResponse(user_id=share.user_id, share_amount=share.share_amount)
            for share in expense.shares
        ],
    )


def _request_fingerprint(payload: ExpenseCreate) -> str:
    canonical = json.dumps(
        payload.model_dump(mode="json"), sort_keys=True, separators=(",", ":")
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _require_group_members(db: Session, group_id: int, user_ids: set[int]) -> None:
    member_ids = set(
        db.scalars(
            select(GroupMember.user_id).where(
                GroupMember.group_id == group_id,
                GroupMember.user_id.in_(user_ids),
            )
        )
    )
    missing = user_ids - member_ids
    if missing:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Users are not members of this group: {sorted(missing)}",
        )


@router.get("/groups/{group_id}/expenses", response_model=list[ExpenseResponse])
def list_group_expenses(
    group: Annotated[Group, Depends(require_group_member)],
    db: Annotated[Session, Depends(get_db)],
) -> list[ExpenseResponse]:
    expenses = db.scalars(
        select(Expense)
        .options(selectinload(Expense.shares))
        .where(Expense.group_id == group.id, Expense.is_deleted.is_(False))
        .order_by(Expense.created_at.desc(), Expense.id.desc())
    ).all()
    return [_to_response(expense) for expense in expenses]


@router.post(
    "/groups/{group_id}/expenses",
    response_model=ExpenseResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_expense(
    payload: ExpenseCreate,
    group: Annotated[Group, Depends(require_group_member)],
    db: Annotated[Session, Depends(get_db)],
    idempotency_key: Annotated[
        str, Header(alias="Idempotency-Key", min_length=1, max_length=255)
    ],
) -> ExpenseResponse:
    key = idempotency_key.strip()
    if not key:
        raise HTTPException(status_code=400, detail="Idempotency-Key cannot be blank")
    fingerprint = _request_fingerprint(payload)
    existing = db.scalar(
        select(Expense)
        .options(selectinload(Expense.shares))
        .where(Expense.group_id == group.id, Expense.idempotency_key == key)
    )
    if existing is not None:
        if existing.idempotency_fingerprint != fingerprint:
            raise HTTPException(
                status_code=409,
                detail="Idempotency-Key was already used with a different request",
            )
        return _to_response(existing)

    try:
        if payload.split_type == "equal":
            shares = calculate_equal_split(payload.amount, payload.user_ids or [])
        else:
            shares = calculate_exact_split(
                payload.amount,
                {share.user_id: share.amount for share in payload.shares or []},
            )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    split_user_ids = set(shares) | {payload.paid_by}
    _require_group_members(db, group.id, split_user_ids)

    expense = Expense(
        group_id=group.id,
        description=payload.description,
        amount=payload.amount,
        paid_by=payload.paid_by,
        split_type=payload.split_type,
        idempotency_key=key,
        idempotency_fingerprint=fingerprint,
        shares=[
            ExpenseShare(user_id=user_id, share_amount=share_amount)
            for user_id, share_amount in shares.items()
        ],
    )
    try:
        db.add(expense)
        db.commit()
        db.refresh(expense)
    except IntegrityError as exc:
        db.rollback()
        existing = db.scalar(
            select(Expense)
            .options(selectinload(Expense.shares))
            .where(Expense.group_id == group.id, Expense.idempotency_key == key)
        )
        if existing is None:
            raise
        if existing.idempotency_fingerprint != fingerprint:
            raise HTTPException(
                status_code=409,
                detail="Idempotency-Key was already used with a different request",
            ) from exc
        return _to_response(existing)
    except Exception:
        db.rollback()
        raise
    return _to_response(expense)


@router.delete(
    "/groups/{group_id}/expenses/{expense_id}", status_code=status.HTTP_204_NO_CONTENT
)
def soft_delete_expense(
    group: Annotated[Group, Depends(require_group_member)],
    user_id: Annotated[int, Depends(get_current_user_id)],
    expense_id: Annotated[int, Path(gt=0)],
    db: Annotated[Session, Depends(get_db)],
) -> None:
    expense = db.scalar(
        select(Expense).where(
            Expense.id == expense_id,
            Expense.group_id == group.id,
            Expense.is_deleted.is_(False),
        )
    )
    if expense is None:
        raise HTTPException(status_code=404, detail="Expense not found")
    if expense.paid_by != user_id:
        raise HTTPException(
            status_code=403, detail="Only the expense payer can delete this expense"
        )
    try:
        expense.is_deleted = True
        db.commit()
    except Exception:
        db.rollback()
        raise
