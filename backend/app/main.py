import os
import time
from typing import Any

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse

from app.auth import AuthenticationError, get_current_user, verify_firebase_id_token
from app.graph.builder import build_wheat_graph
from app.data.dependency import calculate_multi_year_dependencies
from app.data.layers import get_layer_coverage
from app.data.loaders import DATA_ROOT, load_comtrade_trade_csv, load_faostat_production_csv
from app.data.scenario_store import get_saved_scenario, list_saved_scenarios, save_scenario
from app.explanation.builder import build_explanation
from app.models.scenario import (
    NodeScenarioRequest,
    SavedScenarioRequest,
    ScenarioComparisonRequest,
    ScenarioRequest,
)
from app.simulation.engine import (
    calculate_direct_trade_impacts,
    find_temporal_paths,
    resolve_shock_sources,
    run_simulation,
)


app = FastAPI(
    title="ATLAS API",
    description="Global Consequence Simulation Engine",
    version="0.1.0",
)


# ---------------------------------------------------------
# CORS
# ---------------------------------------------------------

def _allowed_origins() -> list[str]:
    origins = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
        "http://localhost:5175",
        "http://127.0.0.1:5175",
        "http://localhost:5176",
        "http://127.0.0.1:5176",
        "http://localhost:5177",
        "http://127.0.0.1:5177",
        "http://localhost:5178",
        "http://127.0.0.1:5178",
    ]

    production_origin = os.environ.get(
        "ATLAS_FRONTEND_ORIGIN",
        "",
    ).strip().rstrip("/")

    if production_origin:
        origins.append(production_origin)

    known_production_origin = (
        "https://atlas-global-consequence-simulation-ten.vercel.app"
    )
    if known_production_origin not in origins:
        origins.append(known_production_origin)

    return origins




# ---------------------------------------------------------
# AUTHENTICATION / RATE LIMITING / SECURITY HEADERS
# ---------------------------------------------------------

_rate_limit: dict[tuple[str, str], list[float]] = {}
_RATE_LIMIT_WINDOW_SECONDS = 60
_RATE_LIMIT_MAX_REQUESTS = 20


def _client_key(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def _rate_limited(request: Request) -> bool:
    protected_rate_limited_paths = {
        "/api/scenario/run",
        "/api/scenario/explain",
        "/api/scenario/compare",
        "/api/scenario/export",
        "/api/scenario/node",
    }

    if (
        request.url.path not in protected_rate_limited_paths
        and not request.url.path.startswith("/api/scenario/node/")
    ):
        return False

    now = time.monotonic()
    key = (_client_key(request), request.url.path)

    recent = [
        item
        for item in _rate_limit.get(key, [])
        if now - item < _RATE_LIMIT_WINDOW_SECONDS
    ]

    if len(recent) >= _RATE_LIMIT_MAX_REQUESTS:
        _rate_limit[key] = recent
        return True

    recent.append(now)
    _rate_limit[key] = recent

    return False


@app.middleware("http")
async def security_middleware(request: Request, call_next):
    # CORS preflight requests must pass through without authentication.
    if request.method != "OPTIONS" and request.url.path.startswith("/api/"):
        authorization = request.headers.get("Authorization", "")
        scheme, _, token = authorization.partition(" ")

        if scheme.lower() != "bearer" or not token.strip():
            return JSONResponse(
                {"detail": "Authentication required."},
                status_code=401,
            )

        try:
            request.state.atlas_user = verify_firebase_id_token(token.strip())
        except AuthenticationError:
            return JSONResponse(
                {"detail": "Authentication required."},
                status_code=401,
            )

        if _rate_limited(request):
            return JSONResponse(
                {"detail": "Rate limit exceeded."},
                status_code=429,
            )

    response = await call_next(request)

    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "same-origin"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; frame-ancestors 'none'"
    )

    return response


app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/auth/me")
def auth_me(request: Request):
    user = get_current_user(request)

    return {
        "authenticated": True,
        "user": {
            "subject": user.subject,
            "email": user.email,
            "name": user.name,
            "picture": user.picture,
        },
    }


