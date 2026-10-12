"""Food-quality signals for expected-value ranking.

expected_value = P(free food) x quality_score

quality_score blends: how good the food sounds (cuisine keywords),
how much of it there is (meal vs snack words), and scarcity pressure
("while supplies last", "first 50"). All weights are transparent and
tunable in one place.
"""

from __future__ import annotations

import re

# Cuisine / item keywords -> desirability weight. Higher = better spread.
CUISINE_WEIGHTS = {
    "pizza": 1.00,
    "bbq": 0.95,
    "barbecue": 0.95,
    "tacos": 0.95,
    "sushi": 0.90,
    "wings": 0.90,
    "chipotle": 0.90,
    "boba": 0.85,
    "bubble tea": 0.85,
    "burgers": 0.85,
    "shawarma": 0.85,
    "biryani": 0.85,
    "dumplings": 0.80,
    "ramen": 0.80,
    "sandwiches": 0.75,
    "subs": 0.75,
    "bagels": 0.70,
    "donuts": 0.70,
    "doughnuts": 0.70,
    "ice cream": 0.70,
    "pasta": 0.70,
    "fried chicken": 0.80,
    "street cart": 0.85,
    "empanadas": 0.75,
    "samosas": 0.70,
    "spring rolls": 0.65,
    "cookies": 0.55,
    "brownies": 0.55,
    "cupcakes": 0.55,
    "popcorn": 0.45,
    "chips": 0.45,
    "soda": 0.40,
    "coffee": 0.50,
}

MEAL_WORDS = {"dinner": 0.25, "lunch": 0.25, "brunch": 0.20, "catered": 0.25,
              "full meal": 0.25, "buffet": 0.25, "feast": 0.25}
SNACK_WORDS = {"light refreshments": -0.25, "snacks": -0.15,
               "refreshments will be served": -0.10, "light snacks": -0.20}
SCARCITY_WORDS = {"while supplies last": 0.10, "first 50": 0.10,
                  "first come": 0.08, "limited": 0.05, "rsvp": 0.05}

FREE_FOOD_PATTERNS = [
    "free food", "free pizza", "free lunch", "free dinner", "free brunch",
    "free snacks", "free boba", "free coffee", "free donuts", "free ice cream",
    "food will be provided", "food provided", "lunch provided",
    "dinner provided", "refreshments provided", "pizza will be served",
    "free wings",
]

FOOD_RE = re.compile("|".join(sorted(CUISINE_WEIGHTS, key=len, reverse=True)))
MEAL_RE = re.compile("|".join(sorted(MEAL_WORDS, key=len, reverse=True)))
SNACK_RE = re.compile("|".join(sorted(SNACK_WORDS, key=len, reverse=True)))
SCARCE_RE = re.compile("|".join(sorted(SCARCITY_WORDS, key=len, reverse=True)))
FREE_RE = re.compile("|".join(sorted(FREE_FOOD_PATTERNS, key=len, reverse=True)))


def quality_score(text: str) -> tuple[float, list[str]]:
    """Return (score in [0, 1.5], matched keywords)."""
    t = text.lower()
    score = 0.45  # prior: an average free-food mention
    hits: list[str] = []
    for m in FOOD_RE.finditer(t):
        w = CUISINE_WEIGHTS[m.group(0)]
        score = max(score, 0.35 + 0.65 * w)
        hits.append(m.group(0))
    for m in MEAL_RE.finditer(t):
        score += MEAL_WORDS[m.group(0)]
        hits.append(m.group(0))
    for m in SNACK_RE.finditer(t):
        score += SNACK_WORDS[m.group(0)]
        hits.append(m.group(0))
    for m in SCARCE_RE.finditer(t):
        score += SCARCITY_WORDS[m.group(0)]
    return min(max(score, 0.05), 1.5), sorted(set(hits))


def free_food_keywords(text: str) -> list[str]:
    t = text.lower()
    return sorted({m.group(0) for m in FREE_RE.finditer(t)})


def expected_value(probability: float, text: str) -> tuple[float, float, list[str]]:
    """Return (expected_value, quality, keywords)."""
    q, kw = quality_score(text)
    return probability * q, q, kw
