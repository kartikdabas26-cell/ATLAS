from __future__ import annotations

from typing import Any

import networkx as nx

from app.graph.builder import build_wheat_graph
from app.models.scenario import ScenarioRequest, ScenarioType


ENGINE_VERSION = "0.7.0"

EUROPEAN_PRODUCERS = (
    "france",
    "germany",
    "poland",
    "romania",
    "spain",
)


def classify_risk(deficit_percent: float) -> str:
    if deficit_percent >= 20:
        return "HIGH"

    if deficit_percent >= 10:
        return "MODERATE"

    return "LOW"


def calculate_price_pressure(
    deficit_percent: float,
) -> float:
    """
    Provisional price-pressure assumption.

    This is a model indicator, not an observed market forecast.
    """

    return round(
        deficit_percent * 0.75,
        2,
    )


def calculate_confidence(
    dependency_weight: float,
) -> float:
    """
    Confidence is a structural model-confidence indicator.

    It does not represent statistical forecast accuracy.
    """

    return round(
        min(
            0.95,
            0.60 + dependency_weight * 0.40,
        ),
        2,
    )


def resolve_shock_sources(
    graph: nx.DiGraph,
    shock_region: str,
    *args: Any,
) -> list[str]:
    """
    Resolve a scenario alias into real producer country nodes.
    """
    normalized = shock_region.strip().lower().replace(" ", "_")
    if normalized == "europe":
        sources = [country for country in EUROPEAN_PRODUCERS if country in graph]
        if not sources:
            raise ValueError("No European producer nodes are available in the current graph.")
        return sources
    if normalized not in graph:
        raise ValueError(f"Unknown shock region: {shock_region}")
    node = graph.nodes[normalized]
    if node.get("node_type", node.get("type")) not in {"region", "country"}:
        raise ValueError("Shock region must refer to a country/region node.")
    return [normalized]


def _coerce_shock_sources(
    graph: nx.DiGraph,
    sources: str | list[str] | tuple[str, ...],
) -> list[str]:
    if isinstance(sources, str):
        return resolve_shock_sources(graph, sources)
    resolved: list[str] = []
    for source in sources:
        resolved.extend(resolve_shock_sources(graph, source))
    return list(dict.fromkeys(resolved))


def _edge_trade_value(edge: dict[str, Any]) -> float | None:
    value = edge.get("trade_value")
    if value is None:
        value = edge.get("trade_value_usd")
    return None if value is None else float(value)


def calculate_import_exposure(graph: nx.DiGraph, target: str) -> float:
    total = 0.0
    for _, _, edge in graph.in_edges(target, data=True):
        if edge.get("relationship") != "SUPPLIES_TO":
            continue
        if edge.get("status") == "derived":
            continue
        trade_value = _edge_trade_value(edge)
        if trade_value is not None:
            total += max(0.0, trade_value)
    return total


def calculate_trade_dependency_weight(
    graph: nx.DiGraph,
    source: str,
    target: str,
) -> float:
    """
    Calculate the source's share of the observed Comtrade
    trade-value exposure for a target importer.

    This avoids inventing a dependency weight.

    Important:
    The current dataset contains a selected set of bilateral
    flows, not every global wheat trade flow. Therefore this
    weight is explicitly provisional.
    """

    edge = graph[source][target]

    trade_value = _edge_trade_value(edge)

    if trade_value is None:
        return 0.0

    total_import_exposure = calculate_import_exposure(
        graph,
        target,
    )

    if total_import_exposure <= 0:
        return 0.0

    return round(
        max(
            0.0,
            float(trade_value),
        )
        / total_import_exposure,
        4,
    )


