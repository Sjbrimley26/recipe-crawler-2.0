"""Polite fetching: real User-Agent, robots.txt, per-host rate limit, bounded retries."""
from __future__ import annotations

import time
import urllib.robotparser
from urllib.parse import urlsplit

import httpx

UA = "recipe-scraper/0.1 (personal project; contact: spencerbcarpentry.com)"


class Fetcher:
    def __init__(self, min_interval: float = 2.0, max_retries: int = 3, client: httpx.Client | None = None):
        self.min_interval = min_interval
        self.max_retries = max_retries
        self.client = client or httpx.Client(headers={"User-Agent": UA}, timeout=20, follow_redirects=True)
        self._last = 0.0
        self._robots: dict[str, urllib.robotparser.RobotFileParser] = {}

    def allowed(self, url: str) -> bool:
        host = "{0.scheme}://{0.netloc}".format(urlsplit(url))
        rp = self._robots.get(host)
        if rp is None:
            rp = urllib.robotparser.RobotFileParser()
            try:
                r = self.client.get(host + "/robots.txt")
                rp.parse(r.text.splitlines() if r.status_code == 200 else [])
            except httpx.HTTPError:
                rp.parse([])
            self._robots[host] = rp
        return rp.can_fetch(UA, url)

    def get(self, url: str) -> str | None:
        """Return HTML, or None if disallowed / permanently failed. Never loops forever."""
        if not self.allowed(url):
            return None
        for attempt in range(self.max_retries):
            wait = self.min_interval - (time.monotonic() - self._last)
            if wait > 0:
                time.sleep(wait)
            self._last = time.monotonic()
            try:
                r = self.client.get(url)
            except httpx.HTTPError:
                r = None
            if r is not None and r.status_code == 200:
                return r.text
            if r is not None and r.status_code in (403, 404, 410):
                return None  # retrying will not help
            time.sleep(2 ** attempt)  # 429 / 5xx / network: back off
        return None
