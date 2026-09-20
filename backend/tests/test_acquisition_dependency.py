import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.auth import AuthUser, AuthenticationError
from app.data.acquisition import (
    acquire_cached_file,
    validate_comtrade_json,
    validate_csv_columns,
)
from app.data.dependency import calculate_multi_year_dependencies
from app.data.loaders import load_comtrade_trade_csv
from app.main import app


DATA_ROOT = Path(__file__).resolve().parents[1] / "data"


def authenticated_client() -> TestClient:
    client = TestClient(app)
    client.headers.update({"Authorization": "Bearer test-firebase-token"})
    return client


def _fake_verify(token):
    if token != "test-firebase-token":
        raise AuthenticationError("invalid")
    return AuthUser("data-test", "data@example.com", "Data Test")


import pytest


@pytest.fixture(autouse=True)
def mock_firebase_verifier(monkeypatch):
    monkeypatch.setattr("app.main.verify_firebase_id_token", _fake_verify)


def test_cached_acquisition_records_checksum_without_network(tmp_path: Path):
    source = tmp_path / "source.csv"
    source.write_text("country,year\nFrance,2024\n", encoding="utf-8")
    destination = tmp_path / "raw.csv"

    result = acquire_cached_file(
        url=source.as_uri(),
        raw_path=destination,
        dataset_name="local test source",
        min_bytes=1,
    )
    assert result.from_cache is False
    assert result.sha256
    assert json.loads(result.metadata_path.read_text(encoding="utf-8"))["retrieval_status"] == "downloaded"

    cached = acquire_cached_file(
        url="https://invalid.example/not-used",
        raw_path=destination,
        dataset_name="local test source",
        min_bytes=1,
    )
    assert cached.from_cache is True


def test_download_validation_rejects_missing_schema(tmp_path: Path):
    path = tmp_path / "bad.csv"
    path.write_text("country\nFrance\n", encoding="utf-8")
    try:
        validate_csv_columns(path, {"country", "year"})
    except RuntimeError as exc:
        assert "missing required columns" in str(exc)
    else:
        raise AssertionError("Expected malformed schema to be rejected")


def test_comtrade_json_validation_requires_data_array(tmp_path: Path):
    path = tmp_path / "response.json"
    path.write_text(json.dumps({"error": "bad"}), encoding="utf-8")
    try:
        validate_comtrade_json(path)
    except RuntimeError as exc:
        assert "data list" in str(exc)
    else:
        raise AssertionError("Expected malformed Comtrade response to be rejected")


def test_faostat_quality_report_preserves_rejections_and_zero(tmp_path: Path):
    path = tmp_path / "faostat.csv"
    path.write_text(
        "country,year,production_tonnes,harvested_area_ha,yield_kg_ha\n"
        "France,2024,0,1,2\n"
        "France,2024,10,1,2\n"
        ",2024,10,1,2\n"
        "Germany,1899,10,1,2\n"
        "Spain,2024,-4,1,2\n"
        "Italy,2024,NA,1,2\n",
        encoding="utf-8",
    )
    bundle = __import__("app.data.loaders", fromlist=["load_faostat_production_csv"]).load_faostat_production_csv(path)
    report = bundle.quality_report
    assert report.duplicate_rows == 1
    assert report.invalid_years == [1899]
    assert report.negative_values == ["Spain:2024"]
    assert report.missing_values
    assert report.zero_values == ["France:2024:production"]
    assert any(record.value == 0 for record in bundle.records)


def test_comtrade_quality_report_distinguishes_missing_from_zero(tmp_path: Path):
    path = tmp_path / "comtrade.csv"
    path.write_text(
        "reporter,partner,year,flow,commodity_code,trade_value_usd,quantity_kg\n"
        "France,Egypt,2024,Export,1001,0,0\n"
        "France,Egypt,2024,Export,1001,,\n"
        ",Egypt,2024,Export,1001,10,10\n"
        "France,,2024,Export,1001,10,10\n",
        encoding="utf-8",
    )
    bundle = load_comtrade_trade_csv(path)
    assert bundle.quality_report.missing_values
    assert any(record.value == 0 for record in bundle.records)
    assert bundle.quality_report.rejected_rows >= 3


def test_multi_year_dependency_metrics_include_hhi_and_change():
    bundle = load_comtrade_trade_csv(
        DATA_ROOT / "raw" / "comtrade" / "wheat-global-trade.csv"
    )
    metrics = calculate_multi_year_dependencies(bundle)
    assert metrics
    egypt = next(metric for metric in metrics if metric["importer"] == "Egypt")
    assert 0 < egypt["supplier_concentration_hhi"] <= 1
    assert egypt["active_supplier_count"] > 1
    assert egypt["status"] == "provisional"


def test_dependency_endpoint_and_supplier_disruption():
    client = authenticated_client()
    dependency_response = client.get("/api/data/dependencies?year=2024")
    assert dependency_response.status_code == 200
    assert dependency_response.json()["metrics"]

    supplier_response = client.post(
        "/api/scenario/run",
        json={
            "scenario_type": "supplier_disruption",
            "supplier_region": "france",
            "shock_percent": -20,
            "time_horizon_months": 6,
            "alternate_supply_percent": 0,
        },
    )
    assert supplier_response.status_code == 200
    assert supplier_response.json()["scenario"]["scenario_type"] == "supplier_disruption"


def test_trade_disruption_requires_target_and_logistics_is_explicitly_unsupported():
    client = authenticated_client()
    invalid = client.post(
        "/api/scenario/run",
        json={
            "scenario_type": "trade_disruption",
            "supplier_region": "france",
            "shock_percent": -20,
        },
    )
    assert invalid.status_code == 422

    unsupported = client.post(
        "/api/scenario/run",
        json={
            "scenario_type": "logistics_disruption",
            "shock_region": "europe",
            "shock_percent": -20,
        },
    )
    assert unsupported.status_code == 200
    assert unsupported.json()["status"] == "unsupported"


def test_coverage_and_unavailable_domain_layers_are_explicit():
    client = authenticated_client()
    coverage = client.get("/api/data/coverage")
    assert coverage.status_code == 200
    body = coverage.json()
    assert body["graph"]["observed_edges"] > 0
    assert body["layers"]["climate"]["status"] == "unavailable"

    layer = client.get("/api/data/layers/climate")
    assert layer.status_code == 200
    assert layer.json()["climate"]["status"] == "unavailable"

    unknown = client.get("/api/data/layers/unknown")
    assert unknown.status_code == 404
