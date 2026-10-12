"""Historical analytics: who feeds people, and when."""

from __future__ import annotations

from collections import Counter
from datetime import datetime

import pandas as pd

from .models import Event

DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def top_clubs(events: list[Event], n: int = 10) -> list[tuple[str, int]]:
    counts = Counter(e.club for e in events if e.club)
    return counts.most_common(n)


def events_by_day(events: list[Event]) -> dict[str, int]:
    counts = Counter()
    for e in events:
        if e.starts_at:
            counts[DAY_NAMES[e.starts_at.weekday()]] += 1
    return {d: counts.get(d, 0) for d in DAY_NAMES}


def heatmap_matrix(events: list[Event]) -> pd.DataFrame:
    """Day-of-week x time-of-day counts (time buckets)."""
    buckets = ["Morning\n(before 11)", "Midday\n(11-2)", "Afternoon\n(2-5)",
               "Evening\n(5-9)", "Night\n(after 9)"]

    def bucket(h: int) -> str:
        if h < 11:
            return buckets[0]
        if h < 14:
            return buckets[1]
        if h < 17:
            return buckets[2]
        if h < 21:
            return buckets[3]
        return buckets[4]

    mat = pd.DataFrame(0, index=DAY_NAMES, columns=buckets)
    for e in events:
        if e.starts_at:
            mat.loc[DAY_NAMES[e.starts_at.weekday()], bucket(e.starts_at.hour)] += 1
    return mat


def food_mention_rate_by_club(events: list[Event], min_events: int = 2) -> list[tuple[str, float, int]]:
    """Clubs ranked by share of their events that mention free food."""
    total = Counter()
    food = Counter()
    for e in events:
        if not e.club:
            continue
        total[e.club] += 1
        if e.food_probability >= 0.5:
            food[e.club] += 1
    out = [
        (club, food[club] / total[club], total[club])
        for club in total
        if total[club] >= min_events
    ]
    return sorted(out, key=lambda t: t[1], reverse=True)


def summary(events: list[Event]) -> dict:
    scored = [e for e in events if e.food_probability >= 0.5]
    return {
        "n_events": len(events),
        "n_food_events": len(scored),
        "food_rate": len(scored) / len(events) if events else 0.0,
        "top_clubs": top_clubs(scored),
        "by_day": events_by_day(scored),
        "avg_confidence": (
            sum(e.food_probability for e in scored) / len(scored) if scored else 0.0
        ),
    }
