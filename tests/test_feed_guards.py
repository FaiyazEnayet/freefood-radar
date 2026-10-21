"""FR1: success-empty and severe feed-shrink guards; no network needed.

A syntactically valid feed must not silently replace a healthy snapshot
with an empty or drastically smaller one. Suspicious count changes keep
the last good snapshot until a second, identical observation confirms
them; a feed whose components are all cancelled, expired or outside the
window is a verified zero and is accepted immediately.
"""
from datetime import datetime, timezone
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from radar.live import refresh
from radar.scrapers.sbengaged import parse_calendar

NOW = datetime(2026, 10, 17, 12, tzinfo=timezone.utc)
FIXTURES = Path(__file__).resolve().parent / 'fixtures'
SCORER = lambda rows, root: {'test_model': True}


def fixture(name):
    return (FIXTURES / name).read_bytes()


def seed_snapshot(tmp_path, name='sbengaged_full.ics'):
    assert refresh(tmp_path, now=NOW, fetcher=lambda: (fixture(name), {}), scorer=SCORER)
    return json.loads((tmp_path / 'data/sbengaged-events.json').read_text())


def status_of(tmp_path):
    return json.loads((tmp_path / 'data/sbengaged-status.json').read_text())


def snapshot_of(tmp_path):
    return json.loads((tmp_path / 'data/sbengaged-events.json').read_text())


def test_verified_empty_fixture_parses_to_zero_selected(tmp_path):
    _, stats = parse_calendar(fixture('sbengaged_verified_empty.ics'), NOW)
    assert stats['source_components'] == 3
    assert stats['cancelled'] == 1
    assert stats['selected_events'] == 0


def test_empty_feed_does_not_replace_full_snapshot(tmp_path):
    good = seed_snapshot(tmp_path)
    assert len(good['events']) == 30
    assert refresh(tmp_path, now=NOW, fetcher=lambda: (fixture('sbengaged_empty.ics'), {}),
                   scorer=SCORER) is False
    assert snapshot_of(tmp_path) == good
    status = status_of(tmp_path)
    assert status['success'] is False
    assert status['count_change'] == 'empty_suspect'
    assert status['previous_selected_events'] == 30
    assert status['selected_events'] == 0


def test_repeated_empty_feed_is_confirmed_and_accepted(tmp_path):
    seed_snapshot(tmp_path)
    feed = lambda: (fixture('sbengaged_empty.ics'), {})
    assert refresh(tmp_path, now=NOW, fetcher=feed, scorer=SCORER) is False
    assert refresh(tmp_path, now=NOW, fetcher=feed, scorer=SCORER) is True
    assert snapshot_of(tmp_path)['events'] == []
    assert status_of(tmp_path)['count_change'] == 'empty_confirmed'


def test_verified_empty_feed_replaces_snapshot_immediately(tmp_path):
    seed_snapshot(tmp_path)
    assert refresh(tmp_path, now=NOW, fetcher=lambda: (fixture('sbengaged_verified_empty.ics'), {}),
                   scorer=SCORER) is True
    assert snapshot_of(tmp_path)['events'] == []
    status = status_of(tmp_path)
    assert status['success'] is True
    assert status['count_change'] == 'verified_empty'


def test_severe_shrink_keeps_last_good_snapshot(tmp_path):
    good = seed_snapshot(tmp_path)
    assert refresh(tmp_path, now=NOW, fetcher=lambda: (fixture('sbengaged_shrunk.ics'), {}),
                   scorer=SCORER) is False
    assert snapshot_of(tmp_path) == good
    status = status_of(tmp_path)
    assert status['success'] is False
    assert status['count_change'] == 'severe_shrink_suspect'
    assert status['previous_selected_events'] == 30
    assert status['selected_events'] == 5


def test_repeated_shrink_is_confirmed_and_accepted(tmp_path):
    seed_snapshot(tmp_path)
    feed = lambda: (fixture('sbengaged_shrunk.ics'), {})
    assert refresh(tmp_path, now=NOW, fetcher=feed, scorer=SCORER) is False
    assert refresh(tmp_path, now=NOW, fetcher=feed, scorer=SCORER) is True
    assert len(snapshot_of(tmp_path)['events']) == 5
    assert status_of(tmp_path)['count_change'] == 'severe_shrink_confirmed'


def test_changing_shrink_is_not_confirmed(tmp_path):
    seed_snapshot(tmp_path)
    assert refresh(tmp_path, now=NOW, fetcher=lambda: (fixture('sbengaged_shrunk.ics'), {}),
                   scorer=SCORER) is False
    # A different shrunk result (empty feed) does not confirm the first one.
    assert refresh(tmp_path, now=NOW, fetcher=lambda: (fixture('sbengaged_empty.ics'), {}),
                   scorer=SCORER) is False
    assert len(snapshot_of(tmp_path)['events']) == 30


def test_moderate_shrink_is_accepted_and_labelled(tmp_path):
    seed_snapshot(tmp_path)
    assert refresh(tmp_path, now=NOW, fetcher=lambda: (fixture('sbengaged_moderate.ics'), {}),
                   scorer=SCORER) is True
    assert len(snapshot_of(tmp_path)['events']) == 20
    status = status_of(tmp_path)
    assert status['count_change'] == 'shrank'
    assert status['previous_selected_events'] == 30
    assert status['selected_events'] == 20
