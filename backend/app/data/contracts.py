from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class DataStatus(str, Enum):
    OBSERVED = "observed"
    MODELED = "modeled"
    PROVISIONAL = "provisional"


class DataSource(str, Enum):
    FAO = "FAO"
    UN_COMTRADE = "UN Comtrade"
    NOAA = "NOAA"
    ATLAS_DEMO = "ATLAS demo"


class MetricType(str, Enum):
    PRODUCTION = "production"
    IMPORTS = "imports"
    EXPORTS = "exports"


class DatasetMetadata(BaseModel):
    source_organization: str = Field(min_length=1)
    dataset_name: str = Field(min_length=1)
    url: str | None = None
    retrieval_date: str | None = None
    retrieval_status: str = "local_fixture"
    source_version: str | None = None
    query_parameters: dict[str, Any] = Field(default_factory=dict)
    sha256: str | None = None
    reference_year: int | None = Field(default=None, ge=1900, le=2100)
    geographic_coverage: str = "global"
    units: str = "unknown"
    license: str | None = None
    methodology_notes: str | None = None
    limitations: str | None = None


class DataQualityReport(BaseModel):
    source_rows: int = 0
    accepted_rows: int = 0
    rejected_rows: int = 0
    row_count: int = 0
    duplicate_rows: int = 0
    missing_values: list[str] = Field(default_factory=list)
    invalid_country_names: list[str] = Field(default_factory=list)
    invalid_years: list[int] = Field(default_factory=list)
    negative_values: list[str] = Field(default_factory=list)
    zero_values: list[str] = Field(default_factory=list)
    normalized_countries: list[str] = Field(default_factory=list)
    year_min: int | None = None
    year_max: int | None = None
    commodity_coverage: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class TradeRecord(BaseModel):
    """
    Normalized trade/production data record used by ATLAS.

    This contract intentionally keeps source provenance attached
    to every value so the graph can later expose where a value came from.
    """

    region_id: str = Field(min_length=1)
    region_name: str = Field(min_length=1)

    commodity: str = Field(default="wheat", min_length=1)
    metric: MetricType

    value: float
    unit: str = Field(min_length=1)

    reference_year: int = Field(ge=1900, le=2100)

    source: DataSource
    status: DataStatus = DataStatus.OBSERVED

    source_reference: str | None = None

    notes: str | None = None
    partner_region: str | None = None
    flow: str | None = None


class RegionData(BaseModel):
    """
    Normalized regional wheat data.

    A region may contain production, imports and exports
    for the same reference period.
    """

    region_id: str = Field(min_length=1)
    region_name: str = Field(min_length=1)

    reference_year: int = Field(ge=1900, le=2100)

    production: float | None = None
    imports: float | None = None
    exports: float | None = None

    unit: str = "million tonnes"

    source: DataSource
    status: DataStatus = DataStatus.OBSERVED

    source_reference: str | None = None


class DataBundle(BaseModel):
    """
    Collection of normalized data records supplied to ATLAS.
    """

    commodity: str = "wheat"
    reference_year: int = Field(ge=1900, le=2100)

    records: list[TradeRecord] = Field(default_factory=list)

    source_status: DataStatus = DataStatus.OBSERVED

    description: str = (
        "Normalized public-data inputs for the ATLAS wheat "
        "supply and trade model."
    )

    dataset_metadata: DatasetMetadata | None = None
    quality_report: DataQualityReport = Field(default_factory=DataQualityReport)
    source_fields: dict[str, Any] = Field(default_factory=dict)