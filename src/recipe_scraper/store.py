"""Postgres storage: recipe + ingredients in ONE transaction, canonical table, model-answer cache.

The legacy Node crawler wrote the recipe row and then each ingredient separately, so a failure
mid-way left a partial recipe. Here `save_recipe` runs in a single transaction: all or nothing.
"""
from __future__ import annotations

from typing import Callable

import psycopg

from .ingredients import CATEGORIES, SEED_CANONICAL, Ingredient, normalize
from .jsonld import ingredient_lines

SCHEMA = """
CREATE TABLE IF NOT EXISTS canonical_ingredient (
    name     text PRIMARY KEY,
    category text NOT NULL,
    source   text NOT NULL DEFAULT 'seed'      -- seed | model
);
CREATE TABLE IF NOT EXISTS recipe (
    id    bigserial PRIMARY KEY,
    url   text NOT NULL UNIQUE,
    name  text,
    data  jsonb NOT NULL
);
CREATE TABLE IF NOT EXISTS recipe_ingredient (
    id           bigserial PRIMARY KEY,
    recipe_id    bigint NOT NULL REFERENCES recipe(id) ON DELETE CASCADE,
    position     int NOT NULL,
    raw          text NOT NULL,
    quantity     double precision,
    unit         text,
    name         text,
    category     text,
    source       text NOT NULL,
    needs_review boolean NOT NULL DEFAULT false
);
"""


def init(conn: psycopg.Connection) -> None:
    """Create tables and load the seed canonical table (idempotent)."""
    with conn.transaction():
        conn.execute(SCHEMA)
        for name, cat in SEED_CANONICAL.items():
            conn.execute(
                "INSERT INTO canonical_ingredient(name, category, source) VALUES (%s,%s,'seed') "
                "ON CONFLICT (name) DO NOTHING",
                (name, cat),
            )


def load_table(conn: psycopg.Connection) -> dict[str, str]:
    return {n: c for n, c in conn.execute("SELECT name, category FROM canonical_ingredient")}


def save_recipe(
    conn: psycopg.Connection,
    url: str,
    recipe: dict,
    model: Callable[[str], str | None] | None = None,
) -> int:
    """Upsert one recipe and its normalized ingredients atomically. Returns the recipe id.

    Model answers are only asked for names missing from the canonical table, and each accepted
    answer is written back to it, so every distinct name is asked once.
    """
    from psycopg.types.json import Jsonb

    with conn.transaction():
        table = load_table(conn)
        rid = conn.execute(
            "INSERT INTO recipe(url, name, data) VALUES (%s,%s,%s) "
            "ON CONFLICT (url) DO UPDATE SET name = EXCLUDED.name, data = EXCLUDED.data RETURNING id",
            (url, recipe.get("name"), Jsonb(recipe)),
        ).fetchone()[0]
        conn.execute("DELETE FROM recipe_ingredient WHERE recipe_id = %s", (rid,))
        for pos, line in enumerate(ingredient_lines(recipe)):
            ing: Ingredient = normalize(line, table, model)
            if ing.source == "model" and ing.name and ing.category in CATEGORIES:
                conn.execute(
                    "INSERT INTO canonical_ingredient(name, category, source) VALUES (%s,%s,'model') "
                    "ON CONFLICT (name) DO NOTHING",
                    (ing.name, ing.category),
                )
                table[ing.name] = ing.category
            conn.execute(
                "INSERT INTO recipe_ingredient(recipe_id, position, raw, quantity, unit, name, category, source, needs_review) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (rid, pos, ing.raw, ing.quantity, ing.unit, ing.name, ing.category, ing.source, ing.needs_review),
            )
    return rid
