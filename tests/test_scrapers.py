"""Scraper tests: parse fixtures, never hit the network."""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from radar.scrapers import CorqScraper, DiscordWidgetScraper, InstagramScraper
from radar.scrapers.base import BaseScraper

FIX = os.path.join(os.path.dirname(__file__), "fixtures")


def test_corq_parses_listing_fixture():
    html = open(os.path.join(FIX, "corq_events.html")).read()
    events = CorqScraper.parse_listing(html)
    assert len(events) == 2
    assert events[0]["title"] == "GBM: Free Pizza Night"
    assert events[0]["club"] == "CS Club"
    assert events[0]["location"] == "SAC 302"
    assert "pizza" in events[0]["description"].lower()
    assert events[0]["url"].endswith("/event/1")
    assert events[0]["starts_at"] is not None
    assert events[1]["title"] == "Budget Planning Meeting"


def test_corq_parses_detail_fixture():
    html = '<div class="event-description">Free tacos!\nLine two.</div>'
    d = CorqScraper.parse_detail(html)
    assert "Free tacos!" in d["description"]


def test_discord_parses_widget_fixture():
    payload = json.load(open(os.path.join(FIX, "discord_widget.json")))
    events = DiscordWidgetScraper.parse_widget(payload, "123456789")
    # Only channels with non-empty topics become candidates.
    assert len(events) == 2
    assert events[0].club == "SBU Esports Club"
    assert "free pizza" in events[0].description.lower()
    assert all(e.source == "discord" for e in events)


def test_instagram_parses_post_fixture():
    html = open(os.path.join(FIX, "instagram_post.html")).read()
    ev = InstagramScraper.parse_post_html(html, url="https://instagram.com/p/x")
    assert ev is not None
    assert "tacos" in ev.description.lower()
    assert ev.club == "SBU Taco Club"
    assert ev.source == "instagram"


def test_instagram_extracts_post_urls():
    text = "See https://www.instagram.com/p/AbC123/ and https://instagram.com/reel/XyZ9/"
    urls = InstagramScraper.extract_post_urls(text)
    assert len(urls) == 2


def test_base_respects_robots_block(monkeypatch):
    s = BaseScraper()
    monkeypatch.setattr(s, "allowed", lambda url: False)
    res = s.fetch("https://example.com/x")
    assert res.blocked_by_robots is True
    assert res.text == ""


def test_base_fetch_handles_errors(monkeypatch):
    import requests

    s = BaseScraper(delay=0)
    monkeypatch.setattr(s, "allowed", lambda url: True)

    def boom(*a, **k):
        raise requests.ConnectionError("down")

    monkeypatch.setattr(s.session, "get", boom)
    res = s.fetch("https://example.com/x")
    assert res.status == 0