@app.get("/")
def root():
    return {
        "name": "ATLAS",
        "description": "Global Consequence Simulation Engine",
        "status": "online",
    }


# ---------------------------------------------------------
# HEALTH
# ---------------------------------------------------------

@app.get("/health")
def health():
    return {
        "status": "healthy",
    }


# ---------------------------------------------------------
# KNOWLEDGE GRAPH
# ---------------------------------------------------------

@app.get("/api/graph")
def get_graph():
    graph = build_wheat_graph()

    nodes = [
        {
            "id": node_id,
            **data,
        }
        for node_id, data in graph.nodes(data=True)
    ]

    edges = [
        {
            "source": source,
            "target": target,
            **data,
        }
        for source, target, data in graph.edges(data=True)
    ]

    return {
        "nodes": nodes,
        "edges": edges,
    }


@app.post("/api/scenario/run")
def run_scenario(
    scenario: ScenarioRequest,
):
    try:
        return run_simulation(
            scenario
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )


def _comparison_snapshot(
    simulation: dict[str, Any],
    phase: str = "shock",
) -> dict[str, Any]:
    comparison = simulation.get("comparison", {})
    result = comparison.get(phase, {})
    summary = result.get("summary", {})
    impacts = result.get("impacts", [])

    return {
        "scenario": simulation.get("scenario", {}),
        "affected_nodes": [
            item.get("node_id")
            for item in impacts
            if item.get("node_id")
        ],
        "supply_loss": summary.get("total_supply_loss", 0.0),
        "average_deficit_percent": summary.get(
            "average_deficit_percent",
            0.0,
        ),
        "average_price_pressure_percent": summary.get(
            "average_price_pressure_percent",
            0.0,
        ),
        "risk": max(
            (item.get("risk", "LOW") for item in impacts),
            key={"LOW": 0, "MODERATE": 1, "HIGH": 2}.get,
            default="LOW",
        ),
        "active_pathways": result.get(
            "cascade_summary",
            {},
        ).get(
            "cascade_paths",
            0,
        ),
        "intervention_effect": comparison.get(
            "intervention_effect",
            {},
        ),
        "provenance": simulation.get(
            "provenance",
            {},
        ),
    }


@app.post("/api/scenario/compare")
def compare_scenarios(request: ScenarioComparisonRequest):
    try:
        first = run_simulation(request.scenario_a)
        second = run_simulation(request.scenario_b)
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    return {
        "baseline": _comparison_snapshot(
            first,
            phase="baseline",
        ),
        "scenario_a": _comparison_snapshot(
            first,
        ),
        "scenario_b": _comparison_snapshot(
            second,
        ),
        "results": {
            "scenario_a": first,
            "scenario_b": second,
        },
    }


@app.post("/api/scenarios")
def create_saved_scenario(
    request: SavedScenarioRequest,
    http_request: Request,
):
    user = get_current_user(http_request)

    try:
        return save_scenario(
            request.name,
            request.scenario.model_dump(mode="json"),
            user.subject,
        )
    except RuntimeError as exc:
        raise HTTPException(
            status_code=500,
            detail="Saved scenarios are temporarily unavailable.",
        ) from exc


@app.get("/api/scenarios")
def get_saved_scenarios(http_request: Request):
    user = get_current_user(http_request)

    try:
        return {
            "scenarios": list_saved_scenarios(user.subject),
        }
    except RuntimeError as exc:
        raise HTTPException(
            status_code=500,
            detail="Saved scenarios are temporarily unavailable.",
        ) from exc


@app.get("/api/scenarios/{scenario_id}")
def get_saved_scenario_by_id(
    scenario_id: str,
    http_request: Request,
):
    user = get_current_user(http_request)

    try:
        saved = get_saved_scenario(
            scenario_id,
            user.subject,
        )
    except RuntimeError as exc:
        raise HTTPException(
            status_code=500,
            detail="Saved scenarios are temporarily unavailable.",
        ) from exc

    if saved is None:
        raise HTTPException(
            status_code=404,
            detail="Saved scenario not found",
        )

    return saved


