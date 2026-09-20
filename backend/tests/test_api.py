import pytest

from fastapi.testclient import TestClient

from app.auth import AuthUser, AuthenticationError

from app.data.scenario_store import DEFAULT_STORE, _store_path, list_saved_scenarios
from app.main import _allowed_origins, app


def _fake_verify(token):
    users = {
        "test-firebase-token": AuthUser(
            "api-test",
            "api@example.com",
            "API Test",
        ),
        "second-firebase-token": AuthUser(
            "second-test",
            "second@example.com",
            "Second Test",
        ),
    }

    user = users.get(token)
    if user is None:
        raise AuthenticationError("invalid")

    return user


@pytest.fixture(autouse=True)
def mock_firebase_verifier(monkeypatch):
    monkeypatch.setattr("app.main.verify_firebase_id_token", _fake_verify)


def authenticated_client(token="test-firebase-token"):
    return TestClient(
        app,
        headers={"Authorization": f"Bearer {token}"},
    )


client = authenticated_client()


def test_cors_keeps_local_origins_and_adds_configured_frontend(monkeypatch):
    monkeypatch.delenv("ATLAS_FRONTEND_ORIGIN", raising=False)
    local_origins = _allowed_origins()
    assert "http://localhost:5173" in local_origins
    assert "http://127.0.0.1:5178" in local_origins
    assert "https://app.example.com" not in local_origins

    monkeypatch.setenv("ATLAS_FRONTEND_ORIGIN", "https://app.example.com")
    configured_origins = _allowed_origins()
    assert configured_origins[:-1] == local_origins
    assert configured_origins[-1] == "https://app.example.com"
    assert "*" not in configured_origins


def test_graph_endpoint_returns_nodes_and_edges():
    response = client.get("/api/graph")
    assert response.status_code == 200
    payload = response.json()
    assert "nodes" in payload
    assert "edges" in payload
    assert len(payload["nodes"]) > 0
    assert len(payload["edges"]) > 0


def test_scenario_run_endpoint_returns_model_results():
    payload = {
        "shock_region": "europe",
        "shock_percent": -20.0,
        "time_horizon_months": 6,
        "alternate_supply_percent": 10.0,
    }
    response = client.post("/api/scenario/run", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["scenario"]["shock_region"] == "europe"
    assert len(body["comparison"]["shock"]["timeline"]) == 6
    assert body["comparison"]["intervention_effect"]["supply_loss_reduction_percent"] >= 0


def test_explain_endpoint_returns_summary():
    payload = {
        "shock_region": "europe",
        "shock_percent": -20.0,
        "time_horizon_months": 6,
        "alternate_supply_percent": 10.0,
    }
    response = client.post("/api/scenario/explain", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert "summary" in body
    assert "steps" in body
    assert "5 modeled European producer countries" in body["summary"]
    assert "France, Germany, Poland, Romania, Spain" in body["steps"][0]["description"]


def test_node_inspection_endpoint_works():
    payload = {
        "shock_region": "europe",
        "shock_percent": -20.0,
        "time_horizon_months": 6,
        "alternate_supply_percent": 10.0,
    }
    response = client.post("/api/scenario/node/egypt", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["node"]["id"] == "egypt"
    assert "provenance" in body


def test_invalid_shock_region_is_rejected():
    payload = {
        "shock_region": "moon",
        "shock_percent": -20.0,
        "time_horizon_months": 6,
        "alternate_supply_percent": 10.0,
    }
    response = client.post("/api/scenario/run", json=payload)
    assert response.status_code == 400


def test_compare_endpoint_uses_model_outputs():
    payload = {
        "scenario_a": {
            "shock_region": "europe",
            "shock_percent": -20,
            "time_horizon_months": 6,
            "alternate_supply_percent": 0,
        },
        "scenario_b": {
            "shock_region": "europe",
            "shock_percent": -20,
            "time_horizon_months": 6,
            "alternate_supply_percent": 10,
        },
    }
    response = client.post("/api/scenario/compare", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["baseline"]["supply_loss"] == 0
    assert body["scenario_a"]["supply_loss"] >= body["scenario_b"]["supply_loss"]
    assert "affected_nodes" in body["scenario_a"]
    assert "active_pathways" in body["scenario_b"]


def test_saved_scenario_can_be_retrieved_and_rerun(tmp_path, monkeypatch):
    monkeypatch.setenv("ATLAS_SCENARIO_STORE", str(tmp_path / "saved.json"))

    payload = {
        "name": "European wheat baseline",
        "scenario": {
            "shock_region": "europe",
            "shock_percent": -20,
            "time_horizon_months": 6,
            "alternate_supply_percent": 10,
        },
    }

    user_client = authenticated_client("test-firebase-token")

    saved = user_client.post("/api/scenarios", json=payload)
    assert saved.status_code == 200

    body = saved.json()
    scenario_id = body["id"]

    assert body["owner_id"] == "api-test"

    retrieved = user_client.get(f"/api/scenarios/{scenario_id}")
    assert retrieved.status_code == 200
    assert retrieved.json()["owner_id"] == "api-test"

    rerun = user_client.post(f"/api/scenarios/{scenario_id}/run")
    assert rerun.status_code == 200
    assert rerun.json()["scenario"]["shock_region"] == "europe"


def test_saved_scenario_is_isolated_between_users(tmp_path, monkeypatch):
    monkeypatch.setenv("ATLAS_SCENARIO_STORE", str(tmp_path / "saved.json"))

    payload = {
        "name": "Private European wheat scenario",
        "scenario": {
            "shock_region": "europe",
            "shock_percent": -20,
            "time_horizon_months": 6,
            "alternate_supply_percent": 10,
        },
    }

    first_user = authenticated_client("test-firebase-token")
    second_user = authenticated_client("second-firebase-token")

    saved = first_user.post("/api/scenarios", json=payload)
    assert saved.status_code == 200

    scenario_id = saved.json()["id"]

    first_list = first_user.get("/api/scenarios")
    assert first_list.status_code == 200
    assert len(first_list.json()["scenarios"]) == 1
    assert first_list.json()["scenarios"][0]["owner_id"] == "api-test"

    second_list = second_user.get("/api/scenarios")
    assert second_list.status_code == 200
    assert second_list.json()["scenarios"] == []

    assert second_user.get(
        f"/api/scenarios/{scenario_id}"
    ).status_code == 404

    assert second_user.post(
        f"/api/scenarios/{scenario_id}/run"
    ).status_code == 404


def test_scenario_store_uses_safe_default_for_missing_or_empty_configuration(monkeypatch):
    monkeypatch.delenv("ATLAS_SCENARIO_STORE", raising=False)
    assert _store_path() == DEFAULT_STORE

    monkeypatch.setenv("ATLAS_SCENARIO_STORE", "  ")
    assert _store_path() == DEFAULT_STORE


def test_scenario_store_treats_empty_file_as_empty_store(tmp_path, monkeypatch):
    path = tmp_path / "saved.json"
    path.write_text("", encoding="utf-8")
    monkeypatch.setenv("ATLAS_SCENARIO_STORE", str(path))

    assert list_saved_scenarios("api-test") == []


def test_malformed_scenario_store_returns_safe_api_error(tmp_path, monkeypatch):
    path = tmp_path / "saved.json"
    path.write_text('{"not": "a list"}', encoding="utf-8")
    monkeypatch.setenv("ATLAS_SCENARIO_STORE", str(path))

    response = client.get("/api/scenarios")

    assert response.status_code == 500
    assert response.json()["detail"] == "Saved scenarios are temporarily unavailable."
    assert str(path) not in response.text
