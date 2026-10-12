"""Digest, stats, features, and watchlist tests."""

import os
import sys
from datetime import datetime

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from radar import digest as digest_mod
from radar import features, stats as stats_mod
from radar import watchlist as watchlist_mod
from radar.classifier import load_model, train
from radar.models import Event


@pytest.fixture(scope="module")
def model():
    return train()["model"]


def _ev(title, desc, club="Test Club", hour=12, prob=None):
    e = Event(title=title, description=desc, club=club, location="SAC",
              starts_at=datetime(2026, 10, 12, hour), source="test")
    if prob is not None:
        e.food_probability = prob
        v, q, kw = features.expected_value(prob, e.text())
        e.score = v
        e.food_keywords = kw
    return e


def test_expected_value_ranking(model):
    events = [
        _ev("Pizza Party", "Free pizza for everyone!"),
        _ev("Budget Meeting", "No food served."),
    ]
    ranked = digest_mod.rank(digest_mod.score_events(events, model))
    assert len(ranked) == 1
    assert ranked[0].title == "Pizza Party"
    assert ranked[0].score > 0


def test_digest_renders_markdown(model):
    events = [_ev("Pizza Party", "Free pizza for everyone!")]
    text, ranked = digest_mod.build_digest(events, model)
    assert "# Free Food Radar" in text
    assert "Pizza Party" in text


def test_quality_signals():
    q_pizza, kw = features.quality_score("Free pizza and wings for all!")
    q_snack, _ = features.quality_score("Light refreshments will be served.")
    assert q_pizza > q_snack
    assert "pizza" in kw


def test_free_food_keywords():
    kws = features.free_food_keywords("Free pizza! Food will be provided.")
    assert "free pizza" in kws
    assert "food will be provided" in kws


def test_stats_top_clubs():
    events = [
        _ev("A", "x", club="CS Club", prob=0.9),
        _ev("B", "x", club="CS Club", prob=0.8),
        _ev("C", "x", club="Chess Club", prob=0.9),
        _ev("D", "x", club="Chess Club", prob=0.1),
    ]
    top = stats_mod.top_clubs([e for e in events if e.food_probability >= 0.5])
    assert top[0][0] == "CS Club"
    rates = stats_mod.food_mention_rate_by_club(events)
    assert rates[0][0] == "CS Club"  # 2/2 = 100%


def test_heatmap_matrix_shape():
    events = [_ev("A", "x", hour=h) for h in (9, 12, 18, 22)]
    for e in events:
        e.food_probability = 0.9
    mat = stats_mod.heatmap_matrix(events)
    assert mat.shape == (7, 5)
    assert mat.values.sum() == 4


def test_watchlist_alerts():
    events = [_ev("Pizza Night", "Free pizza for all!", prob=0.9),
              _ev("Sushi Social", "Free sushi tasting!", prob=0.85),
              _ev("Budget Talk", "No food.", prob=0.1)]
    alerts = watchlist_mod.check(events, ["pizza", "ramen"])
    assert len(alerts) == 1
    assert alerts[0].food == "pizza"
    assert "pizza" in alerts[0].reason


def test_watchlist_render():
    events = [_ev("Pizza Night", "Free pizza for all!", prob=0.9)]
    alerts = watchlist_mod.check(events, ["pizza"])
    html = watchlist_mod.render_alerts(alerts)
    assert "Pizza" in html
    assert watchlist_mod.render_alerts([]).startswith("No watchlist")


def test_event_serialization_roundtrip():
    e = _ev("T", "D", hour=15)
    d = e.to_dict()
    e2 = Event.from_dict(d)
    assert e2.title == "T"
    assert e2.starts_at == e.starts_at
