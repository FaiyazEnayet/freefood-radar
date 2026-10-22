# Changelog

## Unreleased

### Fixed
- P1: the production dashboard can no longer carry seeded demonstration data.
  `portfolio_ui/renderer.py` now splits production render mode from the
  explicit offline demo mode at the generator/data-contract level:
  - Production (default) requires a valid `public_source_snapshot` payload
    (classification, schema version and per-event source validated at the
    publication boundary) or renders a marked no-snapshot status-only state
    with zero event listings. It never reads `data/seed_events.json`, never
    packages seeded event records, and replaces seeded demonstration charts
    with explicit redaction markers while keeping the separately labeled
    historical evaluation figures (classifier report, calibration) in place.
  - A snapshot containing seeded records is rejected loudly and never
    rendered (`scripts/refresh_sbengaged.py` publication check).
  - Demo generation is now explicit only: `scripts/make_dashboard.py --demo`
    writes to a non-production path (default `docs/demo-dashboard.html`) and
    refuses the production artifact path; `renderer.py --mode demo` likewise.
    Without `--demo`, `make_dashboard.py` refuses to build when no public
    snapshot exists instead of silently falling back to seeded content.
  - New regression test `test_stage3_freefood_radar_1` (8 cases) pins the
    acceptance fixtures. Full suite: 48 tests passing.
  - Note: the dashboard-side dispatch that routes a no-snapshot production
    render to the marked status-only view (instead of the demo fallback) and
    the workflow publication gate are tracked as follow-ups; no dashboard
    HTML or workflow YAML was changed in this item.
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
