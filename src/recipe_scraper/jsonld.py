"""Extract schema.org Recipe objects from a page's JSON-LD.

Handles what the 2020 Node parser did not: several <script> blocks, a top-level
list, an @graph wrapper, and @type given as a string or a list.
"""
from __future__ import annotations

import json
from bs4 import BeautifulSoup


def _walk(node):
    if isinstance(node, list):
        for n in node:
            yield from _walk(n)
    elif isinstance(node, dict):
        yield node
        if "@graph" in node:
            yield from _walk(node["@graph"])


def _is_recipe(obj: dict) -> bool:
    t = obj.get("@type")
    return t == "Recipe" or (isinstance(t, list) and "Recipe" in t)


def extract_recipe(html: str) -> dict | None:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(tag.string or "")
        except json.JSONDecodeError:
            continue
        for obj in _walk(data):
            if _is_recipe(obj):
                return obj
    return None


def ingredient_lines(recipe: dict) -> list[str]:
    raw = recipe.get("recipeIngredient") or recipe.get("ingredients") or []
    if isinstance(raw, str):
        raw = [raw]
    return [str(x).strip() for x in raw if str(x).strip()]
