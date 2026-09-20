from app.graph.builder import build_wheat_graph
from app.simulation.engine import (
    build_temporal_timeline,
    calculate_direct_trade_impacts,
    find_temporal_paths,
)


def test_graph_contains_expected_nodes_and_trade_edges():
    graph = build_wheat_graph()
    assert "europe" in graph
    assert "egypt" in graph
    assert "morocco" in graph
    assert "algeria" in graph
    assert graph.has_edge("europe", "egypt")


def test_direct_trade_impacts_are_calculated_for_a_shock():
    graph = build_wheat_graph()
    impacts = calculate_direct_trade_impacts(graph, "europe", -20.0, 10.0)
    assert len(impacts) >= 1
    assert impacts[0]["node_id"] in {"egypt", "morocco", "algeria"}
    assert impacts[0]["shock_supply_loss"] > 0


def test_temporal_paths_follow_delay_logic():
    graph = build_wheat_graph()
    paths = find_temporal_paths(graph, "europe", 6)
    assert any(path["final_node"] == "egypt" for path in paths)
    assert all(path["activation_month"] <= 6 for path in paths)


def test_timeline_includes_required_fields():
    graph = build_wheat_graph()
    impacts = calculate_direct_trade_impacts(graph, "europe", -20.0, 10.0)
    timeline = build_temporal_timeline(graph, "europe", -20.0, impacts, 6, 10.0)
    first_month = timeline[0]
    assert "month" in first_month
    assert "active_paths" in first_month
    assert "affected_nodes" in first_month
    assert "supply_loss" in first_month
    assert "deficit_indicator" in first_month
    assert "price_pressure_indicator" in first_month
    assert "risk" in first_month
    assert "intervention_state" in first_month
