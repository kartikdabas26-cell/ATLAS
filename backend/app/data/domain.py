from __future__ import annotations

from datetime import date
from enum import Enum

from pydantic import BaseModel, Field


class ObservationStatus(str, Enum):
    OBSERVED = "observed"
    DERIVED = "derived"
    MODELED = "modeled"
    UNAVAILABLE = "unavailable"


class ClimateObservation(BaseModel):
    region_id: str
    observed_on: date
    variable: str
    value: float
    unit: str
    source: str
    status: ObservationStatus = ObservationStatus.OBSERVED


class ClimateIndicator(BaseModel):
    region_id: str
    period: str
    indicator: str
    value: float
    unit: str
    source_observations: list[str] = Field(default_factory=list)
    status: ObservationStatus = ObservationStatus.DERIVED


class ProductionClimateRelationship(BaseModel):
    region_id: str
    commodity: str = "wheat"
    indicator: str
    coefficient: float
    method: str
    confidence_label: str
    status: ObservationStatus = ObservationStatus.MODELED
    limitation: str


class LogisticsObservation(BaseModel):
    node_id: str
    node_type: str
    name: str
    country: str | None = None
    capacity_value: float | None = None
    capacity_unit: str | None = None
    source: str | None = None
    status: ObservationStatus = ObservationStatus.OBSERVED


class InputDependency(BaseModel):
    producer_id: str
    input_id: str
    commodity: str = "wheat"
    coefficient: float | None = None
    unit: str | None = None
    source: str | None = None
    status: ObservationStatus = ObservationStatus.UNAVAILABLE
    limitation: str = "No validated country-specific coefficient is loaded."
