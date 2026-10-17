"""Build docs/dashboard.html: the stunning self-contained Plotly dashboard.

Sections: KPI cards, campus map with pins, ranked digest, classifier
report (precision/recall + calibration), historical analytics
(top clubs, day x time heatmap), watchlist alerts.

Run: PYTHONPATH=src .venv/bin/python scripts/make_dashboard.py
"""

import json
import os
import sys
from datetime import datetime

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from radar import digest as digest_mod
from radar import stats as stats_mod
from radar import watchlist as watchlist_mod
from radar.classifier import load_model
from radar.models import Event

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
DOCS = os.path.join(ROOT, "docs")

BG = "#0e1117"
CARD = "#161b22"
TEXT = "#e6edf3"
ACCENT = "#f0a832"
GREEN = "#3fb950"
BLUE = "#58a6ff"


def load_events() -> list[Event]:
    with open(os.path.join(ROOT, "data", "seed_events.json")) as f:
        raw = json.load(f)
    return [Event.from_dict(d) for d in raw]


def load_places() -> dict:
    with open(os.path.join(ROOT, "data", "campus_places.json")) as f:
        return json.load(f)


def place_coords(name: str, places: dict) -> tuple[float, float] | None:
    for key, coords in places["places"].items():
        if key.lower() in name.lower() or name.lower() in key.lower():
            return coords["lat"], coords["lon"]
    return None


def kpi_cards(s: dict) -> str:
    cards = [
        ("Events scanned", str(s["n_events"])),
        ("Free-food hits", str(s["n_food_events"])),
        ("Hit rate", f"{s['food_rate']:.0%}"),
        ("Avg confidence", f"{s['avg_confidence']:.0%}"),
    ]
    inner = "".join(
        f"<div style='background:{CARD};border-radius:12px;padding:18px 22px;"
        f"min-width:150px;text-align:center'>"
        f"<div style='font-size:13px;color:#8b949e'>{label}</div>"
        f"<div style='font-size:32px;font-weight:700;color:{TEXT}'>{val}</div></div>"
        for label, val in cards
    )
    return f"<div style='display:flex;gap:14px;flex-wrap:wrap;margin:18px 0'>{inner}</div>"


def map_figure(ranked: list[Event], places: dict) -> go.Figure:
    rows = []
    for e in ranked:
        coords = place_coords(e.location or "", places)
        if not coords:
            continue
        when = e.starts_at.strftime("%a %I:%M %p") if e.starts_at else "TBA"
        rows.append({
            "lat": coords[0] + np.random.RandomState(hash(e.title) % 2**16).uniform(-0.0006, 0.0006),
            "lon": coords[1] + np.random.RandomState(hash(e.title) % 2**16 + 1).uniform(-0.0006, 0.0006),
            "label": f"<b>{e.title}</b><br>{e.club}<br>{e.location} · {when}<br>"
                     f"confidence {e.food_probability:.0%} · EV {e.score:.2f}",
            "prob": e.food_probability,
            "title": e.title,
        })
    df = pd.DataFrame(rows)
    fig = px.scatter_map(
        df, lat="lat", lon="lon", color="prob", hover_name="title",
        hover_data={"label": True, "lat": False, "lon": False, "prob": False},
        color_continuous_scale=["#ff6b6b", "#ffd166", "#3fb950"],
        range_color=[0.5, 1.0],
        zoom=14.2,
        center={"lat": places["campus_center"]["lat"], "lon": places["campus_center"]["lon"]},
        map_style="open-street-map",
        title="Campus map — today's free-food pins (color = confidence)",
    )
    fig.update_layout(height=480, margin=dict(l=0, r=0, t=40, b=0),
                      paper_bgcolor=BG, font_color=TEXT)
    fig.update_traces(marker=dict(size=13, opacity=0.92))
    return fig


