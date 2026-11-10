"""Tests for web-backed product alternative ranking."""

from pipeline.recommendations.web_alternatives import ProductAlternativeResearcher


class FakeSearchProvider:
    """Network-free search provider for ranking tests."""

    def search(self, query: str, count: int = 10) -> list[dict[str, str]]:
        assert "Trailblazer footwear" in query
        return [
            {
                "title": "Trailblazer running footwear",
                "url": "https://example.com/better",
                "snippet": "4.8/5 stars, $80, in stock",
            },
            {
                "title": "Kitchen blender",
                "url": "https://example.com/unrelated",
                "snippet": "5/5 stars, $40, in stock",
            },
        ]


def test_ranks_comparable_products_using_similarity_and_quality():
    researcher = ProductAlternativeResearcher(FakeSearchProvider())

    result = researcher.find_alternatives(
        {
            "product_no": "P1",
            "product_description": "Trailblazer footwear",
            "product_category": "Footwear",
            "unit_price": 100,
        },
        limit=1,
    )

    assert result["alternatives"][0]["url"] == "https://example.com/better"
    assert result["alternatives"][0]["rating"] == 4.8
    assert result["alternatives"][0]["price"] == 80.0


def test_requires_product_description():
    researcher = ProductAlternativeResearcher(FakeSearchProvider())

    try:
        researcher.find_alternatives({})
    except ValueError as error:
        assert "product_description" in str(error)
    else:
        raise AssertionError("Expected product_description validation error")


def test_api_reports_missing_search_credentials(monkeypatch):
    from pipeline.ml import serve

    monkeypatch.delenv("BRAVE_SEARCH_API_KEY", raising=False)
    client = serve.app.test_client()

    health = client.get("/health")
    response = client.post(
        "/product-alternatives",
        json={"product_description": "Trailblazer footwear"},
    )

    assert health.status_code == 200
    assert health.get_json()["web_search_configured"] is False
    assert response.status_code == 503
