"""Ingredient-line -> (quantity, unit, name, category).

Pipeline (see README): rules first, local model only for lines the rules cannot place,
and every model answer is validated against the closed category list before use.
"""
from __future__ import annotations

from dataclasses import dataclass

CATEGORIES = ("produce", "dairy", "meat", "seafood", "baking", "spice", "pantry", "frozen", "beverage", "other")


@dataclass
class Ingredient:
    raw: str
    name: str | None = None
    category: str | None = None


def normalize(raw: str) -> Ingredient:
    raise NotImplementedError("stage 1: rule/library parser; stage 2: local-model fallback (see backlog card)")
