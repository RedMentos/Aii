"""Read-only AG12 English/German procedural-score diagnostic (Run22).

Never starts evaluation, registers a suite, or mutates the Store. Equal generation
is necessary but not sufficient to prove identical model weights or language
transfer; these results must never promote an Age/learning gate.
"""
from __future__ import annotations

import math

from .generality import (KEY, REVISION, _solver_key,
                         _validated_holdout_registry, build_suite)

METRICS = ("overall", "seen", "unseen")
CLAIM_LIMIT = (
    "Descriptive procedural EN/DE scores only. Language prompts differ; "
    "model/source revision and causal language transfer are not verified."
)


def _base(status, solver, seed):
    return {
        "status": status,
        "solver": solver,
        "suite_seed": seed,
        "evidence_level": "SOFTWARE_PERSISTED_SCORES_ONLY",
        "learning_proven": False,
        "model_revision_bound": False,
        "authority": 0,
        "claim_limit": CLAIM_LIMIT,
    }


def _latest(st, lang, expected_hash, count, solver):
    if type(st) is not dict or st.get("revision") != REVISION:
        return None, "INVALID_STATE_" + lang
    try:
        _validated_holdout_registry(st)
    except (ValueError, TypeError, KeyError, AttributeError):
        return None, "INVALID_STATE_" + lang
    if st["holdout_history_unknown"]:
        return None, "HOLDOUT_HISTORY_UNKNOWN_" + lang
    if st.get("suite_hash") != expected_hash:
        return None, "SUITE_MISMATCH_" + lang

    matches = [r for r in st["runs"]
               if r.get("suite_hash") == expected_hash
               and r.get("solver", "default") == solver]
    if not matches:
        return None, "NO_RUN_" + lang
    run = matches[-1]  # never cherry-pick an older DONE past a failed/latest run
    if (run.get("status") != "DONE" or type(run.get("items")) is not int
            or run["items"] != count):
        return None, "INCOMPLETE_" + lang
    summary = run.get("summary")
    if type(summary) is not dict:
        return None, "INVALID_METRIC_" + lang
    metrics = {}
    for name in METRICS:
        value = summary.get(name)
        if (type(value) not in (int, float) or not 0 <= value <= 1
                or not math.isfinite(value)):
            return None, "INVALID_METRIC_" + lang
        metrics[name] = float(value)
    generation = run.get("generation")
    if type(generation) not in (str, int) or not generation:
        return None, "GENERATION_UNKNOWN_" + lang
    return (metrics | {"items": count}, generation), None


def compare_languages(store, solver="v13", seed=13):
    """Compare latest complete EN/DE AG12 runs without a Store write or model call.

    A fixed seed/hash, same solver and same generation are required. This does
    not establish matched model revisions or learned transfer.
    """
    if type(seed) is not int or not 0 <= seed <= 1000000:
        raise ValueError("AG12_COMPARE_SEED")
    key = _solver_key(solver, lookup=True)
    en_suite = build_suite(seed=seed, lang="en")
    de_suite = build_suite(seed=seed, lang="de")
    en_state, en_version = store.state(KEY, None)
    de_state, de_version = store.state(KEY + "_DE", None)
    result = _base("NOT_MEASURED", key, seed)

    if en_state is None:
        result["status"] = "MISSING_EN" if en_version == 0 else "INVALID_STATE_EN"
    elif de_state is None:
        result["status"] = "MISSING_DE" if de_version == 0 else "INVALID_STATE_DE"
    else:
        en, problem = _latest(en_state, "EN", en_suite["hash"], len(en_suite["items"]), key)
        if problem:
            result["status"] = problem
        else:
            de, problem = _latest(de_state, "DE", de_suite["hash"], len(de_suite["items"]), key)
            if problem:
                result["status"] = problem
            elif en[1] != de[1]:
                result["status"] = "GENERATION_MISMATCH"
            else:
                en_metrics, de_metrics = en[0], de[0]
                result.update(
                    status="DIAGNOSTIC_ONLY",
                    en=en_metrics,
                    de=de_metrics,
                    same_generation=True,
                    delta_de_minus_en={
                        metric: round(de_metrics[metric] - en_metrics[metric], 4)
                        for metric in METRICS
                    },
                )

    # Optimistic read-side stability: concurrent suite rotation or run append
    # must not publish a mixed-version diagnostic as comparable.
    if (store.state(KEY, None)[1] != en_version
            or store.state(KEY + "_DE", None)[1] != de_version):
        return _base("CONCURRENT_CHANGE", key, seed)
    return result
