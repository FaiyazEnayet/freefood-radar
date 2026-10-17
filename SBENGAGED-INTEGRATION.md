# Public SB Engaged integration

The event page at https://sbengaged.stonybrook.edu/events advertises the public
ICS feed used by this integration. No NetID, password, browser cookies, private
mobile API or paid API is used. The source redirects its calendar to the official
CampusGroups static host. The old CampusGroups HTML scraper remains a legacy
adapter; it is not the production source for this dashboard.

## Run locally

```sh
python -m pip install -r requirements.txt
python scripts/refresh_sbengaged.py --days 14
python -m pytest tests/test_sbengaged.py -q
```

The refresh writes `data/sbengaged-events.json`, `data/sbengaged-status.json`
and the self-contained `docs/dashboard.html`. Open the HTML directly. A downloaded
copy is a dated snapshot and does not update itself.

The daily GitHub Actions workflow runs at **11:17 UTC**, approximately 7:17 a.m.
New York during daylight saving time and 6:17 a.m. in standard time. GitHub can
delay or disable scheduled jobs, including inactive public-repository schedules.
It also runs on integration-code updates and supports Run workflow. The workflow
must be enabled on the default branch and allowed to write repository contents.
It does not deploy a server or change Pages configuration. A repository already
configured to serve docs/ may publish the new HTML through its existing settings.

## Data contract

- Includes not-ended public occurrences starting before a rolling 14-day cutoff.
- Uses UTC/TZID timestamps and displays America/New_York. All-day events retain
  their date semantics. Floating times, if received, are flagged as assumed NY.
- Deduplicates by source UID, retaining the newest modification/sequence. A
  cancelled newest record removes its older occurrence.
- Public locations are retained. “Sign in to download the location” becomes an
  explicit withheld-location state. No coordinates or rooms are inferred.
- Enforces calendar content type, supported redirect hosts, response size and
  timeouts. Robots policy must be retrievable and permit the feed.
- The current feed expands recurring occurrences. If an RRULE/RECURRENCE-ID
  schema appears, refresh fails visibly rather than silently losing recurrences.
- A failed fetch, parse or scoring step preserves the last successful snapshot
  and writes a failed status. Demonstration events never replace public data.
- Records source URL, fetch time, source-body hash, window, row diagnostics,
  training-data hash, model recipe, seed and inference library version.

## Prediction limitations

The repository does not ship its classifier binary. Refresh therefore refits the
existing TF-IDF/logistic/sigmoid recipe on the original seed-7, 75% training split
of data/labeled.csv. It does not overwrite historical evaluation metrics or use
the held-out labels for this fit. Probabilities and ranking scores are computed
model outputs, not verified food offers. Historical labeled-text precision,
recall and calibration do not establish accuracy on actual SB Engaged text.
Training dependency versions are recorded; they can affect the rebuilt model.

The top-level original seeded digest remains an offline demo. The new public
dashboard uses its own public-source snapshot and never calls it a live stream.
Upcoming work: human-reviewed real-feed labels, time-split validation, cancelled
event monitoring, and source freshness alerts.

## Authentication

Public ingestion needs no login. A browser session is not permanent and is not
transferred to GitHub Actions. Withheld fields can be viewed on the official
event page after university sign-in. Automating private access requires a
university-approved interface or service identity; do not store personal
credentials or session cookies in this repository.
