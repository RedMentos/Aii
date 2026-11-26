#!/usr/bin/env python3
"""Exact toy probe for set-level predictive value in a JEPA-style process.

This does NOT train a JEPA or measure a V14 runtime. It analytically evaluates
one controlled transition used by Levy, Lidayan & Goldberg (arXiv:2610.27364):
a binary light is sampled independently each frame, but its current value biases
which of two image positions is replaced. The light has zero self-predictive
information while its current value can predict the other features' transition.

The probe reports partner information and the light's one-bit entropy cost
separately. It deliberately does not collapse them into an attention score or
an admission decision.
"""

from __future__ import annotations

import argparse
import json
import math
import random
from typing import Iterable

SCHEMA = "v14.predictive-closure-toy-probe/1"
DEFAULT_Q = (0.0, 0.25, 0.5, 0.75, 1.0)


def binary_entropy_bits(probability: float) -> float:
    """Shannon entropy of a Bernoulli variable, in bits."""
    if isinstance(probability, bool) or not isinstance(probability, (int, float)):
        raise ValueError("probability must be a finite number in [0, 1]")
    p = float(probability)
    if not math.isfinite(p) or not 0.0 <= p <= 1.0:
        raise ValueError("probability must be a finite number in [0, 1]")
    if p in (0.0, 1.0):
        return 0.0
    return -(p * math.log2(p) + (1.0 - p) * math.log2(1.0 - p))


def empirical_mutual_information_bits(pairs: Iterable[tuple[int, int]]) -> float:
    """Plug-in MI for binary pairs; intended only for the seeded toy check."""
    counts = {(x, y): 0 for x in (0, 1) for y in (0, 1)}
    n = 0
    for x, y in pairs:
        if x not in (0, 1) or y not in (0, 1):
            raise ValueError("binary samples must contain only 0 or 1")
        counts[(x, y)] += 1
        n += 1
    if n == 0:
        raise ValueError("at least one sample is required")
    px = {x: sum(counts[(x, y)] for y in (0, 1)) / n for x in (0, 1)}
    py = {y: sum(counts[(x, y)] for x in (0, 1)) / n for y in (0, 1)}
    result = 0.0
    for (x, y), count in counts.items():
        if count:
            pxy = count / n
            result += pxy * math.log2(pxy / (px[x] * py[y]))
    return result


def evaluate_light_control(q: float) -> dict[str, float | bool | str]:
    """Evaluate one light-control probability from the paper's toy process.

    q is the probability that the current light selects the replaced position;
    with probability 1-q, the position is selected uniformly at random.
    Therefore P(replaced_position == light) = (1+q)/2.
    """
    if isinstance(q, bool) or not isinstance(q, (int, float)):
        raise ValueError("q must be a finite number in [0, 1]")
    q = float(q)
    if not math.isfinite(q) or not 0.0 <= q <= 1.0:
        raise ValueError("q must be a finite number in [0, 1]")

    match_probability = (1.0 + q) / 2.0
    crossover_probability = 1.0 - match_probability
    partner_information = 1.0 - binary_entropy_bits(crossover_probability)

    return {
        "q": q,
        "light_self_predictive_information_bits": 0.0,
        "light_entropy_cost_bits": 1.0,
        "partner_prediction_information_bits": partner_information,
        "light_identifies_replaced_position_probability": match_probability,
        "scalar_self_predictability_filter_would_drop_light": True,
        "set_level_partner_signal_available": partner_information > 0.0,
    }


def simulate_light_control(
    q: float, *, samples: int = 200_000, seed: int = 17
) -> dict[str, float | int]:
    """Seeded finite-sample check of partner and self unpredictability."""
    if isinstance(samples, bool) or not isinstance(samples, int) or samples < 1:
        raise ValueError("samples must be a positive integer")
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError("seed must be an integer")
    exact = evaluate_light_control(q)
    q = float(exact["q"])
    rng = random.Random(seed)
    partner_pairs = []
    self_pairs = []
    for _ in range(samples):
        light = rng.randrange(2)
        if rng.random() < q:
            replaced_position = light
        else:
            replaced_position = rng.randrange(2)
        next_light = rng.randrange(2)
        partner_pairs.append((light, replaced_position))
        self_pairs.append((light, next_light))
    return {
        "samples": samples,
        "seed": seed,
        "partner_information_bits_empirical": empirical_mutual_information_bits(partner_pairs),
        "light_self_information_bits_empirical": empirical_mutual_information_bits(self_pairs),
    }


def run_probe(q_values: Iterable[float] = DEFAULT_Q) -> dict:
    """Return a deterministic, JSON-serializable sweep."""
    rows = []
    for q in q_values:
        exact = evaluate_light_control(q)
        exact["finite_sample_check"] = simulate_light_control(float(exact["q"]))
        rows.append(exact)
    if not rows:
        raise ValueError("at least one q value is required")
    return {
        "schema": SCHEMA,
        "experiment": "independent-light / light-controlled image replacement",
        "evidence_class": "SYNTHETIC_ANALYTIC_INFORMATION_THEORY_ONLY",
        "trained_jepa": False,
        "runtime_integrated": False,
        "formula": "I(L_t; replaced_position_t) = 1 - H2((1-q)/2)",
        "rows": rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--q",
        type=float,
        nargs="*",
        default=list(DEFAULT_Q),
        help="light-control probabilities in [0,1] (default: 0 .25 .5 .75 1)",
    )
    args = parser.parse_args()
    print(json.dumps(run_probe(args.q), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
