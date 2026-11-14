from decimal import Decimal

import pytest
from services.split import calculate_equal_split, calculate_exact_split


def test_equal_split_assigns_remaining_cents_in_input_order():
    result = calculate_equal_split(Decimal("10.00"), [3, 1, 2])
    assert result == {
        3: Decimal("3.34"),
        1: Decimal("3.33"),
        2: Decimal("3.33"),
    }
    assert sum(result.values(), Decimal("0.00")) == Decimal("10.00")


def test_equal_split_handles_amount_smaller_than_number_of_users():
    assert calculate_equal_split("0.02", ["alice", "bob", "carol"]) == {
        "alice": Decimal("0.01"),
        "bob": Decimal("0.01"),
        "carol": Decimal("0.00"),
    }


def test_equal_split_accepts_empty_amount():
    assert calculate_equal_split("0.00", [1, 2]) == {
        1: Decimal("0.00"),
        2: Decimal("0.00"),
    }


def test_exact_split_returns_normalized_decimal_shares():
    assert calculate_exact_split("10", {1: "4", 2: Decimal("6.00")}) == {
        1: Decimal("4.00"),
        2: Decimal("6.00"),
    }


def test_exact_split_rejects_shares_that_do_not_match_total():
    with pytest.raises(ValueError, match="shares total 99.99"):
        calculate_exact_split(
            Decimal("100.00"),
            {1: Decimal("40.00"), 2: Decimal("30.00"), 3: Decimal("29.99")},
        )


@pytest.mark.parametrize(
    ("operation", "match"),
    [
        (lambda: calculate_equal_split("10.001", [1, 2]), "fractions of a cent"),
        (lambda: calculate_exact_split("10.00", {1: "-0.01"}), "cannot be negative"),
        (lambda: calculate_exact_split("10.00", {1: "NaN"}), "finite monetary amount"),
    ],
)
def test_split_rejects_invalid_amounts(operation, match):
    with pytest.raises(ValueError, match=match):
        operation()


def test_equal_split_rejects_no_users_and_duplicate_user_ids():
    with pytest.raises(ValueError, match="At least one user"):
        calculate_equal_split("1.00", [])
    with pytest.raises(ValueError, match="must be unique"):
        calculate_equal_split("1.00", [1, 1])


def test_exact_split_rejects_no_shares():
    with pytest.raises(ValueError, match="At least one user share"):
        calculate_exact_split("0.00", {})
