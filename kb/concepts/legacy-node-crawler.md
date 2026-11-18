---
type: "Concept"
title: "The 2020 Node crawler (recipe-app)"
description: "What github.com/Sjbrimley26/recipe-app's crawler did, and its known weak spots."
tags: [crawler, legacy]
resource: "https://github.com/Sjbrimley26/recipe-app"
generated: { by: "hermes-agent/claude-sonnet-5-5", at: "2026-11-18T15:40:00Z" }
sources: [{ id: "recipe-app", resource: "https://github.com/Sjbrimley26/recipe-app", title: "recipe-app repo (crawler/, notes.txt)" }]
---

# The 2020 Node crawler

Node, axios and cheerio, pointed at Allrecipes. A hand-written FIFO queue, 10 concurrent connections, 120 requests/min,
recursive link-following filtered to `/recipe` links, dedupe against the database, resume from a saved `latest_read_page`,
and recipes parsed from JSON-LD with HTML/microdata fallbacks. Ingredient text was cleaned with large regexes plus a
hardcoded merge list.

Weak spots (the author's own notes and the code): JSON parsed by slicing at the first `;`; exact `@type == 'Recipe'` match;
failed URLs re-enqueued forever; a recipe and its ingredients saved in separate steps, so a stop mid-crawl leaves partial
recipes; brittle regexes (cheddar cheese mapped to an empty name); no tests, no robots.txt, no User-Agent.