def calculate_direct_trade_impacts(
    graph: nx.DiGraph,
    shock_sources: str | list[str] | tuple[str, ...],
    shock_percent: float,
    intervention_percent: float,
    target_node: str | None = None,
) -> list[dict[str, Any]]:
    """
    Calculate first-order impacts from one or more shocked
    producing countries to their direct importing countries.

    The calculation uses real UN Comtrade trade values.

    The resulting deficit percentage is a proportional scenario
    indicator, not a forecast of physical food shortage.
    """

    shock_sources = _coerce_shock_sources(graph, shock_sources)
    shock_factor = abs(shock_percent) / 100.0

    # Aggregate multiple producer shocks against the same importer.
    aggregated: dict[str, dict[str, Any]] = {}

    for shock_source in shock_sources:

        for target in graph.successors(shock_source):

            if target_node is not None and target != target_node:
                continue

            edge = graph[shock_source][target]

            if edge.get("relationship") != "SUPPLIES_TO":
                continue

            trade_value = _edge_trade_value(edge)

            if trade_value is None:
                continue

            trade_value = max(
                0.0,
                float(trade_value),
            )

            dependency_weight = (
                calculate_trade_dependency_weight(
                    graph,
                    shock_source,
                    target,
                )
            )

            importer_exposure = calculate_import_exposure(
                graph,
                target,
            )

            shock_trade_loss = (
                trade_value
                * shock_factor
            )

            intervention_offset = min(
                shock_trade_loss,
                trade_value
                * intervention_percent
                / 100.0,
            )

            net_trade_loss = max(
                0.0,
                shock_trade_loss
                - intervention_offset,
            )

            # Relative pressure on the observed import exposure.
            deficit_percent = (
                (
                    net_trade_loss
                    / max(
                        importer_exposure,
                        0.1,
                    )
                )
                * 100.0
            )

            price_pressure = calculate_price_pressure(
                deficit_percent
            )

            if target not in aggregated:
                target_data = graph.nodes[target]

                aggregated[target] = {
                    "node_id": target,
                    "name": target_data.get(
                        "name",
                        target,
                    ),
                    "node_type": target_data.get(
                        "node_type",
                        "unknown",
                    ),
                    "order": 1,
                    "relationship": "SUPPLIES_TO",
                    "dependency_weight": 0.0,
                    "propagation_delay_months": int(
                        edge.get(
                            "propagation_delay_months",
                            0,
                        )
                    ),
                    "baseline_import_exposure": importer_exposure,
                    "exposed_trade_value": 0.0,
                    "shock_trade_loss": 0.0,
                    "intervention_offset": 0.0,
                    "net_trade_loss": 0.0,
                    "deficit_percent": 0.0,
                    "price_pressure_percent": 0.0,
                    "risk": "LOW",
                    "confidence": 0.60,
                    "source_contributions": [],
                }

            result = aggregated[target]

            result["dependency_weight"] += (
                dependency_weight
            )

            result["exposed_trade_value"] += (
                trade_value
            )

            result["shock_trade_loss"] += (
                shock_trade_loss
            )

            result["intervention_offset"] += (
                intervention_offset
            )

            result["net_trade_loss"] += (
                net_trade_loss
            )

            result["source_contributions"].append(
                {
                    "source": shock_source,
                    "source_name": graph.nodes[
                        shock_source
                    ].get(
                        "name",
                        shock_source,
                    ),
                    "trade_value": round(
                        trade_value,
                        3,
                    ),
                    "dependency_weight": (
                        dependency_weight
                    ),
                }
            )

    impacts = []

    for result in aggregated.values():

        importer_exposure = result[
            "baseline_import_exposure"
        ]

        net_trade_loss = result[
            "net_trade_loss"
        ]

        deficit_percent = (
            net_trade_loss
            / max(
                importer_exposure,
                0.1,
            )
        ) * 100.0

        result["dependency_weight"] = round(
            min(
                1.0,
                result["dependency_weight"],
            ),
            4,
        )

        result["exposed_trade_value"] = round(
            result["exposed_trade_value"],
            3,
        )

        result["shock_trade_loss"] = round(
            result["shock_trade_loss"],
            3,
        )

        result["intervention_offset"] = round(
            result["intervention_offset"],
            3,
        )

        result["net_trade_loss"] = round(
            net_trade_loss,
            3,
        )

        result["deficit_percent"] = round(
            deficit_percent,
            2,
        )

        result["price_pressure_percent"] = (
            calculate_price_pressure(
                deficit_percent
            )
        )

        result["risk"] = classify_risk(
            deficit_percent
        )

        result["confidence"] = (
            calculate_confidence(
                result["dependency_weight"]
            )
        )

        # Backward-compatible aliases used by existing
        # frontend/explanation code.
        result["baseline_imports"] = round(
            importer_exposure,
            3,
        )

        result["exposed_supply"] = round(
            result["exposed_trade_value"],
            3,
        )

        result["shock_supply_loss"] = round(
            result["shock_trade_loss"],
            3,
        )

        result["net_supply_loss"] = round(
            result["net_trade_loss"],
            3,
        )

        impacts.append(result)

    return impacts


