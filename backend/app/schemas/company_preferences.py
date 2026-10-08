from pydantic import BaseModel, ConfigDict, Field, field_validator

COUNTRIES = {"US", "GB", "IN", "DE", "FR", "SG", "AE", "HK", "CN", "JP", "CH", "CA", "AU", "NL", "SA", "BR", "ZA"}
CURRENCIES = {"USD", "GBP", "INR", "EUR", "SGD", "AED", "HKD", "CNY", "JPY", "CHF", "CAD", "AUD"}
REVIEWERS = {"TREASURY_MANAGER", "GROUP_TREASURER", "RISK_MANAGER", "AUDITOR"}


class PreferencesSave(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    countries: list[str] = Field(min_length=1, max_length=17)
    currencies: list[str] = Field(min_length=1, max_length=12)
    minimum_cash_usd: str = Field(pattern=r"^(0|[1-9][0-9]{0,11})(\.[0-9]{1,2})?$")
    reviewer_roles: list[str] = Field(min_length=1, max_length=4)
    expected_version: int = Field(ge=0, le=2147483646)

    @field_validator("countries", "currencies", "reviewer_roles")
    @classmethod
    def supported_unique(cls, values, info):
        allowed = {"countries": COUNTRIES, "currencies": CURRENCIES, "reviewer_roles": REVIEWERS}[info.field_name]
        if len(values) != len(set(values)) or any(value not in allowed for value in values):
            raise ValueError("Choose unique supported values.")
        return values
