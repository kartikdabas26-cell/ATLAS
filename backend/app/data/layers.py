from __future__ import annotations

from typing import Any


LAYER_COVERAGE: dict[str, dict[str, Any]] = {
    "climate": {
        "status": "unavailable",
        "observations": [],
        "years": [],
        "entity_coverage": [],
        "source": None,
        "supported_fields": ["precipitation", "temperature", "drought_indicator"],
        "methodology": "Interface reserved for authoritative climate observations; no observations are loaded.",
        "limitations": ["No climate observation is used in scenario calculations."],
    },
    "logistics": {
        "status": "provisional",
        "observations": [],
        "years": [],
        "entity_coverage": [],
        "source": "ATLAS provisional structural relationships only",
        "supported_fields": ["ports", "routes", "capacity_proxy", "disruption_status"],
        "methodology": "Only provisional graph logistics relationships are available.",
        "limitations": ["No observed route capacity or port throughput dataset is loaded."],
    },
    "inputs": {
        "status": "unavailable",
        "observations": [],
        "years": [],
        "entity_coverage": [],
        "source": None,
        "supported_fields": ["fertilizer", "agricultural_inputs"],
        "methodology": "Interface reserved for observed fertilizer and input availability data.",
        "limitations": ["No country-specific input coefficient is inferred."],
    },
    "energy": {
        "status": "unavailable",
        "observations": [],
        "years": [],
        "entity_coverage": [],
        "source": None,
        "supported_fields": ["fuel", "electricity", "energy_proxy"],
        "methodology": "Interface reserved for observed agricultural energy data.",
        "limitations": ["No energy coefficient is used in production or logistics calculations."],
    },
}


def get_layer_coverage(layer: str | None = None) -> dict[str, Any]:
    if layer is not None:
        return {layer: LAYER_COVERAGE.get(layer, {
            "status": "unknown",
            "observations": [],
            "limitations": ["No such ATLAS layer exists."],
        })}
    return LAYER_COVERAGE