def ranked_table(ranked: list[Event]) -> go.Figure:
    rows = []
    for i, e in enumerate(ranked[:15], 1):
        when = e.starts_at.strftime("%a %I:%M %p") if e.starts_at else "TBA"
        rows.append([i, e.title, e.club, e.location or "TBA", when,
                     f"{e.food_probability:.0%}", f"{e.score:.2f}",
                     ", ".join(e.food_keywords[:3])])
    fig = go.Figure(data=[go.Table(
        header=dict(values=["#", "Event", "Club", "Where", "When", "Confidence", "EV", "Signals"],
                    fill_color="#1f6feb", font=dict(color="white", size=12), align="left"),
        cells=dict(values=list(zip(*rows)) if rows else [[]] * 8,
                   fill_color=CARD, font=dict(color=TEXT, size=11), align="left"),
    )])
    fig.update_layout(title="Ranked digest — expected value = confidence x food quality",
                      paper_bgcolor=BG, font_color=TEXT, height=520,
                      margin=dict(l=0, r=0, t=40, b=0))
    return fig


def classifier_report() -> tuple[go.Figure, go.Figure]:
    with open(os.path.join(ROOT, "models", "metrics.json")) as f:
        m = json.load(f)
    cal = np.load(os.path.join(ROOT, "models", "calibration.npz"))
    y_true, y_prob = cal["y_true"], cal["y_prob"]

    perf = go.Figure(data=[go.Bar(
        x=["Accuracy", "Precision", "Recall", "F1"],
        y=[m["accuracy"], m["precision"], m["recall"], m["f1"]],
        marker_color=[BLUE, GREEN, ACCENT, "#a371f7"],
        text=[f"{v:.1%}" for v in [m["accuracy"], m["precision"], m["recall"], m["f1"]]],
        textposition="outside",
    )])
    perf.update_layout(title=f"Classifier report — TF-IDF + logistic regression "
                             f"(n={m['n_total']}, {m['n_train']} train / {m['n_test']} test)",
                       yaxis_range=[0, 1.15], paper_bgcolor=BG, plot_bgcolor=BG,
                       font_color=TEXT, height=360)

    # Calibration curve: mean predicted prob vs observed rate per bin.
    bins = np.linspace(0, 1, 11)
    idx = np.clip(np.digitize(y_prob, bins) - 1, 0, 9)
    bx, by, bn = [], [], []
    for b in range(10):
        mask = idx == b
        if mask.sum() > 0:
            bx.append(y_prob[mask].mean())
            by.append(y_true[mask].mean())
            bn.append(mask.sum())
    calib = go.Figure()
    calib.add_trace(go.Scatter(x=[0, 1], y=[0, 1], mode="lines",
                               line=dict(dash="dash", color="#8b949e"), name="perfect"))
    calib.add_trace(go.Scatter(x=bx, y=by, mode="markers+lines", name="model",
                               marker=dict(size=10, color=ACCENT)))
    calib.update_layout(title="Calibration — predicted probability vs observed rate",
                        xaxis_title="mean predicted probability",
                        yaxis_title="observed free-food rate",
                        paper_bgcolor=BG, plot_bgcolor=BG, font_color=TEXT, height=360)
    return perf, calib


def analytics_figures(events: list[Event]):
    scored = [e for e in events if e.food_probability >= 0.5]
    top = stats_mod.top_clubs(scored, 10)
    clubs_fig = go.Figure(data=[go.Bar(
        y=[c for c, _ in reversed(top)], x=[n for _, n in reversed(top)],
        orientation="h", marker_color=GREEN,
        text=[n for _, n in reversed(top)], textposition="outside",
    )])
    clubs_fig.update_layout(title="Which clubs feed people most",
                            paper_bgcolor=BG, plot_bgcolor=BG, font_color=TEXT, height=420)

    mat = stats_mod.heatmap_matrix(scored)
    heat = go.Figure(data=[go.Heatmap(
        z=mat.values, x=mat.columns, y=mat.index,
        colorscale=["#161b22", "#f0a832"], showscale=True,
        text=mat.values, texttemplate="%{text}",
    )])
    heat.update_layout(title="Best days x times for free food",
                       paper_bgcolor=BG, font_color=TEXT, height=380)
    return clubs_fig, heat