def find_temporal_paths(
    graph: nx.DiGraph,
    sources: str | list[str] | tuple[str, ...],
    horizon: int,
) -> list[dict[str, Any]]:
    """
    Find downstream pathways from one or more shocked sources.

    Only real trade edges are treated as initial supply propagation.
    Supporting ATLAS market/logistics relationships can then continue
    the cascade.
    """

    sources = _coerce_shock_sources(graph, sources)
    paths = []

    for source in sources:

        for target in graph.nodes:

            if target == source:
                continue

            try:
                simple_paths = nx.all_simple_paths(
                    graph,
                    source=source,
                    target=target,
                    cutoff=4,
                )
            except nx.NetworkXError:
                continue

            for path in simple_paths:

                if len(path) < 2:
                    continue

                first_edge = graph[
                    path[0]
                ][
                    path[1]
                ]

                if first_edge.get(
                    "relationship"
                ) != "SUPPLIES_TO":
                    continue

                relationships = []

                cumulative_delay = 0
                cumulative_weight = 1.0

                for edge_source, edge_target in zip(
                    path,
                    path[1:],
                ):

                    edge = graph[
                        edge_source
                    ][
                        edge_target
                    ]

                    delay = int(
                        edge.get(
                            "propagation_delay_months",
                            0,
                        )
                    )

                    if edge.get(
                        "relationship"
                    ) == "SUPPLIES_TO":

                        weight = calculate_trade_dependency_weight(
                            graph,
                            edge_source,
                            edge_target,
                        )

                    else:

                        weight = float(
                            edge.get(
                                "weight",
                                0.0,
                            )
                        )

                    cumulative_delay += delay

                    # Prevent a zero-weight supporting edge
                    # from destroying the entire pathway.
                    if weight <= 0:
                        weight = 0.01

                    cumulative_weight *= weight

                    relationships.append(
                        {
                            "source": edge_source,
                            "target": edge_target,
                            "relationship": edge.get(
                                "relationship"
                            ),
                            "weight": round(
                                weight,
                                4,
                            ),
                            "order": edge.get(
                                "order",
                                0,
                            ),
                            "propagation_delay_months": delay,
                        }
                    )

                if cumulative_delay > horizon:
                    continue

                cascade_order = max(
                    (
                        relationship.get(
                            "order",
                            0,
                        )
                        for relationship in relationships
                    ),
                    default=0,
                )

                paths.append(
                    {
                        "source": source,
                        "path": path,
                        "path_names": [
                            graph.nodes[node].get(
                                "name",
                                node,
                            )
                            for node in path
                        ],
                        "final_node": path[-1],
                        "final_node_name": graph.nodes[
                            path[-1]
                        ].get(
                            "name",
                            path[-1],
                        ),
                        "final_node_type": graph.nodes[
                            path[-1]
                        ].get(
                            "node_type",
                            "unknown",
                        ),
                        "relationships": relationships,
                        "cumulative_delay_months": (
                            cumulative_delay
                        ),
                        "activation_month": max(
                            1,
                            cumulative_delay,
                        ),
                        "cumulative_weight": round(
                            cumulative_weight,
                            4,
                        ),
                        "cascade_order": cascade_order,
                    }
                )

    return paths


