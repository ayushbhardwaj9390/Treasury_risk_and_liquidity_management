from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


class CompanyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    country_code: str = Field(pattern=r"^[A-Z]{2}$")


class ProfileSave(CompanyRequest):
    company_name: str = Field(min_length=1, max_length=160)
    industry: Literal["MANUFACTURING", "ENERGY", "SERVICES", "RETAIL", "FINANCIAL_SERVICES", "OTHER"]
    expected_version: int = Field(ge=0, le=2147483646)


class EntityRegister(CompanyRequest):
    name: str = Field(min_length=1, max_length=160)
    functional_currency: str = Field(pattern=r"^[A-Z]{3}$")
