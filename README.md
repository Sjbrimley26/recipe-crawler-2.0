# recipe-scraper

Python rewrite of the crawler in github.com/Sjbrimley26/recipe-app (Node, 2020).

Status: scaffold. Done: JSON-LD extraction (list / @graph / typed-list safe), polite fetcher
(real User-Agent, robots.txt, rate limit, bounded retries), tests on a saved fixture.
Done since: crawl loop (frontier, depth/page limits, atomic resume file), rules parser + seed canonical table + validated model-fallback hook.
Done since: Postgres storage (one-transaction recipe+ingredients, canonical table in PG, model-answer cache), `recipe-scraper crawl` CLI.
Not done: local-model comparison on ~200 labels, GitHub push.

## Run it
```
docker run -d --name recipes-pg -e POSTGRES_PASSWORD=dev -p 127.0.0.1:5432:5432 postgres:16-alpine
export DATABASE_URL=postgresql://postgres:dev@127.0.0.1:5432/postgres
.venv/bin/recipe-scraper crawl --state crawl.json --max-pages 20 --max-depth 2 --interval 3 https://example.com/recipes
```
Re-running with the same `--state` resumes; recipes upsert by URL, so repeats are safe. Keep the page limit small and the
interval polite. `tests/test_store.py` starts its own throwaway postgres container and skips without docker.

Why a rewrite (found 2026-11-18): Allrecipes returns 403 to the axios User-Agent and 200 to a browser one;
JSON-LD is still present but `@type` is `["Recipe","NewsArticle"]`, which the old exact-match missed.

## Ingredient normalization plan (rules first, local model for the leftovers)
1. Parse "1 1/2 cups packed brown sugar, divided" with a library (e.g. ingredient-parser-nlp) or small rules.
2. Canonicalize names with a lookup table in Postgres (replaces the old hardcoded duplicateReplacements).
3. Only names not in the table go to a local model: "name -> canonical name + category from CATEGORIES".
   Constrain output (JSON schema / enum), validate against the closed list, cache the answer in the table,
   so each distinct name is asked once. Unknown/invalid -> "other" and flagged for review.
4. Measure before trusting: hand-label ~200 names, score candidate local models vs rules-only
   (the ollama-bench notebook and the categorize-arena skill have a harness for exactly this shape).

Run tests: `uv venv .venv && uv pip install -p .venv/bin/python -e '.[dev]' && .venv/bin/pytest`
