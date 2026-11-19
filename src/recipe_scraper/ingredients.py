"""Ingredient-line -> (quantity, unit, name, category).

Pipeline (see README): rules first, local model only for lines the rules cannot place,
and every model answer is validated against the closed category list before use.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from fractions import Fraction
from typing import Callable, Mapping

CATEGORIES = ("produce", "dairy", "meat", "seafood", "baking", "spice", "pantry", "frozen", "beverage", "other")

UNITS = {
    "cup", "cups", "c", "tablespoon", "tablespoons", "tbsp", "tbsps", "tbs", "teaspoon", "teaspoons", "tsp", "tsps",
    "ounce", "ounces", "oz", "pound", "pounds", "lb", "lbs", "gram", "grams", "g", "kg", "ml", "l", "liter", "liters",
    "pinch", "dash", "clove", "cloves", "can", "cans", "package", "packages", "stick", "sticks", "slice", "slices",
    "quart", "quarts", "pint", "pints",
}
_NOISE = re.compile(
    r"\b(softened|melted|chopped|diced|minced|sliced|grated|shredded|beaten|divided|packed|fresh|freshly|large|medium|"
    r"small|finely|roughly|room temperature|to taste|optional|crushed|peeled|cubed|sifted)\b",
    re.I,
)
_QTY = re.compile(r"^\s*(\d+\s+\d+/\d+|\d+/\d+|\d+(?:\.\d+)?)\s*(?:-\s*\d+(?:\.\d+)?)?\s*")

# Seed canonical table: canonical name -> category. In production this lives in Postgres and
# grows from cached model answers; the seed is what ships with the repo.
SEED_CANONICAL: dict[str, str] = {
    "butter": "dairy", "milk": "dairy", "egg": "dairy", "cream": "dairy", "cheese": "dairy",
    "flour": "baking", "sugar": "baking", "brown sugar": "baking",
    "baking soda": "baking", "baking powder": "baking", "vanilla extract": "baking", "chocolate chips": "baking",
    "salt": "spice", "pepper": "spice", "cinnamon": "spice", "paprika": "spice",
    "onion": "produce", "garlic": "produce", "tomato": "produce", "lemon": "produce",
    "carrot": "produce", "potato": "produce",
    "chicken": "meat", "chicken breast": "meat", "beef": "meat", "ground beef": "meat", "bacon": "meat",
    "salmon": "seafood", "shrimp": "seafood",
    "olive oil": "pantry", "oil": "pantry", "water": "beverage", "rice": "pantry", "pasta": "pantry",
}
ALIASES = {"eggs": "egg", "tomatoes": "tomato", "carrots": "carrot", "potatoes": "potato",
           "all-purpose flour": "flour", "black pepper": "pepper", "ground black pepper": "pepper",
           "ground cinnamon": "cinnamon", "ground beef": "ground beef"}


@dataclass
class Ingredient:
    raw: str
    quantity: float | None = None
    unit: str | None = None
    name: str | None = None
    category: str | None = None
    source: str = "none"  # table | model | none
    needs_review: bool = False


def _qty(text: str) -> float | None:
    try:
        return float(sum(Fraction(p) for p in text.split()))
    except (ValueError, ZeroDivisionError):
        return None


def parse(raw: str) -> Ingredient:
    """Rules-only split of a line into quantity / unit / cleaned name. No category yet."""
    s = re.sub(r"\([^)]*\)", " ", raw).split(",")[0]
    ing = Ingredient(raw=raw)
    m = _QTY.match(s)
    if m:
        ing.quantity = _qty(m.group(1))
        s = s[m.end():]
    words = s.split()
    if words and words[0].lower().rstrip(".") in UNITS:
        ing.unit = words[0].lower().rstrip(".")
        words = words[1:]
        if words and words[0].lower() == "of":
            words = words[1:]
    name = re.sub(r"\s+", " ", _NOISE.sub(" ", " ".join(words))).strip(" -.").lower()
    ing.name = name or None
    return ing


def canonical(name: str) -> str:
    return ALIASES.get(name, name)


def normalize(
    raw: str,
    table: Mapping[str, str] | None = None,
    model: Callable[[str], str | None] | None = None,
) -> Ingredient:
    """Parse, look the name up in the canonical table, fall back to `model` (name -> category).

    A model answer is accepted only if it is in CATEGORIES; anything else becomes "other"
    flagged for review. The caller caches accepted answers (source == "model") into the table.
    """
    table = SEED_CANONICAL if table is None else table
    ing = parse(raw)
    if not ing.name:
        ing.needs_review = True
        return ing
    ing.name = canonical(ing.name)
    cat = table.get(ing.name)
    if cat in CATEGORIES:
        ing.category, ing.source = cat, "table"
        return ing
    if model is not None:
        answer = (model(ing.name) or "").strip().lower()
        if answer in CATEGORIES:
            ing.category, ing.source = answer, "model"
            return ing
    ing.category, ing.needs_review = "other", True
    return ing
