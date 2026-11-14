from __future__ import annotations

from decimal import Decimal

from sqlalchemy import ForeignKey, Integer, Numeric, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class ExpenseShare(Base):
    __tablename__ = "expense_shares"
    __table_args__ = (UniqueConstraint("expense_id", "user_id", name="uq_expense_shares_expense_user"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    expense_id: Mapped[int] = mapped_column(ForeignKey("expenses.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    share_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    expense: Mapped[Expense] = relationship(back_populates="shares")
    user: Mapped[User] = relationship(back_populates="expense_shares")