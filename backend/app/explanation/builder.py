from __future__ import annotations


EXPLANATION_ENGINE_VERSION = "0.1.3"


def build_explanation(simulation: dict) -> dict:
    """
    Build a transparent, deterministic explanation from the ATLAS
    simulation output.

    This layer does not generate forecasts independently. It explains
    the deterministic simulation that has already been calculated.
    """

    model = simulation.get("model", {})
    scenario = simulation.get("scenario", {})
    source = simulation.get("source", {})
    comparison = simulation.get("comparison", {})
    assumptions = simulation.get("assumptions", [])

    engine_version = model.get("version", "unknown")

    shock_percent = float(
        scenario.get("shock_percent", 0.0)
    )

    shock_sources = scenario.get("shock_source_names")
    if shock_sources is None:
        shock_sources = scenario.get("shock_sources", [])
    if isinstance(shock_sources, str):
        shock_sources = [shock_sources]

    time_horizon = scenario.get(
        "time_horizon_months",
        0,
    )

    baseline_production = float(
        source.get("baseline_production_tonnes", 0.0)
    )

    shocked_production = float(
        source.get("shocked_production_tonnes", 0.0)
    )

    production_loss = float(
        source.get("production_loss_tonnes", 0.0)
    )

    baseline_trade_value = float(
        source.get("baseline_trade_value", 0.0)
    )

    trade_value_loss = float(
        source.get("trade_value_loss", 0.0)
    )

    intervention_percent = float(
        scenario.get("alternate_supply_percent", 0.0)
    )

    intervention_effect = comparison.get(
        "intervention_effect",
        {},
    )

    supply_loss_reduction = float(
        intervention_effect.get(
            "supply_loss_reduction_percent",
            0.0,
        )
    )

    shock_summary = (
        comparison
        .get("shock", {})
        .get("summary", {})
    )

    affected_regions = int(
        shock_summary.get(
            "affected_regions",
            0,
        )
    )

    total_supply_loss = float(
        shock_summary.get(
            "total_supply_loss",
            0.0,
        )
    )

    steps = [
        {
            "step": 1,
            "title": "Production shock",
            "description": (
                f"A {abs(shock_percent):.1f}% production shock "
                f"is applied to the selected producer group: "
                f"{', '.join(shock_sources)}."
            ),
            "evidence": {
                "baseline_production_tonnes": baseline_production,
                "shocked_production_tonnes": shocked_production,
                "production_loss_tonnes": production_loss,
                "data_source": "FAOSTAT 2024",
            },
        },
        {
            "step": 2,
            "title": "Trade exposure",
            "description": (
                "The model propagates the production shock through "
                "the observed bilateral wheat trade relationships "
                "available in the ATLAS MVP dataset."
            ),
            "evidence": {
                "baseline_trade_value": baseline_trade_value,
                "trade_value_loss": trade_value_loss,
                "data_source": "UN Comtrade 2024",
            },
        },
        {
            "step": 3,
            "title": "Affected import markets",
            "description": (
                f"The current trade network identifies "
                f"{affected_regions} directly affected importing "
                f"regions."
            ),
            "evidence": {
                "affected_regions": affected_regions,
                "modeled_supply_loss": total_supply_loss,
            },
        },
        {
            "step": 4,
            "title": "Intervention scenario",
            "description": (
                f"A {intervention_percent:.1f}% alternate-supply "
                f"intervention is applied to the modeled trade "
                f"exposure."
            ),
            "evidence": {
                "alternate_supply_percent": intervention_percent,
                "modeled_supply_loss_reduction_percent": (
                    supply_loss_reduction
                ),
            },
        },
    ]

    return {
        "enabled": True,
        "summary": (
            f"A {abs(shock_percent):.1f}% production shock across "
            f"{len(shock_sources)} modeled European producer countries "
            f"is propagated through the available 2024 wheat trade "
            f"network over a {time_horizon}-month horizon."
        ),
        "steps": steps,
        "intervention": {
            "enabled": intervention_percent > 0,
            "alternate_supply_percent": intervention_percent,
            "supply_loss_reduction_percent": supply_loss_reduction,
            "summary": (
                f"A {intervention_percent:.1f}% alternate-supply "
                f"intervention produces a modeled "
                f"{supply_loss_reduction:.1f}% reduction in the "
                f"selected supply-loss metric."
            ),
        },
        "traceability": {
            "simulation_engine_version": engine_version,
            "explanation_engine_version": EXPLANATION_ENGINE_VERSION,
            "method": (
                "Deterministic graph traversal, observed bilateral "
                "trade exposure, propagation delays and scenario "
                "comparison."
            ),
            "data_sources": [
                "FAOSTAT 2024 wheat production",
                "UN Comtrade 2024 bilateral wheat trade",
            ],
            "llm_used": False,
        },
        "uncertainty": {
            "level": "provisional",
            "message": (
                "ATLAS currently uses observed public-data inputs "
                "combined with deterministic scenario assumptions. "
                "The current Comtrade network is a selected MVP "
                "subset rather than a complete global wheat trade "
                "matrix. Outputs are modeled scenario indicators, "
                "not validated real-world forecasts."
            ),
        },
        "assumptions": assumptions,
    }