"""Train the free-food classifier and report metrics. Run: PYTHONPATH=src .venv/bin/python scripts/train_classifier.py"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from radar.classifier import train


def main():
    res = train()
    m = res["metrics"]
    print(f"trained on {m['n_total']} labeled examples "
          f"({m['n_train']} train / {m['n_test']} test, seed {m['seed']})")
    print(f"accuracy  {m['accuracy']:.3f}")
    print(f"precision {m['precision']:.3f}")
    print(f"recall    {m['recall']:.3f}")
    print(f"F1        {m['f1']:.3f}")
    tn, fp, fn, tp = m["confusion"][0][0], m["confusion"][0][1], m["confusion"][1][0], m["confusion"][1][1]
    print(f"confusion: TN={tn} FP={fp} FN={fn} TP={tp}")
    print("model -> models/classifier.joblib, metrics -> models/metrics.json")


if __name__ == "__main__":
    main()
