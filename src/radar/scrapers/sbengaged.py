"""Public SB Engaged calendar ingestion. No login, cookies or private API.

The feed URL is advertised by https://sbengaged.stonybrook.edu/events.
Locations withheld by the publisher remain withheld. Calendar occurrences
are deduplicated by UID; cancellation and timezone information are retained.
"""
from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from hashlib import sha256
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup
from icalendar import Calendar

FEED_URL = "https://sbengaged.stonybrook.edu/ical/stonybrook/ical_stonybrook.ics"
LISTING_URL = "https://sbengaged.stonybrook.edu/events"
NY = ZoneInfo("America/New_York")
UA = "freefood-radar/0.2 (+https://github.com/FaiyazEnayet/freefood-radar)"
MAX_BYTES = 20 * 1024 * 1024
ALLOWED_HOSTS = {"sbengaged.stonybrook.edu", "static-prod-us-east-1.campusgroups.com"}


class FeedError(RuntimeError):
    pass


def _public_url(value: str) -> str:
    parsed = urlparse(value)
    return value if parsed.scheme == "https" and parsed.hostname == "sbengaged.stonybrook.edu" else ""


def _plain(value) -> str:
    return BeautifulSoup(str(value or ""), "html.parser").get_text(" ", strip=True)


def _date(value) -> tuple[datetime, bool, bool]:
    if isinstance(value, datetime):
        floating = value.tzinfo is None
        return value.replace(tzinfo=NY) if floating else value, False, floating
    if isinstance(value, date):
        return datetime.combine(value, time.min, NY), True, False
    raise ValueError("missing or invalid DTSTART")


def parse_calendar(raw: bytes, now: datetime, days: int = 14) -> tuple[list[dict], dict]:
    """Select not-ended occurrences in [now, now + days], newest UID wins.

    An unsupported recurrence is a source-contract failure, not an excuse to
    silently drop occurrences. The currently published feed expands them.
    """
    if now.tzinfo is None or not 1 <= days <= 90:
        raise ValueError("timezone-aware now and days in 1..90 required")
    if len(raw) > MAX_BYTES or b"BEGIN:VCALENDAR" not in raw[:256]:
        raise FeedError("Response is not a supported public calendar")
    try:
        cal = Calendar.from_ical(raw)
    except Exception as exc:
        raise FeedError("Invalid calendar data") from exc
    if str(cal.name) != "VCALENDAR":
        raise FeedError("Calendar envelope missing")
    components = cal.walk("VEVENT")
    if len(components) > 50000:
        raise FeedError("Unexpected event volume; inspect source contract")
    newest = {}
    rejected = 0
    for item in components:
        if item.get("RRULE") or item.get("RECURRENCE-ID"):
            raise FeedError("Recurring-event schema changed; occurrence expansion needs review")
        uid = str(item.get("UID", "")).strip()
        if not uid:
            rejected += 1
            continue
        modified = item.decoded("LAST-MODIFIED", datetime.min.replace(tzinfo=timezone.utc))
        if not isinstance(modified, datetime):
            modified = datetime.min.replace(tzinfo=timezone.utc)
        modified = modified.replace(tzinfo=timezone.utc) if modified.tzinfo is None else modified
        key = (modified, int(item.get("SEQUENCE", 0)))
        if uid not in newest or key >= newest[uid][0]:
            newest[uid] = (key, item)
    events = []
    cancelled = 0
    until = now + timedelta(days=days)
    for uid, (_, item) in newest.items():
        if str(item.get("STATUS", "")).upper() == "CANCELLED":
            cancelled += 1
            continue
        try:
            start, all_day, floating = _date(item.decoded("DTSTART"))
            end_value = item.decoded("DTEND", None)
            end = _date(end_value)[0] if end_value is not None else (start + timedelta(days=1) if all_day else None)
            if end is not None and end < start:
                raise ValueError("negative duration")
            if start >= until or (end or start) <= now:
                continue
        except (ValueError, TypeError, KeyError):
            rejected += 1
            continue
        title = _plain(item.get("SUMMARY"))
        url = _public_url(str(item.get("URL", "")))
        if not title or not url:
            rejected += 1
            continue
        location = _plain(item.get("LOCATION"))
        withheld = "sign in" in location.lower() or "log in" in location.lower()
        organizer = item.get("ORGANIZER")
        club = _plain(organizer.params.get("CN", "")) if organizer is not None else ""
        updated = item.decoded("LAST-MODIFIED", None)
        events.append(dict(
            id=sha256(uid.encode()).hexdigest()[:20], uid=uid, title=title,
            description=_plain(item.get("DESCRIPTION")), club=club,
            location="" if withheld else location,
            location_visibility="withheld_by_source" if withheld else ("public" if location else "not_listed"),
            starts_at=start.isoformat(), ends_at=end.isoformat() if end else None,
            all_day=all_day, timezone="America/New_York", floating_time_assumed=floating,
            url=url, source="sbengaged", source_updated_at=updated.isoformat() if isinstance(updated, datetime) else None,
            food_probability=None, score=None, food_keywords=[], food_verified=False,
        ))
    if rejected and rejected > max(3, len(components) * .05):
        raise FeedError(f"Too many invalid events ({rejected}); keeping the last good snapshot")
    return sorted(events, key=lambda x: (datetime.fromisoformat(x["starts_at"]).timestamp(), x["id"])), dict(
        source_components=len(components), unique_uids=len(newest), cancelled=cancelled,
        invalid_records=rejected, selected_events=len(events), source_sha256=sha256(raw).hexdigest(),
        window_start=now.isoformat(), window_end=until.isoformat(),
    )


def fetch_calendar(session=None) -> tuple[bytes, dict]:
    """One robots read and one bounded public-feed read with timeouts."""
    session = session or requests.Session()
    headers = {"User-Agent": UA}
    robots = session.get("https://sbengaged.stonybrook.edu/robots.txt", headers=headers, timeout=(10, 30))
    if robots.status_code != 200:
        raise FeedError("Could not verify public-source robots policy")
    policy = RobotFileParser()
    policy.parse(robots.text.splitlines())
    if not policy.can_fetch(UA, FEED_URL):
        raise FeedError("Calendar fetching is disallowed by the public robots policy")
    with session.get(FEED_URL, headers=headers, timeout=(10, 45), stream=True, allow_redirects=True) as response:
        if response.status_code != 200:
            raise FeedError(f"Calendar returned HTTP {response.status_code}")
        chain = list(response.history) + [response]
        if any(urlparse(r.url).scheme != "https" or urlparse(r.url).hostname not in ALLOWED_HOSTS for r in chain):
            raise FeedError("Unexpected feed redirect; inspect publisher configuration")
        if "text/calendar" not in response.headers.get("Content-Type", "").lower():
            raise FeedError("Source returned a non-calendar page, possibly a login screen")
        raw = bytearray()
        for chunk in response.iter_content(65536):
            raw.extend(chunk)
            if len(raw) > MAX_BYTES:
                raise FeedError("Calendar exceeds configured size limit")
        return bytes(raw), dict(url=FEED_URL, final_url=response.url, etag=response.headers.get("ETag"),
                                last_modified=response.headers.get("Last-Modified"))
