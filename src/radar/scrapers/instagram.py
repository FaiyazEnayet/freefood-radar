"""Public Instagram post scraper (documented limitation).

Instagram's public web pages require a logged-in session for reliable
access, which this project will not do (no login-gated scraping, per
the project rules). This module therefore works in two modes:

1. **Fixture / saved-HTML mode** (used by the tests and the demo): parse
   the public post HTML a club saved or shared, extracting caption text.
2. **Embed mode**: clubs can paste an instagram.com post URL and this
   module fetches only the public oEmbed-style metadata.

In practice the demo pipeline runs on SB Engaged + Discord widget data
plus the seeded dataset; this module exists so Instagram-sourced posts
can be folded in wherever a public, login-free copy is available.
"""

from __future__ import annotations

import re

from bs4 import BeautifulSoup

from ..models import Event
from .base import BaseScraper

POST_URL_RE = re.compile(r"https?://(www\.)?instagram\.com/(p|reel)/[\w\-]+/?")


class InstagramScraper(BaseScraper):
    name = "instagram"

    def __init__(self, post_urls: list[str] | None = None, **kwargs):
        super().__init__(**kwargs)
        self.post_urls = post_urls or []

    @staticmethod
    def extract_post_urls(text: str) -> list[str]:
        return POST_URL_RE.findall(text) and [
            m.group(0) for m in POST_URL_RE.finditer(text)
        ]

    @staticmethod
    def parse_post_html(html: str, url: str = "") -> Event | None:
        """Extract caption + author from a public post page's HTML."""
        soup = BeautifulSoup(html, "lxml")
        # Public pages embed the caption in og:description.
        desc = soup.select_one('meta[property="og:description"]')
        title = soup.select_one('meta[property="og:title"]')
        if not desc:
            return None
        caption = desc.get("content", "")
        # og:title is usually "<author> on Instagram: <first words>"
        club = ""
        if title:
            m = re.match(r"(.+?) on Instagram", title.get("content", ""))
            if m:
                club = m.group(1).strip().strip('"')
        return Event(
            title=caption[:80],
            description=caption,
            club=club,
            source="instagram",
            url=url,
        )

    def scrape(self) -> list[Event]:
        events: list[Event] = []
        for url in self.post_urls:
            res = self.fetch(url)
            if res.blocked_by_robots or res.status != 200 or not res.text:
                continue
            ev = self.parse_post_html(res.text, url=url)
            if ev:
                events.append(ev)
        return events