def watchlist_html(alerts: list[watchlist_mod.Alert], favorites: list[str]) -> str:
    if not alerts:
        return "<p>No watchlist matches today.</p>"
    items = "".join(
        f"<div style='background:{CARD};border-left:4px solid {ACCENT};"
        f"border-radius:8px;padding:10px 14px;margin:8px 0'>"
        f"<b style='color:{ACCENT}'>{a.food.title()}</b> — {a.event.title} "
        f"<span style='color:#8b949e'>({a.event.club}, "
        f"{a.event.starts_at.strftime('%a %I:%M %p') if a.event.starts_at else 'TBA'})</span>"
        f"</div>"
        for a in alerts[:10]
    )
    return (f"<p style='color:#8b949e'>Watching: {', '.join(favorites)}</p>{items}")


def main():
    events = load_events()
    places = load_places()
    model = load_model()
    _, ranked = digest_mod.build_digest(events, model)
    s = stats_mod.summary(events)
    favorites = watchlist_mod.load_favorites()
    alerts = watchlist_mod.check(ranked, favorites)

    perf_fig, calib_fig = classifier_report()
    clubs_fig, heat_fig = analytics_figures(events)

    parts = [
        f"<h1 style='color:{TEXT}'>Free Food Radar <span style='font-size:18px;color:#8b949e'>"
        f"Stony Brook University</span></h1>",
        f"<p style='color:#8b949e'>Scraped {s['n_events']} campus events, "
        f"scored every blurb with a calibrated NLP classifier, ranked by expected value. "
        f"Week of Oct 12-18, 2026.</p>",
        kpi_cards(s),
        "<h2 style='color:" + TEXT + "'>Today's map</h2>",
        map_figure(ranked, places).to_html(full_html=False, include_plotlyjs=True),
        "<h2 style='color:" + TEXT + "'>Ranked digest</h2>",
        ranked_table(ranked).to_html(full_html=False, include_plotlyjs=False),
        "<h2 style='color:" + TEXT + "'>The model behind the ranking</h2>",
        "<div style='display:flex;gap:14px;flex-wrap:wrap'>"
        "<div style='flex:1;min-width:320px'>" + perf_fig.to_html(full_html=False, include_plotlyjs=False) + "</div>"
        "<div style='flex:1;min-width:320px'>" + calib_fig.to_html(full_html=False, include_plotlyjs=False) + "</div></div>",
        "<h2 style='color:" + TEXT + "'>Historical analytics</h2>",
        "<div style='display:flex;gap:14px;flex-wrap:wrap'>"
        "<div style='flex:1;min-width:320px'>" + clubs_fig.to_html(full_html=False, include_plotlyjs=False) + "</div>"
        "<div style='flex:1;min-width:320px'>" + heat_fig.to_html(full_html=False, include_plotlyjs=False) + "</div></div>",
        "<h2 style='color:" + TEXT + "'>Watchlist alerts</h2>",
        watchlist_html(alerts, favorites),
        "<p style='color:#8b949e;font-size:12px;margin-top:30px'>Built with scikit-learn, "
        "Plotly, and BeautifulSoup. Classifier metrics from a real held-out test split.</p>",
    ]
    html = ("<!DOCTYPE html><html><head><meta charset='utf-8'>"
            "<meta name='viewport' content='width=device-width,initial-scale=1'>"
            "<title>Free Food Radar — Stony Brook</title></head>"
            f"<body style='background:{BG};color:{TEXT};font-family:system-ui,sans-serif;"
            "max-width:1100px;margin:0 auto;padding:24px'>" + "\n".join(parts) + "</body></html>")

    os.makedirs(DOCS, exist_ok=True)
    out = os.path.join(DOCS, "dashboard.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write(_portfolio_html(html))
    print(f"dashboard -> {out} ({os.path.getsize(out)/1e6:.1f} MB)")



def _portfolio_html(raw):
    """Presentation-only transform of this run’s freshly calculated figures."""
    import sys
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root / "portfolio_ui"))
    from renderer import render_html
    return render_html(root, 'freefood-radar', raw)[0]

if __name__ == "__main__":
    from pathlib import Path
    project_root = Path(__file__).resolve().parents[1]
    if (project_root / "data/sbengaged-events.json").exists():
        sys.path.insert(0, str(project_root / "portfolio_ui"))
        from renderer import render
        render(project_root, "freefood-radar", project_root / "portfolio_ui/original-dashboard-snapshot.html", project_root / "docs/dashboard.html")
    else:
        main()
