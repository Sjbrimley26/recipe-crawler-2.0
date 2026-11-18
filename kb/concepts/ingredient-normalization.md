---
type: "Concept"
title: "Ingredient normalization: rules first, local model for leftovers"
description: "Plan for turning ingredient lines into quantity, canonical name and category."
tags: [ingredients, local-llm, plan]
generated: { by: "hermes-agent/claude-sonnet-5-5", at: "2026-11-18T15:40:00Z" }
---

# Ingredient normalization

1. Parse quantity and unit with a library or rules.
2. Look the name up in a Postgres canonical-name table (replaces the old hardcoded merge list).
3. Names not in the table go to a local model that must choose a canonical name and a category from a closed list.
   Output is constrained (enum or JSON schema), validated, and cached so each distinct name is asked once. An invalid answer
   becomes "other" and is flagged for review.
4. The model is chosen by measurement: about 200 hand-labelled names, candidates compared against rules-only. Not yet done.

Categories (see `src/recipe_scraper/ingredients.py`): produce, dairy, meat, seafood, baking, spice, pantry, frozen, beverage, other.
Open work lives on the backlog card recipe-scraper-python-port.
