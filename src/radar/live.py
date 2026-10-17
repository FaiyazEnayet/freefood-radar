"""Refresh a public-source snapshot; never replace a failed fetch with demo data."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import os

from .scrapers.sbengaged import FEED_URL, LISTING_URL, fetch_calendar, parse_calendar


def atomic_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf8")
    os.replace(temp, path)


def score_snapshot(events: list[dict], root: Path) -> dict:
    """Refit the existing model recipe on its original seed-7 training split.

    No old model artifact is shipped in the repo. Do not overwrite historical
    metrics.json or claim its held-out accuracy measures these live texts.
    """
    import sklearn
    from sklearn.model_selection import train_test_split
    from .classifier import build_pipeline, load_labeled
    from .models import Event
    from .digest import score_events
    path = root / "data/labeled.csv"
    labeled = load_labeled(str(path))
    texts, _, labels, _ = train_test_split(labeled.text.tolist(), labeled.label.tolist(),
                                         test_size=.25, random_state=7, stratify=labeled.label.tolist())
    model = build_pipeline()
    model.fit(texts, labels)
    scored = score_events([Event.from_dict(e) for e in events], model)
    for row, prediction in zip(events, scored):
        row.update(food_probability=prediction.food_probability, score=prediction.score,
                   food_keywords=prediction.food_keywords)
    return dict(recipe="Repository TF-IDF + logistic regression + sigmoid calibration, cv=3",
                seed=7, training_rows=len(texts), labeled_rows=len(labeled),
                labeled_sha256=hashlib.sha256(path.read_bytes()).hexdigest(), sklearn_version=sklearn.__version__,
                validation="Historical labeled-text evaluation is not validated live-feed precision/recall")


def refresh(root: Path, days: int = 14, now=None, fetcher=fetch_calendar, scorer=score_snapshot) -> bool:
    root = Path(root)
    now = now or datetime.now(timezone.utc)
    snapshot_path = root / "data/sbengaged-events.json"
    status_path = root / "data/sbengaged-status.json"
    previous = json.loads(snapshot_path.read_text(encoding="utf8")) if snapshot_path.exists() else None
    status = dict(last_attempt_at=now.isoformat(), success=False,
                  last_successful_fetch_at=previous.get("fetched_at") if previous else None)
    try:
        raw, http = fetcher()
        events, diagnostics = parse_calendar(raw, now, days)
        model = scorer(events, root)
        payload = dict(schema_version=1, classification="public_source_snapshot", fetched_at=now.isoformat(),
                       source={"name": "SB Engaged public calendar", "url": FEED_URL, "listing_url": LISTING_URL, **http},
                       coverage="Public calendar only; private events and withheld locations are unavailable",
                       model=model, diagnostics=diagnostics, events=events)
        atomic_json(snapshot_path, payload)
        status.update(success=True, last_successful_fetch_at=now.isoformat(), error=None)
    except Exception as exc:
        # Deliberately keep the last good source data, with explicit failed status.
        status["error"] = f"{type(exc).__name__}: {exc}"
    atomic_json(status_path, status)
    return status["success"]
