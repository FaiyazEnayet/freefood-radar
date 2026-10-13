"""SB Engaged / CampusGroups (Corq) public events scraper.

SB Engaged (Stony Brook's club portal) runs on CampusGroups. Its public
event cards are reachable without a login; the admin calendar is not.
This scraper parses the public event listing and each event's public
detail page. If the listing ever moves behind login, scrape() returns
what it can and flags the rest. It never attempts credentialed access.
"""

from __future__ import annotations

from datetime import datetime
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from ..models import Event
from .base import BaseScraper

BASE = "https://stonybrook.campusgroups.com"
LISTING_PATHS = [
    "/events?search=",          # public listing (when not login-walled)
    "/rss/events",              # public RSS feed (when enabled)
]


class CorqScraper(BaseScraper):
    name = "corq"

    def __init__(self, max_pages: int = 3, **kwargs):
        super().__init__(**kwargs)
        self.max_pages = max_pages

    # -- parsing (pure functions, easy to unit test) --------------------
    @staticmethod
    def parse_listing(html: str, base_url: str = BASE) -> list[dict]:
        """Extract raw event dicts from a CampusGroups listing page."""
        soup = BeautifulSoup(html, "lxml")
        out: list[dict] = []
        for card in soup.select(".event-card, .event-listing-item, [data-event-id]"):
            title_el = card.select_one(".event-title, h3, h4, a.event-link")
            if not title_el:
                continue
            title = title_el.get_text(strip=True)
            link = title_el.get("href") if title_el.name == "a" else None
            if not link:
                a = card.select_one("a[href]")
                link = a.get("href") if a else None
            desc_el = card.select_one(".event-description, .event-teaser, p")
            club_el = card.select_one(".event-org, .org-name, .club-name")
            loc_el = card.select_one(".event-location, .location")
            time_el = card.select_one(".event-time, time[datetime], .date-time")
            starts_at = None
            if time_el:
                dt = time_el.get("datetime") or time_el.get_text(strip=True)
                starts_at = CorqScraper._parse_time(dt)
            out.append(
                {
                    "title": title,
                    "description": desc_el.get_text(strip=True) if desc_el else "",
                    "club": club_el.get_text(strip=True) if club_el else "",
                    "location": loc_el.get_text(strip=True) if loc_el else "",
                    "starts_at": starts_at,
                    "url": urljoin(base_url, link) if link else "",
                }
            )
        return out

    @staticmethod
    def parse_detail(html: str) -> dict:
        """Extract the full description from a public event detail page."""
        soup = BeautifulSoup(html, "lxml")
        body = soup.select_one(".event-detail-description, .event-description, #event-description")
        return {"description": body.get_text("\n", strip=True) if body else ""}

    @staticmethod
    def _parse_time(raw: str) -> datetime | None:
        for fmt in (
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M",
            "%Y-%m-%d %H:%M",
            "%m/%d/%Y %I:%M %p",
            "%B %d, %Y %I:%M %p",
        ):
            try:
                return datetime.strptime(raw.strip(), fmt)
            except (ValueError, AttributeError):
                continue
        return None

    # -- live scraping --------------------------------------------------
    def scrape(self) -> list[Event]:
        events: list[Event] = []
        for path in LISTING_PATHS:
            url = urljoin(BASE, path)
            res = self.fetch(url)
            if res.blocked_by_robots or res.status != 200 or not res.text:
                continue
            for raw in self.parse_listing(res.text)[:25]:
                ev = Event(source=self.name, **raw)
                if ev.url:  # enrich with the public detail page
                    detail = self.fetch(ev.url)
                    if detail.status == 200 and detail.text:
                        d = self.parse_detail(detail.text)
                        if d["description"]:
                            ev.description = d["description"]
                events.append(ev)
            if events or len(events) >= self.max_pages * 25:
                break
        return events