def calculate_path_pressure(
    path: dict[str, Any],
    shock_percent: float,
    intervention_percent: float,
) -> float:
    """
    Convert a pathway's cumulative graph weight into a
    deterministic cascade-pressure indicator.

    This is a modeled indicator, not a forecast.
    """

    shock_factor = (
        abs(shock_percent)
        / 100.0
    )

    intervention_factor = max(
        0.0,
        1.0
        - (
            intervention_percent
            / 100.0
        ),
    )

    pressure = (
        shock_factor
        * path["cumulative_weight"]
        * intervention_factor
        * 100.0
    )

    return round(
        pressure,
        2,
    )


def build_temporal_timeline(
    graph: nx.DiGraph,
    shock_sources: str | list[str] | tuple[str, ...],
    shock_percent: float,
    direct_impacts: list[dict[str, Any]],
    horizon: int,
    intervention_percent: float = 0.0,
    active_scenario: bool = True,
) -> list[dict[str, Any]]:

    shock_sources = _coerce_shock_sources(graph, shock_sources)
    temporal_paths = find_temporal_paths(
        graph=graph,
        sources=shock_sources,
        horizon=horizon,
    )

    timeline = []

    for month in range(
        1,
        horizon + 1,
    ):

        if active_scenario:

            active_paths = [
                path
                for path in temporal_paths
                if path["activation_month"] <= month
            ]

            newly_active_paths = [
                path
                for path in temporal_paths
                if path["activation_month"] == month
            ]

        else:

            active_paths = []
            newly_active_paths = []

        active_nodes = {
            path["final_node"]
            for path in active_paths
        }

        newly_active_nodes = {
            path["final_node"]
            for path in newly_active_paths
        }

        direct_effects = [
            impact
            for impact in direct_impacts
            if (
                active_scenario
                and impact[
                    "propagation_delay_months"
                ] <= month
            )
        ]

        total_direct_loss = round(
            sum(
                impact["net_supply_loss"]
                for impact in direct_effects
            ),
            3,
        )

        average_deficit = round(
            (
                sum(
                    impact["deficit_percent"]
                    for impact in direct_effects
                )
                / len(direct_effects)
            )
            if direct_effects
            else 0.0,
            2,
        )

        average_price_pressure = round(
            (
                sum(
                    impact[
                        "price_pressure_percent"
                    ]
                    for impact in direct_effects
                )
                / len(direct_effects)
            )
            if direct_effects
            else 0.0,
            2,
        )

        cascade_pressures = [
            calculate_path_pressure(
                path=path,
                shock_percent=shock_percent,
                intervention_percent=(
                    intervention_percent
                ),
            )
            for path in active_paths
        ]

        total_cascade_pressure = round(
            sum(cascade_pressures),
            2,
        )

        average_cascade_pressure = round(
            (
                sum(cascade_pressures)
                / len(cascade_pressures)
            )
            if cascade_pressures
            else 0.0,
            2,
        )

        deficit_indicator = (
            average_deficit
            if direct_effects
            else total_cascade_pressure
        )
        price_pressure_indicator = (
            average_price_pressure
            if direct_effects
            else total_cascade_pressure
        )
        risk = classify_risk(deficit_indicator)

        timeline.append(
            {
                "month": month,
                "active_paths": [
                    path["path"]
                    for path in active_paths
                ],
                "newly_activated_paths": [
                    path["path"]
                    for path in newly_active_paths
                ],
                "affected_nodes": sorted(
                    active_nodes
                ),
                "supply_loss": round(
                    total_direct_loss
                    + total_cascade_pressure,
                    3,
                ),
                "deficit_indicator": round(
                    deficit_indicator,
                    2,
                ),
                "price_pressure_indicator": round(
                    price_pressure_indicator,
                    2,
                ),
                "risk": risk,
                "intervention_state": (
                    "active"
                    if intervention_percent > 0
                    else "baseline"
                ),
                "active_path_count": len(
                    active_paths
                ),
                "new_path_count": len(
                    newly_active_paths
                ),
                "active_downstream_nodes": len(
                    active_nodes
                ),
                "newly_active_nodes": len(
                    newly_active_nodes
                ),
                "direct_supply_loss": (
                    total_direct_loss
                ),
                "average_deficit_percent": (
                    average_deficit
                ),
                "average_price_pressure_percent": (
                    average_price_pressure
                ),
                "cascade_pressure_percent": (
                    total_cascade_pressure
                ),
                "average_cascade_pressure_percent": (
                    average_cascade_pressure
                ),
                "newly_activated_paths_details": [
                    {
                        "path": path["path"],
                        "path_names": path[
                            "path_names"
                        ],
                        "activation_month": path[
                            "activation_month"
                        ],
                        "cascade_order": path[
                            "cascade_order"
                        ],
                        "cumulative_weight": path[
                            "cumulative_weight"
                        ],
                        "cascade_pressure_percent": (
                            calculate_path_pressure(
                                path=path,
                                shock_percent=(
                                    shock_percent
                                ),
                                intervention_percent=(
                                    intervention_percent
                                ),
                            )
                        ),
                    }
                    for path in newly_active_paths
                ],
            }
        )

    return timeline


