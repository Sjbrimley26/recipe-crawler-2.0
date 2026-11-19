"""Integration tests against a throwaway postgres:16-alpine container (skipped without docker)."""
from __future__ import annotations

import shutil
import subprocess
import time
import uuid

import psycopg
import pytest

from recipe_scraper import store

RECIPE = {
    "name": "Cookies",
    "recipeIngredient": ["2 cups all-purpose flour", "1 cup butter, softened", "3 tbsp dragonfruit puree"],
}


@pytest.fixture(scope="module")
def dsn():
    if shutil.which("docker") is None or subprocess.run(["docker", "info"], capture_output=True).returncode:
        pytest.skip("docker not available")
    name = f"recipe-test-{uuid.uuid4().hex[:8]}"
    subprocess.run(
        ["docker", "run", "-d", "--rm", "--name", name, "-e", "POSTGRES_PASSWORD=test", "-p", "127.0.0.1::5432",
         "postgres:16-alpine"],
        check=True, capture_output=True,
    )
    try:
        port = subprocess.run(["docker", "port", name, "5432/tcp"], check=True, capture_output=True, text=True
                              ).stdout.split(":")[-1].strip()
        url = f"postgresql://postgres:test@127.0.0.1:{port}/postgres"
        deadline = time.time() + 60
        while True:
            try:
                psycopg.connect(url).close()
                break
            except Exception:
                if time.time() > deadline:
                    raise
                time.sleep(0.5)
        yield url
    finally:
        subprocess.run(["docker", "rm", "-f", name], capture_output=True)


@pytest.fixture()
def conn(dsn):
    with psycopg.connect(dsn, autocommit=True) as c:
        store.init(c)
        c.execute("TRUNCATE recipe CASCADE")
        c.execute("DELETE FROM canonical_ingredient WHERE source = 'model'")
        yield c


def test_save_and_idempotent_upsert(conn):
    rid = store.save_recipe(conn, "http://x/1", RECIPE)
    assert store.save_recipe(conn, "http://x/1", RECIPE) == rid
    assert conn.execute("SELECT count(*) FROM recipe").fetchone()[0] == 1
    assert conn.execute("SELECT count(*) FROM recipe_ingredient").fetchone()[0] == 3
    cat = dict(conn.execute("SELECT name, category FROM recipe_ingredient"))
    assert cat["flour"] == "baking" and cat["butter"] == "dairy"


def test_model_answer_cached_once(conn):
    calls: list[str] = []

    def model(name: str) -> str:
        calls.append(name)
        return "produce"

    store.save_recipe(conn, "http://x/1", RECIPE, model)
    store.save_recipe(conn, "http://x/2", RECIPE, model)
    assert calls == ["dragonfruit puree"]
    assert conn.execute("SELECT source FROM canonical_ingredient WHERE name='dragonfruit puree'").fetchone()[0] == "model"


def test_invalid_model_answer_not_cached(conn):
    store.save_recipe(conn, "http://x/1", RECIPE, lambda n: "banana")
    assert conn.execute("SELECT count(*) FROM canonical_ingredient WHERE source='model'").fetchone()[0] == 0
    assert conn.execute("SELECT needs_review FROM recipe_ingredient WHERE name='dragonfruit puree'").fetchone()[0]


def test_failure_mid_recipe_rolls_back_everything(conn):
    def boom(name: str) -> str:
        raise RuntimeError("model died")

    with pytest.raises(RuntimeError):
        store.save_recipe(conn, "http://x/9", RECIPE, boom)
    assert conn.execute("SELECT count(*) FROM recipe").fetchone()[0] == 0
    assert conn.execute("SELECT count(*) FROM recipe_ingredient").fetchone()[0] == 0


class _FakeSite:
    def __init__(self, pages):
        self.pages = pages

    def get(self, url):
        return self.pages.get(url)


def test_cli_run_end_to_end(dsn, conn, tmp_path):
    from pathlib import Path

    from recipe_scraper.cli import run

    html = (Path(__file__).parent / "fixtures" / "cookies.html").read_text()
    site = _FakeSite({
        "http://s/": '<a href="/r1">r1</a><a href="/r2">r2</a>',
        "http://s/r1": html,
        "http://s/r2": html,
    })
    n = run(["http://s/"], dsn, site, tmp_path / "state.json", max_pages=10, max_depth=2)
    assert n == 2
    assert conn.execute("SELECT count(*) FROM recipe").fetchone()[0] == 2
