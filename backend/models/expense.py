from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, String, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class Expense(Base):
    __tablename__ = "expenses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("groups.id"), nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    paid_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    split_type: Mapped[str] = mapped_column(String, nullable=False)
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    group: Mapped[Group] = relationship(back_populates="expenses")
    payer: Mapped[User] = relationship(back_populates="paid_expenses")
    shares: Mapped[list[ExpenseShare]] = relationship(back_populates="expense")