def summarize_cascades(
    cascades: list[dict[str, Any]],
) -> dict[str, Any]:

    if not cascades:
        return {
            "cascade_paths": 0,
            "max_order": 0,
            "affected_downstream_nodes": 0,
            "latest_activation_month": 0,
        }

    downstream_nodes = {
        item["final_node"]
        for item in cascades
    }

    return {
        "cascade_paths": len(cascades),
        "max_order": max(
            item["cascade_order"]
            for item in cascades
        ),
        "affected_downstream_nodes": len(
            downstream_nodes
        ),
        "latest_activation_month": max(
            item["activation_month"]
            for item in cascades
        ),
    }


def summarize_impacts(
    impacts: list[dict[str, Any]],
) -> dict[str, Any]:

    if not impacts:
        return {
            "affected_regions": 0,
            "total_supply_loss": 0.0,
            "average_deficit_percent": 0.0,
            "average_price_pressure_percent": 0.0,
        }

    return {
        "affected_regions": len(
            impacts
        ),
        "total_supply_loss": round(
            sum(
                item["net_supply_loss"]
                for item in impacts
            ),
            3,
        ),
        "average_deficit_percent": round(
            sum(
                item["deficit_percent"]
                for item in impacts
            )
            / len(impacts),
            2,
        ),
        "average_price_pressure_percent": round(
            sum(
                item[
                    "price_pressure_percent"
                ]
                for item in impacts
            )
            / len(impacts),
            2,
        ),
    }


