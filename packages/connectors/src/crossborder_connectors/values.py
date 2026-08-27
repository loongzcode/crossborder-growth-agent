"""Canonical scalar conversion and hashing for imported facts."""

import hashlib
import re
from datetime import UTC, date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def parse_date(value: Any) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    raw = str(value or "").strip()
    for pattern in ("%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d", "%m/%d/%Y"):
        try:
            return datetime.strptime(raw, pattern).date()
        except ValueError:
            continue
    raise ValueError("日期格式无法识别")


def parse_datetime(value: Any, timezone_name: str) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    else:
        raw = str(value or "").strip()
        parsed = None
        try:
            parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            for pattern in ("%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M:%S", "%Y-%m-%d"):
                try:
                    parsed = datetime.strptime(raw, pattern)
                    break
                except ValueError:
                    continue
        if parsed is None:
            raise ValueError("日期时间格式无法识别")
    assert parsed is not None
    if parsed.tzinfo is not None:
        return parsed
    try:
        return parsed.replace(tzinfo=ZoneInfo(timezone_name))
    except ZoneInfoNotFoundError as exc:
        raise ValueError(f"时区无法识别：{timezone_name}") from exc


def parse_decimal(value: Any) -> Decimal:
    if isinstance(value, Decimal):
        return value
    if isinstance(value, int | float):
        return Decimal(str(value))
    raw = re.sub(r"[^0-9.\-]", "", str(value or "").strip())
    if not raw:
        raise ValueError("数值为空")
    try:
        return Decimal(raw)
    except InvalidOperation as exc:
        raise ValueError("数值格式无法识别") from exc


def parse_int(value: Any) -> int:
    parsed = parse_decimal(value)
    if parsed != parsed.to_integral_value():
        raise ValueError("必须为整数")
    return int(parsed)


def parse_rate(value: Any) -> Decimal:
    raw = str(value or "").strip()
    parsed = parse_decimal(value)
    return parsed / 100 if "%" in raw else parsed


def text_value(value: Any, *, default: str = "") -> str:
    return str(value if value is not None else default).strip()


def _canonical_scalar(value: Any) -> str:
    if isinstance(value, datetime):
        return value.astimezone(UTC).isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Decimal):
        normalized = value.normalize()
        return format(normalized, "f")
    return str(value if value is not None else "")


def stable_record_key(values: dict[str, Any], fields: tuple[str, ...] | None = None) -> str:
    selected = fields or tuple(sorted(values))
    payload = "|".join(f"{field}={_canonical_scalar(values.get(field))}" for field in selected)
    return hashlib.sha256(payload.encode()).hexdigest()
