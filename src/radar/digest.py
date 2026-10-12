"""Daily digest: score events, rank by expected value, render markdown."""

from __future__ import annotations

import os
from datetime import date, datetime

from . import features
from .models import Event

HERE = os.path.dirname(os.path.abspath(__file__))


def score_events(events: list[Event], model) -> list[Event]:
    """Attach food_probability, keywords, and expected-value score."""
    from .classifier import predict_proba

    texts = [e.text() for e in events]
    probas = predict_proba(model, texts) if texts else []
    for ev, p in zip(events, probas):
        ev.food_probability = float(p)
        ev_value, quality, kw = features.expected_value(float(p), ev.text())
        ev.score = float(ev_value)
        ev.food_keywords = kw + features.free_food_keywords(ev.text())
        ev.food_keywords = sorted(set(ev.food_keywords))
    return events


def rank(events: list[Event], min_prob: float = 0.5) -> list[Event]:
    """Keep likely free-food events, ranked by expected value."""
    kept = [e for e in events if e.food_probability >= min_prob]
    return sorted(kept, key=lambda e: e.score, reverse=True)


def render_digest(events: list[Event], day: date | None = None) -> str:
    day = day or date.today()
    lines = [
        f"# Free Food Radar — {day.strftime('%A, %B %d, %Y')}",
        "",
        f"{len(events)} likely free-food events, ranked by expected value "
        "(classifier confidence x food quality).",
        "",
    ]
    for i, e in enumerate(events, 1):
        when = e.starts_at.strftime("%I:%M %p") if e.starts_at else "time TBA"
        where = e.location or "location TBA"
        kw = ", ".join(e.food_keywords[:5]) if e.food_keywords else "free food"
        lines += [
            f"## {i}. {e.title}",
            f"**{e.club}** · {where} · {when} · "
            f"confidence {e.food_probability:.0%} · expected value {e.score:.2f}",
            "",
            f"{e.description[:280]}",
            "",
            f"_Signals: {kw}_",
            "",
        ]
    lines.append("_Scores come from the calibrated classifier; see the dashboard "
                 "for precision/recall._")
    return "\n".join(lines)


def build_digest(events: list[Event], model, day: date | None = None,
                 min_prob: float = 0.5) -> tuple[str, list[Event]]:
    scored = score_events(events, model)
    ranked = rank(scored, min_prob=min_prob)
    return render_digest(ranked, day=day), ranked