def build_comparison(
    graph: nx.DiGraph,
    shock_sources: str | list[str] | tuple[str, ...],
    shock_percent: float,
    intervention_percent: float,
    horizon: int,
    target_node: str | None = None,
) -> dict[str, Any]:

    shock_sources = _coerce_shock_sources(graph, shock_sources)

    # ============================================================
    # BASELINE
    # ============================================================

    baseline_paths = find_temporal_paths(
        graph=graph,
        sources=shock_sources,
        horizon=horizon,
    )

    baseline_timeline = build_temporal_timeline(
        graph=graph,
        shock_sources=shock_sources,
        shock_percent=0.0,
        direct_impacts=[],
        horizon=horizon,
        intervention_percent=0.0,
        active_scenario=False,
    )

    # ============================================================
    # SHOCK
    # ============================================================

    shock_impacts = (
        calculate_direct_trade_impacts(
            graph=graph,
            shock_sources=shock_sources,
            shock_percent=shock_percent,
            intervention_percent=0.0,
            target_node=target_node,
        )
    )

    shock_paths = find_temporal_paths(
        graph=graph,
        sources=shock_sources,
        horizon=horizon,
    )

    shock_timeline = build_temporal_timeline(
        graph=graph,
        shock_sources=shock_sources,
        shock_percent=shock_percent,
        direct_impacts=shock_impacts,
        horizon=horizon,
        intervention_percent=0.0,
        active_scenario=True,
    )

    # ============================================================
    # INTERVENTION
    # ============================================================

    intervention_impacts = (
        calculate_direct_trade_impacts(
            graph=graph,
            shock_sources=shock_sources,
            shock_percent=shock_percent,
            intervention_percent=intervention_percent,
            target_node=target_node,
        )
    )

    intervention_paths = find_temporal_paths(
        graph=graph,
        sources=shock_sources,
        horizon=horizon,
    )

    intervention_timeline = build_temporal_timeline(
        graph=graph,
        shock_sources=shock_sources,
        shock_percent=shock_percent,
        direct_impacts=intervention_impacts,
        horizon=horizon,
        intervention_percent=intervention_percent,
        active_scenario=True,
    )

    baseline_summary = summarize_impacts([])

    shock_summary = summarize_impacts(
        shock_impacts
    )

    intervention_summary = summarize_impacts(
        intervention_impacts
    )

    baseline_cascade_summary = summarize_cascades(
        baseline_paths
    )

    shock_cascade_summary = summarize_cascades(
        shock_paths
    )

    intervention_cascade_summary = summarize_cascades(
        intervention_paths
    )

    shock_loss = shock_summary[
        "total_supply_loss"
    ]

    intervention_loss = intervention_summary[
        "total_supply_loss"
    ]

    if shock_loss > 0:

        supply_loss_reduction = round(
            (
                (
                    shock_loss
                    - intervention_loss
                )
                / shock_loss
            )
            * 100,
            2,
        )

    else:

        supply_loss_reduction = 0.0

    return {
        "baseline": {
            "summary": baseline_summary,
            "cascades": baseline_paths,
            "cascade_summary": (
                baseline_cascade_summary
            ),
            "timeline": baseline_timeline,
        },
        "shock": {
            "summary": shock_summary,
            "impacts": shock_impacts,
            "cascades": shock_paths,
            "cascade_summary": (
                shock_cascade_summary
            ),
            "timeline": shock_timeline,
        },
        "intervention": {
            "summary": intervention_summary,
            "impacts": intervention_impacts,
            "cascades": intervention_paths,
            "cascade_summary": (
                intervention_cascade_summary
            ),
            "timeline": intervention_timeline,
        },
        "intervention_effect": {
            "supply_loss_reduction_percent": (
                supply_loss_reduction
            ),
        },
    }


