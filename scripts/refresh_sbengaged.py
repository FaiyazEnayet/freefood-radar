"""Fetch public SB Engaged events and rebuild the self-contained dashboard.

    python scripts/refresh_sbengaged.py --days 14

Exit 1 on fetch/model failure, retaining the last good snapshot. No authentication
or model downloads are needed. This script does not push or deploy anything.
"""
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from radar.live import refresh


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--days", type=int, default=14, choices=range(1, 91), metavar="1..90")
    args = parser.parse_args()
    succeeded = refresh(ROOT, args.days)
    sys.path.insert(0, str(ROOT / "portfolio_ui"))
    from renderer import render
    render(ROOT, "freefood-radar", ROOT / "portfolio_ui/original-dashboard-snapshot.html", ROOT / "docs/dashboard.html")
    print("SB Engaged snapshot refreshed" if succeeded else "Refresh failed; previous source snapshot retained. Inspect data/sbengaged-status.json.")
    return 0 if succeeded else 1


if __name__ == "__main__":
    raise SystemExit(main())
