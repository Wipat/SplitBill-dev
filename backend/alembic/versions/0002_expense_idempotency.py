"""Add an idempotency key and fingerprint to expenses."""

import sqlalchemy as sa
from alembic import op

revision = "0002_expense_idempotency"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("expenses", sa.Column("idempotency_key", sa.String(length=255)))
    op.add_column(
        "expenses", sa.Column("idempotency_fingerprint", sa.String(length=64))
    )
    op.create_unique_constraint(
        "uq_expenses_group_idempotency_key",
        "expenses",
        ["group_id", "idempotency_key"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_expenses_group_idempotency_key", "expenses", type_="unique")
    op.drop_column("expenses", "idempotency_fingerprint")
    op.drop_column("expenses", "idempotency_key")
