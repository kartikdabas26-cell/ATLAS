from enum import Enum

from pydantic import BaseModel, Field, model_validator


class ScenarioType(str, Enum):
    PRODUCTION_SHOCK = "production_shock"
    SUPPLIER_DISRUPTION = "supplier_disruption"
    TRADE_DISRUPTION = "trade_disruption"
    LOGISTICS_DISRUPTION = "logistics_disruption"
    CLIMATE_SHOCK = "climate_shock"
    INPUT_SHOCK = "input_shock"
    ENERGY_SHOCK = "energy_shock"


class ScenarioRequest(BaseModel):
    scenario_type: ScenarioType = ScenarioType.PRODUCTION_SHOCK
    shock_region: str = "europe"

    shock_percent: float = Field(
        default=-20.0,
        ge=-50.0,
        le=-5.0,
    )

    time_horizon_months: int = Field(
        default=6,
        ge=1,
        le=36,
    )

    alternate_supply_percent: float = Field(
        default=10.0,
        ge=0.0,
        le=50.0,
    )
    supplier_region: str | None = None
    importer_region: str | None = None

    @model_validator(mode="after")
    def validate_target_fields(self) -> "ScenarioRequest":
        if self.scenario_type == ScenarioType.SUPPLIER_DISRUPTION:
            if not (self.supplier_region or self.shock_region):
                raise ValueError("supplier_region is required for supplier_disruption")
        if self.scenario_type == ScenarioType.TRADE_DISRUPTION:
            if not (self.supplier_region or self.shock_region):
                raise ValueError("supplier_region is required for trade_disruption")
            if not self.importer_region:
                raise ValueError("importer_region is required for trade_disruption")
        return self

    @property
    def normalized_region(self) -> str:
        return self.shock_region.strip().lower()


class NodeScenarioRequest(ScenarioRequest):
    """Request body for backend node-specific scenario inspection."""

    pass


class ScenarioComparisonRequest(BaseModel):
    scenario_a: ScenarioRequest
    scenario_b: ScenarioRequest


class SavedScenarioRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    scenario: ScenarioRequest