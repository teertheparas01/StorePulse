"""Web-backed product alternative research.

The search provider is injected so ranking can be tested without network access.
Brave Search is the default provider because it exposes structured web results;
the API key is read only from the environment.
"""

from __future__ import annotations

import json
import os
import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen


class SearchProvider(Protocol):
    """Interface implemented by external web-search providers."""

    def search(self, query: str, count: int = 10) -> list[dict[str, Any]]:
        """Return title, URL, and snippet fields for web results."""


@dataclass(frozen=True)
class AlternativeProduct:
    """A web result ranked as a possible product alternative."""

    title: str
    url: str
    snippet: str
    source: str
    similarity_score: float
    value_quality_score: float
    price: float | None
    rating: float | None
    evidence: list[str]

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable search result."""
        return {
            "title": self.title,
            "url": self.url,
            "snippet": self.snippet,
            "source": self.source,
            "similarity_score": self.similarity_score,
            "value_quality_score": self.value_quality_score,
            "price": self.price,
            "rating": self.rating,
            "evidence": self.evidence,
        }


class BraveSearchClient:
    """Small standard-library client for Brave's web-search API."""

    def __init__(
        self,
        api_key: str | None = None,
        endpoint: str = "https://api.search.brave.com/res/v1/web/search",
        timeout: float = 10.0,
    ) -> None:
        self.api_key = api_key or os.getenv("BRAVE_SEARCH_API_KEY")
        self.endpoint = endpoint
        self.timeout = timeout

    def search(self, query: str, count: int = 10) -> list[dict[str, Any]]:
        """Search the public web and return normalized result dictionaries."""
        if not self.api_key:
            raise RuntimeError("BRAVE_SEARCH_API_KEY is required for web product research")

        params = urlencode({"q": query, "count": min(max(count, 1), 20)})
        request = Request(
            f"{self.endpoint}?{params}",
            headers={
                "Accept": "application/json",
                "X-Subscription-Token": self.api_key,
                "User-Agent": "retail-decision-intelligence/1.0",
            },
        )
        try:
            with urlopen(request, timeout=self.timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            raise RuntimeError(f"Web search provider returned HTTP {error.code}") from error
        except URLError as error:
            raise RuntimeError("Web search provider is unavailable") from error

        return [
            {
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "snippet": item.get("description", ""),
            }
            for item in payload.get("web", {}).get("results", [])
        ]


def _tokens(value: str) -> set[str]:
    """Extract useful comparison terms from a product description."""
    stop_words = {"the", "and", "for", "with", "from", "product", "model"}
    return {
        token
        for token in re.findall(r"[a-z0-9]+", value.lower())
        if len(token) > 2 and token not in stop_words
    }


def _similarity(reference: str, candidate: str) -> float:
    reference_tokens = _tokens(reference)
    candidate_tokens = _tokens(candidate)
    if not reference_tokens or not candidate_tokens:
        return 0.0
    return len(reference_tokens & candidate_tokens) / len(reference_tokens | candidate_tokens)


def _extract_price(value: str) -> float | None:
    match = re.search(
        r"(?:[$€£₹]\s*([0-9]+(?:[.,][0-9]{1,2})?)|([0-9]+(?:[.,][0-9]{1,2})?)\s*(?:USD|INR|EUR|GBP))",
        value,
        re.I,
    )
    if not match:
        return None
    raw = next(group for group in match.groups() if group is not None)
    try:
        return float(raw.replace(",", ""))
    except ValueError:
        return None


def _extract_rating(value: str) -> float | None:
    match = re.search(r"\b([0-5](?:[.,][0-9])?)\s*(?:/\s*5|out of 5|stars?)\b", value, re.I)
    if not match:
        return None
    return min(5.0, max(0.0, float(match.group(1).replace(",", "."))))


class ProductAlternativeResearcher:
    """Search and rank web alternatives for a selected retail product."""

    def __init__(self, search_provider: SearchProvider) -> None:
        self.search_provider = search_provider

    @classmethod
    def from_config(cls, config: Mapping[str, Any]) -> ProductAlternativeResearcher:
        """Build a researcher from the web-search configuration."""
        api_key_env = str(config.get("api_key_env", "BRAVE_SEARCH_API_KEY"))
        return cls(
            BraveSearchClient(
                api_key=os.getenv(api_key_env),
                endpoint=str(
                    config.get("endpoint", "https://api.search.brave.com/res/v1/web/search")
                ),
                timeout=float(config.get("timeout_seconds", 10.0)),
            )
        )

    def find_alternatives(
        self,
        product: Mapping[str, Any],
        limit: int = 5,
    ) -> dict[str, Any]:
        """Search the web and return ranked alternatives with source evidence."""
        description = str(product.get("product_description", "")).strip()
        category = str(product.get("product_category", "")).strip()
        subcategory = str(product.get("product_subcategory", "")).strip()
        if not description:
            raise ValueError("product_description is required")

        reference = " ".join(part for part in (description, category, subcategory) if part)
        query = f"{reference} alternative comparable product review price"
        raw_results = self.search_provider.search(query, count=max(limit * 3, 10))
        original_price = _extract_price(str(product.get("unit_price", "")))
        alternatives = [
            self._rank_result(result, reference, original_price)
            for result in raw_results
            if result.get("url") and result.get("title")
        ]
        alternatives.sort(key=lambda result: result.value_quality_score, reverse=True)
        return {
            "product": {
                "product_no": product.get("product_no"),
                "product_description": description,
                "product_category": category,
                "product_subcategory": subcategory,
            },
            "query": query,
            "alternatives": [alternative.to_dict() for alternative in alternatives[:limit]],
        }

    @staticmethod
    def _rank_result(
        result: Mapping[str, Any],
        reference: str,
        original_price: float | None,
    ) -> AlternativeProduct:
        title = str(result.get("title", ""))
        url = str(result.get("url", ""))
        snippet = str(result.get("snippet", ""))
        searchable = f"{title} {snippet}"
        similarity = _similarity(reference, searchable)
        price = _extract_price(searchable)
        rating = _extract_rating(searchable)
        quality_score = rating / 5 if rating is not None else 0.5
        if original_price and price and price > 0:
            value_score = min(1.0, original_price / price)
        else:
            value_score = 0.5
        score = 0.55 * similarity + 0.25 * quality_score + 0.20 * value_score

        evidence = [f"{similarity:.0%} text similarity to the selected product."]
        if rating is not None:
            evidence.append(f"Web result reports a {rating:.1f}/5 rating.")
        if price is not None:
            evidence.append(f"Web result reports a price of {price:.2f}.")
        if any(word in searchable.lower() for word in ("in stock", "available", "ships")):
            evidence.append("Availability language was found in the result.")

        return AlternativeProduct(
            title=title,
            url=url,
            snippet=snippet,
            source=urlparse(url).netloc,
            similarity_score=round(similarity, 4),
            value_quality_score=round(score, 4),
            price=price,
            rating=rating,
            evidence=evidence,
        )
