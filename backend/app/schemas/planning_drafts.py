"""Bounds mirror the browser's checked cash-planning inputs."""
from datetime import date
from decimal import Decimal
import json
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

CURRENCIES = {"USD", "GBP", "SGD", "EUR", "INR", "JPY", "CHF", "CAD", "AUD", "CNY", "AED", "HKD"}


class StrictInput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


def checked_date(value):
    if len(value) != 10 or date.fromisoformat(value).isoformat() != value:
        raise ValueError("Use a valid YYYY-MM-DD date.")
    return value


class DraftFlow(StrictInput):
    id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_.\-]{0,79}$")
    entity: str = Field(min_length=1, max_length=120)
    date: str = Field(min_length=10, max_length=10)
    direction: Literal["INFLOW", "OUTFLOW"]
    currency: str
    amount: str = Field(pattern=r"^\d{1,13}(?:\.\d{1,2})?$")
    category: Literal["CRUDE_PURCHASE", "PRODUCT_SALE", "FREIGHT", "OPERATING", "OTHER"]
    probability: str = Field(pattern=r"^\d{1,13}(?:\.\d{1,4})?$")

    _date = field_validator("date")(checked_date)

    @model_validator(mode="after")
    def valid_flow(self):
        if self.currency not in CURRENCIES:
            raise ValueError("Unsupported currency.")
        if not 0 < Decimal(self.amount) <= Decimal("1000000000000"):
            raise ValueError("Amount must be positive and no more than one trillion.")
        if not 0 <= Decimal(self.probability) <= 1 or self.direction == "OUTFLOW" and Decimal(self.probability) != 1:
            raise ValueError("Receipt probability must be 0 to 1; payments must stay at 1.")
        if self.category == "CRUDE_PURCHASE" and self.direction != "OUTFLOW" or self.category == "PRODUCT_SALE" and self.direction != "INFLOW":
            raise ValueError("Purchase and sale categories conflict with direction.")
        return self


class DraftAssumptions(StrictInput):
    start: str = Field(min_length=10, max_length=10)
    weeks: int = Field(ge=1, le=52)
    opening: str = Field(pattern=r"^\d{1,13}(?:\.\d{1,2})?$")
    buffer: str = Field(pattern=r"^\d{1,13}(?:\.\d{1,2})?$")
    rates: dict[str, str] = Field(max_length=12)
    delay: int = Field(ge=0, le=90)
    receipts: float = Field(ge=-100, le=200, allow_inf_nan=False)
    costs: float = Field(ge=-100, le=200, allow_inf_nan=False)
    oil: float = Field(ge=-100, le=200, allow_inf_nan=False)
    fx: float = Field(ge=-100, le=200, allow_inf_nan=False)

    _start = field_validator("start")(checked_date)

    @field_validator("receipts", "costs", "oil", "fx")
    @classmethod
    def tenth_steps(cls, value):
        if abs(round(value * 10) - value * 10) > 1e-9:
            raise ValueError("Use changes in 0.1 percent steps.")
        return value

    @field_validator("rates")
    @classmethod
    def valid_rates(cls, values):
        import re
        for currency, rate in values.items():
            if currency not in CURRENCIES or not re.fullmatch(r"\d{1,13}(?:\.\d{1,6})?", rate) or not 0 < Decimal(rate) <= 1000000:
                raise ValueError("Use supported currencies and positive rates up to one million.")
        if "USD" in values and Decimal(values["USD"]) != 1:
            raise ValueError("USD reporting rate must stay at 1.")
        return values


class PlanningDraftSave(StrictInput):
    flows: list[DraftFlow] = Field(min_length=1, max_length=500)
    assumptions: DraftAssumptions
    expected_version: int = Field(ge=0, le=2147483646)

    @model_validator(mode="after")
    def valid_dataset(self):
        if len({flow.id for flow in self.flows}) != len(self.flows):
            raise ValueError("Cash-flow references must be unique.")
        if any(flow.currency != "USD" and flow.currency not in self.assumptions.rates for flow in self.flows):
            raise ValueError("Provide an assumed USD exchange rate for each non-USD currency.")
        if len(json.dumps(self.model_dump(), ensure_ascii=False).encode("utf-8")) > 524288:
            raise ValueError("Planning draft must be under 512 KB.")
        return self
