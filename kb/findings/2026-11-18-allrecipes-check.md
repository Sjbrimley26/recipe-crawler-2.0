---
type: "Finding"
title: "Allrecipes check, 2026-11-18: UA filter and JSON-LD shape"
description: "One plain GET to a recipe page: axios User-Agent gets 403, a browser one gets 200 with JSON-LD in a new shape."
tags: [allrecipes, measured]
resource: "https://www.allrecipes.com/recipe/10813/best-chocolate-chip-cookies/"
generated: { by: "hermes-agent/claude-sonnet-5-5", at: "2026-11-18T15:40:00Z" }
---

# Allrecipes check (2026-11-18)

One request per User-Agent to the chocolate chip cookie page.

- `axios/0.21.1` User-Agent: **403**. A browser User-Agent: **200**, about 590 KB.
- One `application/ld+json` block, a list whose item has `@type` = `["Recipe","NewsArticle"]`; `recipeIngredient` is a list of
  strings such as "1 cup butter, softened". The old exact-match on `'Recipe'` would miss it.
- About 28 `/recipe/` links on the page, so link-following still has material.

Not measured: robots.txt rules, behaviour under sustained crawling, the other fallback selectors. The trimmed page is saved as
`tests/fixtures/cookies.html`.
