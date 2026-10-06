"""ML Pipeline Package."""

from .registry import ModelRegistry
from .train import main as train_main

__all__ = ["train_main", "ModelRegistry"]
