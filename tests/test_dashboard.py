"""Tests for the browser dashboard endpoints."""

from pipeline.ml import serve


def test_dashboard_page_loads():
    response = serve.app.test_client().get("/dashboard")

    assert response.status_code == 200
    assert b"Find a better product" in response.data


def test_dashboard_data_contains_operational_sections():
    response = serve.app.test_client().get("/dashboard-data")
    payload = response.get_json()

    assert response.status_code == 200
    assert {"dataset", "model", "web_search", "monitoring", "backtest"} <= payload.keys()
