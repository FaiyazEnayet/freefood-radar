"""Classifier tests: trains on the real labeled data, checks real metrics."""

import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from radar.classifier import build_pipeline, load_labeled, load_model, predict_proba, train


def test_labeled_data_shape():
    df = load_labeled()
    assert len(df) == 160
    assert set(df["label"].unique()) == {0, 1}
    assert df["label"].sum() == 80  # balanced


def test_train_produces_real_metrics():
    res = train()
    m = res["metrics"]
    assert m["n_total"] == 160
    assert m["precision"] >= 0.80, f"precision {m['precision']:.3f} too low"
    assert m["recall"] >= 0.75, f"recall {m['recall']:.3f} too low"
    assert m["accuracy"] >= 0.80


def test_saved_model_roundtrip():
    train()
    model = load_model()
    proba = predict_proba(model, ["Free pizza for everyone at the GBM!"])
    assert 0.0 <= proba[0] <= 1.0
    assert proba[0] > 0.5  # obvious positive


def test_obvious_negative_scores_low():
    train()
    model = load_model()
    proba = predict_proba(
        model,
        ["Food for thought: philosophy debate on ethics. No food served."],
    )
    assert proba[0] < 0.5


def test_probabilities_are_calibrated_monotone():
    train()
    model = load_model()
    texts = [
        "Free pizza free pizza free pizza for all attendees!",
        "Weekly budget planning meeting. No food.",
    ]
    p = predict_proba(model, texts)
    assert p[0] > p[1]


def test_pipeline_structure():
    pipe = build_pipeline()
    # CalibratedClassifierCV wrapping a Pipeline(tifdf, lr)
    assert hasattr(pipe, "predict_proba")
