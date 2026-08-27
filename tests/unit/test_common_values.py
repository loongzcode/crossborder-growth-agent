from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from pydantic import ValidationError

from crossborder_domain import Money, TimeRange


def test_money_normalizes_iso_currency() -> None:
    money = Money(amount=Decimal("12.34"), currency="usd")
    assert money.currency == "USD"


def test_time_range_requires_aware_increasing_values() -> None:
    start = datetime.now(UTC)
    valid = TimeRange(start=start, end=start + timedelta(days=1))
    assert valid.end > valid.start

    with pytest.raises(ValidationError):
        TimeRange(start=start, end=start)

    with pytest.raises(ValidationError):
        TimeRange(start=datetime.now(), end=datetime.now() + timedelta(days=1))
