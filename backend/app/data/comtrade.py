from __future__ import annotations

from pydantic import BaseModel, Field


class ComtradeTradeRecord(BaseModel):
    year: int = Field(ge=1900, le=2100)
    commodity_code: str = Field(min_length=1)
    commodity: str = Field(min_length=1)

    producer: str = Field(min_length=1)
    importer: str = Field(min_length=1)

    producer_code: int = Field(ge=0)
    importer_code: int = Field(ge=0)

    primary_value: float = Field(ge=0)
    net_weight: float | None = Field(default=None, ge=0)

    is_reported: bool
    is_aggregate: bool

    source: str = "UN Comtrade"
    status: str = "observed"
