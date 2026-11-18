# recipe-scraper

Python rewrite of the crawler in github.com/Sjbrimley26/recipe-app (Node, 2020).

Status: scaffold. Done: JSON-LD extraction (list / @graph / typed-list safe), polite fetcher
(real User-Agent, robots.txt, rate limit, bounded retries), tests on a saved fixture.
Not done: crawl loop + frontier, Postgres storage, ingredient normalization.

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
