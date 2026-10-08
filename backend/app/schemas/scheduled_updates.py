from pydantic import BaseModel, ConfigDict, Field, model_validator


class ScheduleSave(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    connector_id: int = Field(gt=0)
    interval_minutes: int = Field(ge=5, le=10080)
    stale_after_minutes: int = Field(ge=5, le=20160)
    enabled: bool
    expected_version: int = Field(ge=0)

    @model_validator(mode="after")
    def freshness_window(self):
        if self.stale_after_minutes < self.interval_minutes:
            raise ValueError("The old-data alert window must cover at least one update interval.")
        return self
