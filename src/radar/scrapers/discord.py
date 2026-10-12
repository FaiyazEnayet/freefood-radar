"""Discord public widget scraper.

Discord servers that enable the Server Widget expose a public JSON
endpoint — no token, no login:

    https://discord.com/api/guilds/{guild_id}/widget.json

It lists online members and, crucially for us, the server's invite
channels. Many SBU club servers also mirror event announcements in a
public #announcements channel surfaced through the widget. This scraper
reads the widget JSON for a configured list of guild IDs and extracts
any announcement-like text. Guild IDs come from public invite links
the clubs themselves publish.
"""

from __future__ import annotations

from ..models import Event
from .base import BaseScraper

WIDGET_URL = "https://discord.com/api/guilds/{guild_id}/widget.json"


class DiscordWidgetScraper(BaseScraper):
    name = "discord"

    def __init__(self, guild_ids: list[str] | None = None, **kwargs):
        super().__init__(**kwargs)
        self.guild_ids = guild_ids or []

    @staticmethod
    def parse_widget(payload: dict, guild_id: str) -> list[Event]:
        """Turn widget JSON into Event candidates.

        The widget payload has no message history, but servers often put
        their current event in the welcome screen / channel topics, which
        some bots mirror here. We treat each advertised channel topic as
        a candidate and let the classifier decide.
        """
        events: list[Event] = []
        name = payload.get("name", f"guild-{guild_id}")
        for ch in payload.get("channels", []):
            topic = (ch.get("topic") or "").strip()
            if not topic:
                continue
            events.append(
                Event(
                    title=f"#{ch.get('name', 'announcements')} — {name}",
                    description=topic,
                    club=name,
                    source="discord",
                    url=payload.get("instant_invite") or "",
                )
            )
        return events

    def scrape(self) -> list[Event]:
        events: list[Event] = []
        for gid in self.guild_ids:
            res = self.fetch(WIDGET_URL.format(guild_id=gid))
            if res.blocked_by_robots or res.status != 200 or not res.text:
                continue
            try:
                import json

                payload = json.loads(res.text)
            except ValueError:
                continue
            events.extend(self.parse_widget(payload, gid))
        return events