def run_simulation(
    scenario: ScenarioRequest,
) -> dict[str, Any]:

    graph = build_wheat_graph()

    shock_region = scenario.normalized_region
    source_region = (
        scenario.supplier_region.strip().lower().replace(" ", "_")
        if scenario.supplier_region
        else shock_region
    )
    shock_percent = scenario.shock_percent
    intervention_percent = (
        scenario.alternate_supply_percent
    )
    horizon = scenario.time_horizon_months

    if scenario.scenario_type in {
        ScenarioType.LOGISTICS_DISRUPTION,
        ScenarioType.CLIMATE_SHOCK,
        ScenarioType.INPUT_SHOCK,
        ScenarioType.ENERGY_SHOCK,
    }:
        layer_name = {
            ScenarioType.LOGISTICS_DISRUPTION: "logistics",
            ScenarioType.CLIMATE_SHOCK: "climate",
            ScenarioType.INPUT_SHOCK: "inputs",
            ScenarioType.ENERGY_SHOCK: "energy",
        }[scenario.scenario_type]
        return {
            "status": "unsupported",
            "scenario": {
                "scenario_type": scenario.scenario_type.value,
                "shock_region": shock_region,
                "time_horizon_months": horizon,
            },
            "reason": (
                f"{layer_name.capitalize()} scenario is unavailable until authoritative "
                f"{layer_name} observations are available. No consequence is fabricated."
            ),
            "provenance": {
                "model_version": ENGINE_VERSION,
                "limitations": [f"No observed {layer_name} dataset is loaded."],
            },
        }

    shock_sources = resolve_shock_sources(graph, source_region)
    target_node = (
        scenario.importer_region.strip().lower().replace(" ", "_")
        if scenario.importer_region
        else None
    )
    if target_node and target_node not in graph:
        raise ValueError(f"Unknown importer region: {target_node}")

    baseline_production = sum(
        float(
            graph.nodes[source].get(
                "production_tonnes",
                graph.nodes[source].get("production", 0.0),
            )
        )
        for source in shock_sources
    )

    shock_factor = (
        abs(shock_percent)
        / 100.0
    )

    production_loss = (
        baseline_production
        * shock_factor
    )

    shocked_production = (
        baseline_production
        - production_loss
    )

    # ============================================================
    # REAL COMTRADE EXPORT EXPOSURE
    # ============================================================

    baseline_trade_value = 0.0

    for source in shock_sources:

        for target in graph.successors(
            source
        ):

            edge = graph[
                source
            ][
                target
            ]

            if edge.get(
                "relationship"
            ) != "SUPPLIES_TO":
                continue

            trade_value = _edge_trade_value(edge)

            if trade_value is None:
                continue

            baseline_trade_value += max(
                0.0,
                float(trade_value),
            )

    export_capacity_loss = (
        baseline_trade_value
        * shock_factor
    )

    shocked_trade_value = (
        baseline_trade_value
        - export_capacity_loss
    )

    intervention_supply = (
        baseline_trade_value
        * intervention_percent
        / 100.0
    )

    effective_trade_value = (
        shocked_trade_value
        + intervention_supply
    )

    comparison = build_comparison(
        graph=graph,
        shock_sources=shock_sources,
        shock_percent=shock_percent,
        intervention_percent=(
            intervention_percent
        ),
        horizon=horizon,
        target_node=target_node,
    )

    source_names = [
        graph.nodes[source].get(
            "name",
            source,
        )
        for source in shock_sources
    ]

    return {
        "model": {
            "name": (
                "ATLAS Wheat Temporal "
                "Cascade MVP"
            ),
            "version": ENGINE_VERSION,
            "status": (
                "provisional_demo_model"
            ),
        },
        "scenario": {
            "shock_region": shock_region,
            "scenario_type": scenario.scenario_type.value,
            "shock_sources": shock_sources,
            "shock_source_names": source_names,
            "shock_percent": shock_percent,
            "time_horizon_months": horizon,
            "alternate_supply_percent": (
                intervention_percent
            ),
            "supplier_region": scenario.supplier_region,
            "importer_region": scenario.importer_region,
        },
        "source": {
            "name": (
                ", ".join(source_names)
            ),
            "baseline_production_tonnes": (
                round(
                    baseline_production,
                    3,
                )
            ),
            "production_loss_tonnes": round(
                production_loss,
                3,
            ),
            "shocked_production_tonnes": round(
                shocked_production,
                3,
            ),
            "baseline_trade_value": round(
                baseline_trade_value,
                3,
            ),
            "trade_value_loss": round(
                export_capacity_loss,
                3,
            ),
            "shocked_trade_value": round(
                shocked_trade_value,
                3,
            ),
            "intervention_supply_value": round(
                intervention_supply,
                3,
            ),
            "effective_trade_value": round(
                effective_trade_value,
                3,
            ),
            # Backward-compatible aliases.
            "baseline_production": round(
                baseline_production,
                3,
            ),
            "production_loss": round(
                production_loss,
                3,
            ),
            "shocked_production": round(
                shocked_production,
                3,
            ),
            "baseline_exports": round(
                baseline_trade_value,
                3,
            ),
            "export_capacity_loss": round(
                export_capacity_loss,
                3,
            ),
            "shocked_exports": round(
                shocked_trade_value,
                3,
            ),
            "intervention_supply": round(
                intervention_supply,
                3,
            ),
            "effective_exports": round(
                effective_trade_value,
                3,
            ),
        },
        "comparison": comparison,
        "assumptions": [
            {
                "id": "real-production-data",
                "description": (
                    "Country wheat production is "
                    "loaded from FAOSTAT 2024."
                ),
                "type": "observed_input",
            },
            {
                "id": "real-trade-data",
                "description": (
                    "Bilateral wheat trade exposure "
                    "is loaded from the currently "
                    "available 2024 UN Comtrade flows."
                ),
                "type": "observed_input",
            },
            {
                "id": "trade-coverage",
                "description": (
                    "The current Comtrade dataset is "
                    "a selected bilateral network for "
                    "the MVP, not a complete global "
                    "wheat trade matrix."
                ),
                "type": "provisional",
            },
            {
                "id": "price-response",
                "description": (
                    "Modeled price pressure is "
                    "0.75 times the calculated "
                    "trade-exposure deficit percentage."
                ),
                "type": "provisional",
            },
            {
                "id": "dependency-weight",
                "description": (
                    "Trade dependency weights are "
                    "calculated from each supplier's "
                    "share of the currently observed "
                    "Comtrade exposure for an importer."
                ),
                "type": "provisional",
            },
            {
                "id": "temporal-propagation",
                "description": (
                    "Cascade pathways activate "
                    "according to cumulative "
                    "propagation-delay metadata "
                    "on graph edges."
                ),
                "type": "provisional",
            },
            {
                "id": "cascade-pressure",
                "description": (
                    "Downstream pathway pressure "
                    "is derived from shock magnitude "
                    "and cumulative graph dependency "
                    "weights."
                ),
                "type": "provisional",
            },
            {
                "id": "intervention",
                "description": (
                    "Alternate supply is modeled "
                    "as a proportional offset to "
                    "the shocked trade exposure."
                ),
                "type": "provisional",
            },
            {
                "id": "baseline",
                "description": (
                    "Baseline represents the "
                    "no-shock reference state. "
                    "Underlying graph pathways "
                    "remain available as potential "
                    "dependencies but are not "
                    "treated as active adverse "
                    "consequences."
                ),
                "type": "provisional",
            },
            {
                "id": "data-status",
                "description": (
                    "Current graph values are "
                    "demonstration inputs and are "
                    "not yet connected to FAO or "
                    "UN Comtrade."
                ),
                "type": "provisional",
            },
            {
                "id": "forecast-status",
                "description": (
                    "ATLAS outputs are deterministic "
                    "scenario-model indicators and "
                    "are not validated real-world "
                    "forecasts."
                ),
                "type": "provisional",
            },
            {
                "id": "data-provenance",
                "description": (
                    "Observed production and trade fields come from the "
                    "local normalized FAOSTAT and UN Comtrade fixture subsets; "
                    "derived dependency weights and scenario impacts are modeled."
                ),
                "type": "provenance",
            },
        ],
        "provenance": {
            "model_version": ENGINE_VERSION,
            "data_sources": [
                "FAOSTAT Crops and livestock products fixture",
                "UN Comtrade HS1001 fixture",
            ],
            "retrieval_status": "local_fixture",
            "reference_year": 2024,
            "limitations": [
                "Fixture coverage is not a complete global historical archive.",
                "Temporal delays and price pressure are provisional model assumptions.",
            ],
        },
    }