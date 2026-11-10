"""Actionable, model-driven retail recommendations."""

from .engine import Recommendation, generate_recommendation
from .web_alternatives import ProductAlternativeResearcher

__all__ = ["ProductAlternativeResearcher", "Recommendation", "generate_recommendation"]
