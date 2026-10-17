"""Public-source scrapers. Every scraper only touches public pages, honors
robots.txt, and rate-limits itself. Nothing here needs a login."""

from .base import BaseScraper, FetchResult
from .corq import CorqScraper
from .discord import DiscordWidgetScraper
from .instagram import InstagramScraper

__all__ = [
    "BaseScraper",
    "FetchResult",
    "CorqScraper",
    "DiscordWidgetScraper",
    "InstagramScraper",
]

from .sbengaged import fetch_calendar, parse_calendar
