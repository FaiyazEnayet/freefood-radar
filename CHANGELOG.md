# Changelog

## Unreleased

### Fixed
- FR1: a syntactically valid but empty feed, or a severe drop in the
  selected-event count, can no longer silently replace the last good SB
  Engaged snapshot as a successful refresh. `refresh` in `src/radar/live.py`
  now classifies every count change (`initial`, `stable`, `grew`, `shrank`,
  `verified_empty`, `empty_suspect`, `severe_shrink_suspect`, and
  `_confirmed` variants) and records the state plus previous/current counts
  in `data/sbengaged-status.json` and the snapshot diagnostics.
  - A feed whose components are all cancelled, expired or outside the
    window is a verified zero and replaces the snapshot immediately.
  - A feed with zero components, or a drop below half of a snapshot with
    at least 20 selected events, fails the refresh and keeps the last good
    snapshot; it is accepted only when a second, identical observation
    (same selected count, same source hash) confirms it.
  - `parse_calendar` diagnostics now also report `out_of_window`, so a
    verified zero can be told apart from a contract problem.
  - New fixtures (`tests/fixtures/sbengaged_*.ics`) and 8 refresh-level
    tests in `tests/test_feed_guards.py` cover both failure modes.
    Full suite: 40 tests passing.
