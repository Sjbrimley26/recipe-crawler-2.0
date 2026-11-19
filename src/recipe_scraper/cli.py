"""Command line: crawl seeds politely and store recipes in Postgres.

    recipe-scraper crawl --dsn postgresql://... --state crawl.json --max-pages 20 https://site/recipes
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Callable

import psycopg

from . import store
from .crawl import crawl
from .fetch import Fetcher


def run(
    seeds: list[str],
    dsn: str,
    fetcher,
    state: Path | None = None,
    max_pages: int = 50,
    max_depth: int = 2,
    model: Callable[[str], str | None] | None = None,
) -> int:
    """Crawl and store; returns the number of recipes saved."""
    saved = 0
    with psycopg.connect(dsn) as conn:
        store.init(conn)

        def on_recipe(url: str, recipe: dict) -> None:
            nonlocal saved
            store.save_recipe(conn, url, recipe, model)
            saved += 1

        crawl(seeds, fetcher, on_recipe, state, max_pages, max_depth)
    return saved


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="recipe-scraper")
    sub = p.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("crawl", help="crawl seed URLs and store recipes")
    c.add_argument("seeds", nargs="+")
    c.add_argument("--dsn", default=os.environ.get("DATABASE_URL"), help="Postgres DSN (or $DATABASE_URL)")
    c.add_argument("--state", type=Path, help="resume file; created if missing")
    c.add_argument("--max-pages", type=int, default=50)
    c.add_argument("--max-depth", type=int, default=2)
    c.add_argument("--interval", type=float, default=2.0, help="seconds between requests per host")
    a = p.parse_args(argv)
    if not a.dsn:
        p.error("--dsn or DATABASE_URL required")
    n = run(a.seeds, a.dsn, Fetcher(min_interval=a.interval), a.state, a.max_pages, a.max_depth)
    print(f"saved {n} recipes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
