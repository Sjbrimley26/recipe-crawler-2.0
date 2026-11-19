"""Crawl loop: bounded frontier, depth/page limits, resume from a saved state file.

The loop is storage-agnostic: `on_recipe(url, recipe_dict)` is called for each page with a Recipe;
Postgres storage plugs in there. State (queue, seen set, page count) is saved after every page,
so a killed run resumes where it stopped.
"""
from __future__ import annotations

import json
import os
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Protocol
from urllib.parse import urldefrag, urljoin, urlsplit

from bs4 import BeautifulSoup

from .jsonld import extract_recipe


class Getter(Protocol):
    def get(self, url: str) -> str | None: ...


@dataclass
class Frontier:
    queue: deque = field(default_factory=deque)  # (url, depth)
    seen: set = field(default_factory=set)
    pages: int = 0

    def push(self, url: str, depth: int) -> bool:
        if url in self.seen:
            return False
        self.seen.add(url)
        self.queue.append((url, depth))
        return True

    def save(self, path: Path) -> None:
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps({"queue": list(self.queue), "seen": sorted(self.seen), "pages": self.pages}))
        os.replace(tmp, path)  # atomic: a crash never leaves half a state file

    @classmethod
    def load(cls, path: Path) -> "Frontier":
        d = json.loads(path.read_text())
        return cls(deque((u, n) for u, n in d["queue"]), set(d["seen"]), d["pages"])


def links(html: str, base: str, same_host: bool = True) -> list[str]:
    host = urlsplit(base).netloc
    out = []
    for a in BeautifulSoup(html, "html.parser").find_all("a", href=True):
        u = urldefrag(urljoin(base, a["href"]))[0]
        p = urlsplit(u)
        if p.scheme in ("http", "https") and (not same_host or p.netloc == host):
            out.append(u)
    return out


def crawl(
    seeds: list[str],
    fetcher: Getter,
    on_recipe: Callable[[str, dict], None],
    state_path: Path | None = None,
    max_pages: int = 50,
    max_depth: int = 2,
) -> Frontier:
    if state_path and state_path.exists():
        fr = Frontier.load(state_path)
    else:
        fr = Frontier()
        for s in seeds:
            fr.push(s, 0)
    while fr.queue and fr.pages < max_pages:
        url, depth = fr.queue.popleft()
        html = fetcher.get(url)
        fr.pages += 1
        if html is not None:
            recipe = extract_recipe(html)
            if recipe is not None:
                on_recipe(url, recipe)
            elif depth < max_depth:
                for u in links(html, url):
                    fr.push(u, depth + 1)
        if state_path:
            fr.save(state_path)
    return fr
