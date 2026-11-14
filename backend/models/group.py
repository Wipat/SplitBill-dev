from __future__ import annotations

from datetime import datetime

from sqlalchemy import Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class Group(Base):
    __tablename__ = "groups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column()
    deleted_at: Mapped[datetime | None] = mapped_column()

    members: Mapped[list[GroupMember]] = relationship(back_populates="group")
    expenses: Mapped[list[Expense]] = relationship(back_populates="group")