@app.post("/api/scenarios/{scenario_id}/run")
def run_saved_scenario(
    scenario_id: str,
    http_request: Request,
):
    user = get_current_user(http_request)

    try:
        saved = get_saved_scenario(
            scenario_id,
            user.subject,
        )
    except RuntimeError as exc:
        raise HTTPException(
            status_code=500,
            detail="Saved scenarios are temporarily unavailable.",
        ) from exc

    if saved is None:
        raise HTTPException(
            status_code=404,
            detail="Saved scenario not found",
        )

    try:
        scenario = ScenarioRequest.model_validate(
            saved["scenario"]
        )
        return run_simulation(scenario)
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc


def _normalize_node_id(value: str) -> str:
    return value.strip().lower().replace(" ", "_")


def _coerce_node_lookup(graph, node_id: str) -> str:
    normalized = _normalize_node_id(node_id)

    if normalized in graph:
        return normalized

    for existing_id in graph.nodes:
        if _normalize_node_id(existing_id) == normalized:
            return existing_id

    raise KeyError(node_id)


@app.get("/api/data/dependencies")
def get_dependencies(
    year: int | None = Query(
        default=None,
        ge=1900,
        le=2100,
    ),
):
    bundle = load_comtrade_trade_csv(
        DATA_ROOT
        / "raw"
        / "comtrade"
        / "wheat-global-trade.csv"
    )

    production = load_faostat_production_csv(
        DATA_ROOT
        / "raw"
        / "faostat"
        / "wheat-production.csv"
    )

    return {
        "metrics": calculate_multi_year_dependencies(
            bundle,
            [year] if year is not None else None,
            production,
        ),
        "dataset": (
            bundle.dataset_metadata.model_dump()
            if bundle.dataset_metadata
            else None
        ),
        "quality_report": bundle.quality_report.model_dump(),
    }


@app.get("/api/data/provenance")
def get_data_provenance():
    production = load_faostat_production_csv(
        DATA_ROOT
        / "raw"
        / "faostat"
        / "wheat-production.csv"
    )

    trade = load_comtrade_trade_csv(
        DATA_ROOT
        / "raw"
        / "comtrade"
        / "wheat-global-trade.csv"
    )

    return {
        "datasets": [
            {
                "name": "FAOSTAT wheat production",
                "metadata": (
                    production.dataset_metadata.model_dump()
                    if production.dataset_metadata
                    else None
                ),
                "quality_report": (
                    production.quality_report.model_dump()
                ),
            },
            {
                "name": "UN Comtrade HS1001 wheat trade",
                "metadata": (
                    trade.dataset_metadata.model_dump()
                    if trade.dataset_metadata
                    else None
                ),
                "quality_report": (
                    trade.quality_report.model_dump()
                ),
            },
        ]
    }


@app.get("/api/data/coverage")
def get_data_coverage():
    graph = build_wheat_graph()

    production = load_faostat_production_csv(
        DATA_ROOT
        / "raw"
        / "faostat"
        / "wheat-production.csv"
    )

    trade = load_comtrade_trade_csv(
        DATA_ROOT
        / "raw"
        / "comtrade"
        / "wheat-global-trade.csv"
    )

    production_countries = sorted(
        {
            record.region_name
            for record in production.records
        }
    )

    trade_countries = sorted(
        {
            record.region_name
            for record in trade.records
        }
        |
        {
            record.partner_region
            for record in trade.records
            if record.partner_region
        }
    )

    return {
        "datasets": [
            {
                "name": "FAOSTAT wheat production",
                "status": "fixture_backed",
                "years": sorted(
                    {
                        record.reference_year
                        for record in production.records
                    }
                ),
                "entity_coverage": production_countries,
                "source": "FAOSTAT bulk wheat production fixture",
                "limitations": [
                    "Bounded checked-in fixture subset; not a complete global archive."
                ],
            },
            {
                "name": "UN Comtrade HS1001 wheat trade",
                "status": "fixture_backed",
                "years": sorted(
                    {
                        record.reference_year
                        for record in trade.records
                    }
                ),
                "entity_coverage": trade_countries,
                "source": "UN Comtrade HS1001 fixture",
                "limitations": [
                    "Selected bilateral network; missing flows are not inferred as zero."
                ],
            },
        ],
        "graph": {
            "countries_and_regions": sum(
                1
                for _, data in graph.nodes(data=True)
                if data.get("type") in {"country", "region"}
            ),
            "nodes": graph.number_of_nodes(),
            "edges": graph.number_of_edges(),
            "observed_edges": sum(
                1
                for _, _, data in graph.edges(data=True)
                if data.get("status") == "observed"
            ),
            "derived_edges": sum(
                1
                for _, _, data in graph.edges(data=True)
                if data.get("status") == "derived"
            ),
            "provisional_edges": sum(
                1
                for _, _, data in graph.edges(data=True)
                if data.get("status") == "provisional"
            ),
        },
        "layers": get_layer_coverage(),
    }


