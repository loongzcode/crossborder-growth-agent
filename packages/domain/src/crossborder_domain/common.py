"""Reusable domain value objects."""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class StrictDomainModel(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)


class Money(StrictDomainModel):
    amount: Decimal
    currency: str = Field(min_length=3, max_length=3)

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        currency = value.upper()
        if not currency.isalpha():
            raise ValueError("currency 必须为三位字母代码")
        return currency


class TimeRange(StrictDomainModel):
    start: datetime
    end: datetime

    @model_validator(mode="after")
    def validate_range(self) -> "TimeRange":
        if self.start.tzinfo is None or self.end.tzinfo is None:
            raise ValueError("时间范围必须包含时区")
        if self.end <= self.start:
            raise ValueError("end 必须晚于 start")
        return self
