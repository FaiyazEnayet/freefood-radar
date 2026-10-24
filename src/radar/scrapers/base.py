"""Shared scraping plumbing: polite fetching, robots.txt, rate limits."""

from __future__ import annotations

import time
import urllib.robotparser
from dataclasses import dataclass
from urllib.parse import urlparse

import requests

from ..models import Event

USER_AGENT = "freefood-radar-sbu/0.1 (+https://github.com/FaiyazEnayet/freefood-radar-sbu)"
DEFAULT_DELAY = 2.0  # seconds between requests to the same host


@dataclass
class FetchResult:
    url: str
    status: int
    text: str
    blocked_by_robots: bool = False


class BaseScraper:
    """Base class: polite HTTP, robots.txt checks, per-host throttling."""

    name = "base"

    def __init__(self, delay: float = DEFAULT_DELAY, timeout: int = 20):
        self.delay = delay
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT})
        self._last_fetch: dict[str, float] = {}
        self._robots: dict[str, urllib.robotparser.RobotFileParser] = {}

    # -- politeness -----------------------------------------------------
    def _robots_parser(self, url: str) -> urllib.robotparser.RobotFileParser:
        host = urlparse(url).netloc
        if host not in self._robots:
            rp = urllib.robotparser.RobotFileParser()
            rp.set_url(f"https://{host}/robots.txt")
            try:
                rp.read()
            except Exception:
                pass  # fail open: treat as allowed when robots.txt is unreadable
            self._robots[host] = rp
        return self._robots[host]

    def allowed(self, url: str) -> bool:
        return self._robots_parser(url).can_fetch(USER_AGENT, url)

    def fetch(self, url: str) -> FetchResult:
        if not self.allowed(url):
            return FetchResult(url=url, status=0, text="", blocked_by_robots=True)
        host = urlparse(url).netloc
        wait = self.delay - (time.time() - self._last_fetch.get(host, 0.0))
        if wait > 0:
            time.sleep(wait)
        try:
            resp = self.session.get(url, timeout=self.timeout)
            self._last_fetch[host] = time.time()
            return FetchResult(url=url, status=resp.status_code, text=resp.text)
        except requests.RequestException:
            self._last_fetch[host] = time.time()
            return FetchResult(url=url, status=0, text="")

    # -- interface ------------------------------------------------------
    def scrape(self) -> list[Event]:
        """Return candidate events. Must be implemented by subclasses."""
        raise NotImplementedError