@app.get("/api/data/layers/{layer}")
def get_data_layer(layer: str):
    coverage = get_layer_coverage(layer)
    layer_data = coverage.get(layer)

    if not layer_data or layer_data.get("status") == "unknown":
        raise HTTPException(
            status_code=404,
            detail=f"Unknown data layer: {layer}",
        )

    return coverage


@app.get("/api/graph/node/{node_id}")
def get_graph_node(node_id: str):
    graph = build_wheat_graph()

    try:
        canonical_id = _coerce_node_lookup(
            graph,
            node_id,
        )
    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown node: {node_id}",
        ) from exc

    node_data = graph.nodes[canonical_id]

    return {
        "node": {
            "id": canonical_id,
            **node_data,
        },
        "incoming_relationships": [
            {
                "source": source,
                "target": canonical_id,
                **graph[source][canonical_id],
            }
            for source in graph.predecessors(canonical_id)
        ],
        "outgoing_relationships": [
            {
                "source": canonical_id,
                "target": target,
                **graph[canonical_id][target],
            }
            for target in graph.successors(canonical_id)
        ],
        "provenance": {
            "data_source": node_data.get("source_dataset"),
            "reference_year": node_data.get("reference_year"),
            "data_status": node_data.get("status"),
        },
    }


def _build_explanation(
    simulation: dict[str, Any],
) -> dict[str, Any]:
    explanation = build_explanation(simulation)

    return {
        "simulation": simulation,
        "explanation": explanation,
        **explanation,
    }


