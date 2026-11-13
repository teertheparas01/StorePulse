"""Tests for the analytics summary endpoint."""

from pipeline.ml import serve


def test_analytics_summary_endpoint():
    client = serve.app.test_client()
    response = client.get("/api/analytics/summary")

    assert response.status_code == 200
    data = response.get_json()

    # Verify all required sections are present
    assert "revenue_overview" in data
    assert "profit_margins" in data
    assert "capital_health" in data
    assert "top_sellers" in data
    assert "dead_stock" in data

    # Verify revenue_overview structure
    rev = data["revenue_overview"]
    assert "last_30_days" in rev
    assert "daily_breakdown" in rev
    assert "total_revenue" in rev["last_30_days"]
    assert "bill_count" in rev["last_30_days"]

    # Verify profit_margins structure
    margins = data["profit_margins"]
    assert "overall_margin_pct" in margins
    assert "by_category" in margins

    # Verify capital_health structure
    capital = data["capital_health"]
    assert "total_inventory_capital" in capital
    assert "free_working_capital" in capital
    assert "trapped_dead_stock_capital" in capital
    assert "capital_at_risk_pct" in capital

    # Verify top_sellers structure
    top = data["top_sellers"]
    assert "by_revenue" in top
    assert "by_volume" in top

    # Verify dead_stock is a list
    assert isinstance(data["dead_stock"], list)


def test_analytics_summary_with_custom_days():
    client = serve.app.test_client()
    response = client.get("/api/analytics/summary?days=7")

    assert response.status_code == 200
    data = response.get_json()
    assert "revenue_overview" in data
