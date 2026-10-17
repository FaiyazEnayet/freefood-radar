<p align="center"><img src="docs/readme-banner.svg" alt="Freefood-Radar: Public campus events, ranked with food evidence" width="1200"></p>

[![Tests](https://github.com/FaiyazEnayet/freefood-radar/actions/workflows/ci.yml/badge.svg)](https://github.com/FaiyazEnayet/freefood-radar/actions/workflows/ci.yml) [![License: MIT](https://img.shields.io/badge/license-MIT-007EC6)](LICENSE) ![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-3776AB) ![Built with scikit learn + public ICS](https://img.shields.io/badge/built%20with-scikit%20learn%20%2B%20public%20ICS-555555) [![Interactive demo](https://img.shields.io/badge/demo-interactive-4C9D39)](https://faiyazenayet.github.io/freefood-radar/docs/dashboard.html)

<p align="center"><a href="https://faiyazenayet.github.io/freefood-radar/docs/dashboard.html"><b>Open interactive demo</b></a> · <a href="docs/dashboard.html">HTML file</a> · <a href="#method">Method</a> · <a href="#run-locally">Run locally</a> · <a href="#limitations">Limitations</a></p>

# Freefood-Radar

Freefood-Radar reads SB Engaged’s public calendar and ranks possible food opportunities. Event facts stay attached to their official source; food availability remains an unverified model prediction.

**Python · public calendar ingestion · calibrated text classification**

[![Freefood-Radar demo](docs/demo.gif?v=data-20261017)](https://faiyazenayet.github.io/freefood-radar/docs/dashboard.html)


## Explore

- Search official public events, inspect source descriptions and open organizer event links.
- Filter model food candidates, all public events or locally saved events, with date filters and pagination.
- Inspect source freshness, withheld locations and historical model evaluation without confusing them with live-feed accuracy.

## Method

The public ICS calendar is filtered to not-ended events in a rolling 14-day window. UID, modification and cancellation handling produce a dated source snapshot. The existing TF-IDF/logistic classifier supplies probabilities, and transparent food-quality weights supply the ranking.

## Evidence at a glance

| Scope | Recorded result or contract |
| :--- | :--- |
| Source | Official public SB Engaged calendar; no login required |
| Refresh | Daily workflow at 11:17 UTC, plus manual refresh |
| Historical labeled-text test | 40 examples; precision 89.5%; recall 85.0% |
| Live-feed validation | Food-availability precision and calibration are not yet established |

## Run locally


```sh
python -m pip install -r requirements.txt
python -m pip install -r portfolio_ui/requirements.txt
python scripts/refresh_sbengaged.py --days 14
python -m pytest tests -q
```

## Technical design

The ingestion layer reads the public calendar advertised by SB Engaged. It filters a rolling time window, handles source identity and cancellation state, and records fetch provenance. Text is scored by the repository’s existing small-data classifier. The browser displays the dated snapshot and stores saved event IDs locally.

```mermaid
flowchart LR
  N0["Public SB Engaged calendar"] --> N1["Validate filter and deduplicate"]
  N1["Validate filter and deduplicate"] --> N2["Text classifier"]
  N2["Text classifier"] --> N3["Inspectable food ranking"]
  N3["Inspectable food ranking"] --> N4["Dated HTML snapshot"]
  N5["Daily workflow"] --> N0["Public SB Engaged calendar"]
```

## Evaluation protocol

The original labeled-text test is separate from the public feed. Its precision and recall describe that held-out sample, not verified campus food availability. Public-source events can still be cancelled, restricted or have locations withheld behind sign-in. The UI links back to the source rather than fabricating missing details.

![Historical held-out text-classification results](docs/results.png)

An official listing establishes that the event was published, not that food is free or available when a student arrives. The model probability and food-quality weight are ranking aids. Source freshness and organizer details remain necessary for a useful decision.

## Code and data

`src/radar/scrapers/sbengaged.py` parses the public calendar. `live.py` validates and scores snapshots. `data/sbengaged-status.json` records refresh health. [Integration notes](SBENGAGED-INTEGRATION.md) document the contract and daily workflow.


## Limitations

- Public coverage excludes private events and locations hidden behind university sign-in.
- The classifier was trained on a small SBU-style labeled set, not verified food outcomes from this feed.
- A downloaded HTML is a dated snapshot. Failed refreshes retain the last good source data and display the failure. No demonstration events are substituted.

## License

[MIT](LICENSE). Third-party datasets, libraries and fonts retain their own terms.
