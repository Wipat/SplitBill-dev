from __future__ import annotations

from datetime import datetime

from sqlalchemy import Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column()
    deleted_at: Mapped[datetime | None] = mapped_column()

    group_memberships: Mapped[list[GroupMember]] = relationship(back_populates="user")
    paid_expenses: Mapped[list[Expense]] = relationship(back_populates="payer")
    expense_shares: Mapped[list[ExpenseShare]] = relationship(back_populates="user")