"""Run13D: preregistered C2 word-feature v1/v2 synthetic route transfer.

Real NumPy learning_worker.train fits, but constant synthetic embeddings and
synthetic route labels: NO native Needle, human feedback or active authority.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np

from v13 import learning_worker as worker
from v13 import route_words as v1
from v13 import route_words_numeric_candidate as v2

SCHEMA = "v13.c2.route.numeric_generalization.run13d.v1"
COHORT_SHA256 = "563f530aac86a1e4ab5314d0833538ffe3587013742951e5a1cf9474a60c6140"
TEMPLATES = ("half {n} please", "quote {n} exactly",
             "summarize {n} briefly", "compare {n} conflicts")
TRAIN_NUMBERS = tuple(str(i) for i in range(1, 9))
HOLDOUT_NUMBERS = ("100000", "7000000", "3.14", "1.23e-5",
                   "99,999", "8%", "-20", ".5e-3")
CONFIG = {
    "learning_steps": 80, "eligibility_decay": .95,
    "learning_rate": .02, "max_update_norm": .02,
    "retention_max_delta": .02,
}
EMBEDDING = [1., 0., 0., 0.]


def cohort():
    train = [[template.format(n=n), label]
             for label, template in enumerate(TEMPLATES) for n in TRAIN_NUMBERS]
    holdout = [[template.format(n=n), label]
               for label, template in enumerate(TEMPLATES) for n in HOLDOUT_NUMBERS]
    payload = {"train": train, "holdout": holdout}
    sha = hashlib.sha256(json.dumps(
        payload, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")).hexdigest()
    if (sha != COHORT_SHA256 or len(train) != 32 or len(holdout) != 32
            or set(t for t, _ in train) & set(t for t, _ in holdout)):
        raise ValueError("RUN13D_FROZEN_COHORT_RED")
    return payload


def _fit(module, train, holdout, folder, *, deranged=False):
    words = [module.vector(t) for t, _ in train]
    labels = [((label + 1) % 4 if deranged else label)
              for _, label in train]
    request = {
        "config": CONFIG,
        "embeddings": [EMBEDDING[:] for _ in train],
        "words": words,
        "labels": labels,
        "scaffold_labels": [0] * len(train),
    }
    folder.mkdir()
    metrics = worker.train(request, folder)
    with np.load(folder / "candidate.npz", allow_pickle=False) as checkpoint:
        if worker.word_dim(checkpoint) != module.DIM:
            raise ValueError("RUN13D_WORD_DIMENSION_RED")
        weights = checkpoint["route_w"].copy()
    def evaluate(rows):
        x = worker.features(
            [EMBEDDING[:] for _ in rows],
            [module.vector(text) for text, _ in rows])
        prediction = np.argmax(x @ weights, axis=1).tolist()
        labels = [label for _, label in rows]
        correct = sum(p == y for p, y in zip(prediction, labels))
        confusion = [[sum(p == guess and y == actual
                          for p, y in zip(prediction, labels))
                      for guess in range(4)] for actual in range(4)]
        return {"n": len(rows), "correct": correct,
                "accuracy": correct / len(rows), "confusion": confusion}
    return {
        "revision": module.REVISION,
        "train": evaluate(train),
        "holdout": evaluate(holdout),
        "gradient_check": metrics["gradient_check"],
        "deterministic_repeat": metrics["deterministic_repeat"],
        "checkpoint_reload": metrics["checkpoint_reload"],
        "finite": metrics["finite"],
        "optimizer_steps": metrics["optimizer_steps"],
        "worker_commit_eligible_not_active": metrics["commit_eligible"],
    }


def run():
    data = cohort()
    with TemporaryDirectory(prefix="v13-run13d-route-") as tmp:
        root = Path(tmp)
        a = _fit(v1, data["train"], data["holdout"], root / "v1")
        b = _fit(v2, data["train"], data["holdout"], root / "v2")
        negative = _fit(v2, data["train"], data["holdout"],
                        root / "deranged", deranged=True)
    signal = bool(b["holdout"]["correct"] >= a["holdout"]["correct"] + 4
                  and b["train"]["accuracy"] >= a["train"]["accuracy"] - .05)
    return {
        "schema": SCHEMA, "cohort_sha256": COHORT_SHA256,
        "train_rows": 32, "holdout_rows": 32,
        "evidence": "SYNTHETIC_WORD_CHANNEL_LEARNING_NOT_NATIVE",
        "v1": a, "v2": b, "deranged_label_control": negative,
        "prospective_signal_not_gate": signal,
        "model_called": False, "native_calls": 0,
        "active_head_modified": False, "source_cohorts_modified": False,
        "learning_mode": "RECORD_ONLY", "step2_status": "UTILITY_FAIL",
        "b3_status": "NO_PROMOTION", "body_jepa_status": "UNAVAILABLE",
        "jepa_weight": 0, "redmi_measured": False,
        "whole_system_complete": False,
    }


if __name__ == "__main__":
    print(json.dumps(run(), sort_keys=True, allow_nan=False))
