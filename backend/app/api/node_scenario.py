from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.models.scenario import ScenarioRequest
from app.simulation.engine import (
    build_wheat_graph,
    calculate_direct_trade_impacts,
    find_temporal_paths,
    resolve_shock_sources,
)

router = APIRouter(
    prefix="/api/scenario",
    tags=["scenario"],
)


@router.post("/node/{node_id}")
def get_node_scenario_impact(
    node_id: str,
    scenario: ScenarioRequest,
):
    graph = build_wheat_graph()

    if node_id not in graph.nodes:
        raise HTTPException(
            status_code=404,
            detail=f"Graph node '{node_id}' not found.",
        )

    shock_sources = resolve_shock_sources(
        graph,
        scenario.shock_region,
    )

    shock_impacts = calculate_direct_trade_impacts(
        graph=graph,
        shock_sources=shock_sources,
        shock_percent=scenario.shock_percent,
        intervention_percent=0.0,
    )

    intervention_impacts = calculate_direct_trade_impacts(
        graph=graph,
        shock_sources=shock_sources,
        shock_percent=scenario.shock_percent,
        intervention_percent=scenario.alternate_supply_percent,
    )

    shock_impact = next(
        (
            item
            for item in shock_impacts
            if item["node_id"] == node_id
        ),
        None,
    )

    intervention_impact = next(
        (
            item
            for item in intervention_impacts
            if item["node_id"] == node_id
        ),
        None,
    )

    temporal_paths = find_temporal_paths(
        graph=graph,
        sources=shock_sources,
        horizon=scenario.time_horizon_months,
    )

    node_paths = [
        path
        for path in temporal_paths
        if node_id in path["path"]
    ]

    active_paths = [
        path
        for path in node_paths
        if path["activation_month"]
        <= scenario.time_horizon_months
    ]

    if shock_impact is None:
        node_data = graph.nodes[node_id]

        return {
            "node": {
                "id": node_id,
                "name": node_data.get("name", node_id),
                "node_type": node_data.get(
                    "node_type",
                    "unknown",
                ),
            },
            "scenario": {
                "shock_region": scenario.shock_region,
                "shock_percent": scenario.shock_percent,
                "time_horizon_months": (
                    scenario.time_horizon_months
                ),
                "alternate_supply_percent": (
                    scenario.alternate_supply_percent
                ),
                "shock_sources": shock_sources,
            },
            "impact": None,
            "intervention": None,
            "paths": {
                "active_path_count": len(active_paths),
                "paths": active_paths,
            },
            "provenance": {
                "status": "no_direct_trade_impact",
                "model_version": "0.7.0",
                "method": (
                    "Backend deterministic scenario "
                    "simulation using observed bilateral "
                    "trade exposure and graph traversal."
                ),
            },
        }

    impact = dict(shock_impact)

    intervention = (
        dict(intervention_impact)
        if intervention_impact is not None
        else None
    )

    return {
        "node": {
            "id": node_id,
            "name": graph.nodes[node_id].get(
                "name",
                node_id,
            ),
            "node_type": graph.nodes[node_id].get(
                "node_type",
                "unknown",
            ),
        },
        "scenario": {
            "shock_region": scenario.shock_region,
            "shock_percent": scenario.shock_percent,
            "time_horizon_months": (
                scenario.time_horizon_months
            ),
            "alternate_supply_percent": (
                scenario.alternate_supply_percent
            ),
            "shock_sources": shock_sources,
        },
        "impact": impact,
        "intervention": intervention,
        "paths": {
            "active_path_count": len(active_paths),
            "paths": active_paths,
        },
        "provenance": {
            "status": "real_data_provisional_model",
            "model_version": "0.7.0",
            "data_sources": [
                "FAOSTAT 2024",
                "UN Comtrade 2024",
            ],
            "method": (
                "Backend deterministic scenario "
                "simulation using observed bilateral "
                "trade exposure and graph traversal."
            ),
            "forecast_warning": (
                "These are deterministic scenario-model "
                "indicators, not validated real-world "
                "forecasts."
            ),
        },
    }