from collections.abc import Mapping, Sequence
from decimal import Decimal, InvalidOperation
from typing import TypeVar

CENT = Decimal("0.01")
ZERO = Decimal("0.00")
UserId = TypeVar("UserId")


def _as_money(value: Decimal | int | str, *, field: str) -> Decimal:
    if isinstance(value, bool):
        raise TypeError(f"{field} must be a valid monetary amount")
    try:
        amount = value if isinstance(value, Decimal) else Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be a valid monetary amount") from exc

    if not amount.is_finite():
        raise ValueError(f"{field} must be a finite monetary amount")
    if amount < ZERO:
        raise ValueError(f"{field} cannot be negative")
    if amount != amount.quantize(CENT):
        raise ValueError(f"{field} cannot have fractions of a cent")
    return amount.quantize(CENT)


def calculate_equal_split(
    total: Decimal | int | str,
    user_ids: Sequence[UserId],
) -> dict[UserId, Decimal]:
    """Divide a total evenly, assigning remaining cents in input order."""
    amount = _as_money(total, field="total")
    if not user_ids:
        raise ValueError("At least one user is required to split an expense")
    if len(set(user_ids)) != len(user_ids):
        raise ValueError("User IDs must be unique")

    cents = int(amount / CENT)
    base_cents, extra_cents = divmod(cents, len(user_ids))
    return {
        user_id: Decimal(base_cents + (index < extra_cents)).scaleb(-2).quantize(CENT)
        for index, user_id in enumerate(user_ids)
    }


def calculate_exact_split(
    total: Decimal | int | str,
    shares: Mapping[UserId, Decimal | int | str],
) -> dict[UserId, Decimal]:
    """Validate explicitly assigned shares against the expense total."""
    amount = _as_money(total, field="total")
    if not shares:
        raise ValueError("At least one user share is required")

    normalized = {
        user_id: _as_money(share, field=f"share for user {user_id}")
        for user_id, share in shares.items()
    }
    share_total = sum(normalized.values(), ZERO)
    if share_total != amount:
        raise ValueError(
            f"Exact split shares total {share_total:.2f}, but expense total is {amount:.2f}"
        )
    return normalized