@app.post("/api/scenario/explain")
def explain_scenario(scenario: ScenarioRequest):
    try:
        return _build_explanation(
            run_simulation(scenario)
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc


def _build_report(
    payload: dict[str, Any],
) -> str:
    simulation = payload["simulation"]
    explanation = payload["explanation"]
    scenario = simulation.get("scenario", {})
    source = simulation.get("source", {})

    return "\n".join(
        [
            "ATLAS DETERMINISTIC SCENARIO REPORT",
            "",
            f"Scenario: {scenario.get('scenario_type', 'unknown')}",
            f"Shock region: {scenario.get('shock_region', 'unknown')}",
            f"Shock: {scenario.get('shock_percent', 'unknown')}%",
            f"Horizon: {scenario.get('time_horizon_months', 'unknown')} months",
            "",
            "MODEL SUMMARY",
            explanation.get(
                "summary",
                "No summary available.",
            ),
            "",
            "OBSERVED DATA",
            (
                "Baseline production (tonnes): "
                f"{source.get('baseline_production_tonnes', 'unavailable')}"
            ),
            (
                "Baseline trade value (USD): "
                f"{source.get('baseline_trade_value', 'unavailable')}"
            ),
            "Sources: FAOSTAT wheat production; UN Comtrade HS1001 wheat trade.",
            "",
            "LIMITATIONS",
            explanation.get(
                "uncertainty",
                {},
            ).get(
                "message",
                "Results are deterministic modeled indicators, not forecasts.",
            ),
            "",
            "ASSUMPTIONS",
            *[
                f"- {item}"
                for item in simulation.get(
                    "assumptions",
                    [],
                )
            ],
        ]
    )


@app.post("/api/scenario/export")
def export_scenario(
    scenario: ScenarioRequest,
    format: str = Query(
        default="json",
        pattern="^(json|report)$",
    ),
):
    try:
        payload = _build_explanation(
            run_simulation(scenario)
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    if format == "report":
        return PlainTextResponse(
            _build_report(payload),
            media_type="text/plain",
            headers={
                "Content-Disposition": (
                    "attachment; "
                    "filename=atlas-scenario-report.txt"
                )
            },
        )

    return JSONResponse(
        payload,
        headers={
            "Content-Disposition": (
                "attachment; "
                "filename=atlas-scenario.json"
            )
        },
    )


@app.post("/api/scenario/node/{node_id}")
def node_scenario(
    node_id: str,
    scenario: NodeScenarioRequest = NodeScenarioRequest(),
):
    graph = build_wheat_graph()

    try:
        canonical_id = _coerce_node_lookup(
            graph,
            node_id,
        )
    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown node: {node_id}",
        ) from exc

    simulation = run_simulation(scenario)

    if simulation.get("status") == "unsupported":
        return {
            "node": {
                "id": canonical_id,
                **graph.nodes[canonical_id],
            },
            "status": "unsupported",
            "scenario": simulation.get(
                "scenario",
                {},
            ),
            "provenance": simulation.get(
                "provenance",
                {},
            ),
            "reason": simulation.get("reason"),
        }

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
            if item["node_id"] == canonical_id
        ),
        None,
    )

    intervention_impact = next(
        (
            item
            for item in intervention_impacts
            if item["node_id"] == canonical_id
        ),
        None,
    )

    temporal_paths = find_temporal_paths(
        graph=graph,
        sources=shock_sources,
        horizon=scenario.time_horizon_months,
    )

    active_paths = [
        path
        for path in temporal_paths
        if canonical_id in path["path"]
        and path["activation_month"]
        <= scenario.time_horizon_months
    ]

    node_data = graph.nodes[canonical_id]

    provenance = {
        "status": "real_data_provisional_model",
        "model_version": simulation.get(
            "model",
            {},
        ).get("version"),
        "data_sources": [
            "FAOSTAT 2024",
            "UN Comtrade 2024",
        ],
        "method": (
            "Backend deterministic scenario simulation using observed "
            "bilateral trade exposure and graph traversal."
        ),
        "forecast_warning": (
            "These are deterministic scenario-model indicators, "
            "not validated real-world forecasts."
        ),
    }

    return {
        "node": {
            "id": canonical_id,
            "name": node_data.get(
                "name",
                canonical_id,
            ),
            "node_type": node_data.get(
                "node_type",
                node_data.get(
                    "type",
                    "unknown",
                ),
            ),
            **node_data,
        },
        "scenario": {
            "shock_region": scenario.shock_region,
            "shock_percent": scenario.shock_percent,
            "time_horizon_months": scenario.time_horizon_months,
            "alternate_supply_percent": scenario.alternate_supply_percent,
            "shock_sources": shock_sources,
        },
        "status": "ok",
        "impact": shock_impact,
        "intervention": intervention_impact,
        "shock_impact": shock_impact,
        "paths": {
            "active_path_count": len(active_paths),
            "paths": active_paths,
        },
        "active_paths": active_paths,
        "deficit_indicator": (
            shock_impact.get(
                "deficit_percent",
                0.0,
            )
            if shock_impact
            else 0.0
        ),
        "price_pressure_indicator": (
            shock_impact.get(
                "price_pressure_percent",
                0.0,
            )
            if shock_impact
            else 0.0
        ),
        "risk": (
            shock_impact.get(
                "risk",
                "LOW",
            )
            if shock_impact
            else "LOW"
        ),
        "confidence": (
            shock_impact.get(
                "confidence",
                0.0,
            )
            if shock_impact
            else 0.0
        ),
        "provenance": provenance,
    }
