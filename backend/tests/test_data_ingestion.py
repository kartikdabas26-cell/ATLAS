from pathlib import Path

from app.data.contracts import MetricType
from app.data.loaders import load_comtrade_trade_csv, load_faostat_production_csv
from app.graph.builder import build_wheat_graph

DATA_ROOT = Path(__file__).resolve().parents[1] / "data"


def test_faostat_fixture_supports_multiple_years():
    bundle = load_faostat_production_csv(DATA_ROOT / "raw" / "faostat" / "wheat-production.csv")
    assert bundle.reference_year == 2024
    assert any(record.region_name == "France" and record.reference_year == 2024 for record in bundle.records)
    assert any(record.region_name == "France" and record.reference_year == 2023 for record in bundle.records)
    assert any(record.metric == MetricType.PRODUCTION for record in bundle.records)
    assert bundle.quality_report.row_count == 25


def test_comtrade_fixture_distinguishes_value_and_quantity():
    bundle = load_comtrade_trade_csv(DATA_ROOT / "raw" / "comtrade" / "wheat-global-trade.csv")
    usd_records = [record for record in bundle.records if record.unit == "USD"]
    kg_records = [record for record in bundle.records if record.unit == "kg"]
    assert len(usd_records) > 0
    assert len(kg_records) > 0
    assert any(record.region_name == "France" and record.partner_region == "Egypt" for record in usd_records)


def test_graph_is_built_from_normalized_trade_data():
    graph = build_wheat_graph()
    assert "europe" in graph
    assert graph.has_edge("europe", "egypt")
    assert graph["europe"]["egypt"]["relationship"] == "SUPPLIES_TO"
    assert graph["europe"]["egypt"]["weight"] > 0
