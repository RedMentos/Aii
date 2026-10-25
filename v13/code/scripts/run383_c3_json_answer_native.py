"""Run383 pinned native C3 JSON nonempty/schema-visible prompt 2x2 factorial.

Actual Linux-native GGUF and runner are provided/hashed by isolated workflow.
No production schema, prompt, weight, Store, teacher or Age changes.
"""
import argparse
import copy
import hashlib
import json
import math
import os
import threading
import time
import traceback
from pathlib import Path

from v13.config import initialize
from v13.runners import LlamaRunner
from v13.agi.solver import SYS, SCHEMA, extract, confidence
from v13.common import atomic_write, dumps

EXPLICIT_JSON_SYS = (
    "Return only a JSON object with one key named answer containing the exact short "
    "final result as a nonempty string. No explanations, no extra fields, no surrounding text."
)
NONEMPTY_SCHEMA = copy.deepcopy(SCHEMA)
NONEMPTY_SCHEMA["properties"]["answer"]["minLength"] = 1
ARMS = ("baseline", "min_length", "explicit_json", "combined")
CASES = (
    ("arithmetic", "Compute: 6 + 8 = ?", "14"),
    ("arithmetic", "Compute: 15 - 7 = ?", "8"),
    ("arithmetic", "Compute: 4 * 5 = ?", "20"),
    ("arithmetic", "Compute: 13 + 9 = ?", "22"),
    ("backwards", "Write backwards: bird", "drib"),
    ("backwards", "Write backwards: rose", "esor"),
    ("backwards", "Write backwards: moon", "noom"),
    ("backwards", "Write backwards: train", "niart"),
    ("sequence", "Continue: 2, 5, 8, ?", "11"),
    ("sequence", "Continue: 4, 8, 12, ?", "16"),
    ("sequence", "Continue: 9, 7, 5, ?", "3"),
    ("sequence", "Continue: 1, 4, 7, ?", "10"),
)
MIN_GAIN = 2
MIN_EMPTY_REDUCTION = 2
MAX_DURATION_RATIO = 1.5


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def finite(value):
    return value if type(value) in (int, float) and math.isfinite(value) else None


def arm_config(arm):
    if arm not in ARMS:
        raise ValueError("unknown arm")
    return (
        EXPLICIT_JSON_SYS if arm in ("explicit_json", "combined") else SYS,
        NONEMPTY_SCHEMA if arm in ("min_length", "combined") else SCHEMA,
    )


def summarize(rows):
    by_arm = {}
    for arm in ARMS:
        rr = [r for r in rows if r["arm"] == arm]
        durations = [r["duration_s"] for r in rr if r["duration_s"] is not None]
        cats = {
            cat: {"correct": sum(r["correct_exact"] for r in rr if r["category"] == cat),
                  "total": sum(r["category"] == cat for r in rr)}
            for cat in ("arithmetic", "backwards", "sequence")
        }
        by_arm[arm] = {
            "correct": sum(r["correct_exact"] for r in rr),
            "empty": sum(r["empty"] for r in rr),
            "wrong_nonempty": sum(r["wrong_nonempty"] for r in rr),
            "field_supported": sum(r["field_supported"] for r in rr),
            "total": len(rr), "categories": cats,
            "mean_duration_s": sum(durations) / len(durations)
            if durations and len(durations) == len(rr) else None,
        }
    base, combined = by_arm["baseline"], by_arm["combined"]
    ratio = (
        combined["mean_duration_s"] / base["mean_duration_s"]
        if base["mean_duration_s"] and combined["mean_duration_s"] is not None else None
    )
    return {
        "arms": by_arm,
        "exact_gain": combined["correct"] - base["correct"],
        "empty_reduction": base["empty"] - combined["empty"],
        "wrong_nonempty_nonincrease": combined["wrong_nonempty"] <= base["wrong_nonempty"],
        "field_coverage_nonregress": combined["field_supported"] >= base["field_supported"],
        "category_no_regress": all(
            combined["categories"][cat]["correct"] >= base["categories"][cat]["correct"]
            for cat in ("arithmetic", "backwards", "sequence")
        ),
        "combined_duration_ratio": ratio,
        "thresholds": {
            "min_exact_gain": MIN_GAIN,
            "min_empty_reduction": MIN_EMPTY_REDUCTION,
            "max_duration_ratio": MAX_DURATION_RATIO,
        },
    }


def supported(summary, rows, reaped, pids):
    a = summary["arms"]
    ratio = summary["combined_duration_ratio"]
    return bool(
        len(rows) == 48 and all(a[arm]["total"] == 12 for arm in ARMS)
        and summary["exact_gain"] >= MIN_GAIN
        and summary["empty_reduction"] >= MIN_EMPTY_REDUCTION
        and summary["wrong_nonempty_nonincrease"]
        and summary["field_coverage_nonregress"]
        and summary["category_no_regress"]
        and ratio is not None and ratio <= MAX_DURATION_RATIO
        and all(r["status"] == "FINAL" and r["can_train_body"] is False for r in rows)
        and reaped is True and not pids
    )


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--home", required=True)
    p.add_argument("--model", required=True)
    p.add_argument("--binary", required=True)
    p.add_argument("--report", required=True)
    args = p.parse_args()
    home, model, binary = Path(args.home), Path(args.model), Path(args.binary)
    report_path = Path(args.report)
    report = {
        "revision": "RUN383_PINNED_C3_JSON_ANSWER_FACTORIAL_V1",
        "evidence_level": "LINUX_NATIVE_C3_ONLY",
        "status": "STARTED", "model_sha256": sha256(model),
        "binary_sha256": sha256(binary), "arms": list(ARMS),
        "baseline_system_prompt": SYS, "explicit_json_system_prompt": EXPLICIT_JSON_SYS,
        "baseline_schema": SCHEMA, "nonempty_schema": NONEMPTY_SCHEMA,
        "rows": [], "native_plumbing_pass": False,
        "json_answer_supported": False, "can_train_body": False,
        "step2_exit": False, "b3_promoted": False, "jepa_weight_promoted": False,
        "phone_measured": False,
    }
    runner = None
    try:
        cfg = initialize(home)
        cfg.update(context_tokens=512, answer_tokens=40, threads=2, temperature=0.0,
                   native_cache_ram_mb=32, native_ctx_checkpoints=2, offer_logprobs=True)
        os.environ["V13_LLAMA_SERVER"] = str(binary)
        runner = LlamaRunner(home, "C3_LANGUAGE", model, cfg)
        cancel = threading.Event()
        deadline = time.monotonic() + 900.0
        for index, (category, prompt, expected) in enumerate(CASES):
            order = ARMS[index % len(ARMS):] + ARMS[:index % len(ARMS)]
            for arm in order:
                system_prompt, schema = arm_config(arm)
                raw = "".join(runner.generate([
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                ], cancel, deadline, max_tokens=40, schema=schema, seed=13,
                    confidence_field="answer"))
                m = dict(runner.last_metrics)
                tc = m.get("token_confidence") or {}
                answer = extract(raw)
                conf, conf_src = confidence(m)
                correct = answer.strip().casefold() == expected.casefold()
                field_ok = (
                    conf_src in ("field_min_prob", "field_mean_prob")
                    and type(tc.get("field_tokens")) is int and tc["field_tokens"] > 0
                    and conf > 0
                )
                report["rows"].append({
                    "index": index, "category": category, "prompt": prompt,
                    "expected": expected, "arm": arm, "answer": answer[:200],
                    "empty": not bool(answer.strip()), "correct_exact": correct,
                    "wrong_nonempty": bool(answer.strip()) and not correct,
                    "status": m.get("status"), "can_train_body": m.get("CAN_TRAIN_BODY"),
                    "field_supported": field_ok, "confidence": finite(conf),
                    "confidence_source": conf_src,
                    "field_tokens": tc.get("field_tokens"),
                    "field_min_prob": finite(tc.get("field_min_prob")),
                    "field_mean_prob": finite(tc.get("field_mean_prob")),
                    "duration_s": finite(m.get("duration_s")),
                    "ttft_s": finite(m.get("ttft_s")),
                    "sampled_peak_rss_bytes": finite(m.get("sampled_peak_rss_bytes")),
                })
        report["summary"] = summarize(report["rows"])
        report["status"] = "MEASURED"
    except BaseException as exc:
        report["status"] = "ERROR"
        report["error_type"] = type(exc).__name__
        report["error"] = str(exc)[:400]
        report["traceback"] = traceback.format_exc()[-4000:]
        raise
    finally:
        if runner is not None:
            try:
                release = runner.unload()
                report["process_reaped"] = release.get("process_reaped")
                report["remaining_pids"] = runner.pids()
            except BaseException as exc:
                report["process_reaped"] = False
                report["release_error"] = type(exc).__name__
        if "summary" in report:
            report["native_plumbing_pass"] = bool(
                len(report["rows"]) == 48
                and all(r["status"] == "FINAL" and r["can_train_body"] is False
                        for r in report["rows"])
                and report.get("process_reaped") is True
                and not report.get("remaining_pids")
            )
            report["json_answer_supported"] = supported(
                report["summary"], report["rows"],
                report.get("process_reaped"), report.get("remaining_pids")
            )
            report["status"] = (
                "RUN383_JSON_ANSWER_SUPPORTED" if report["json_answer_supported"]
                else "RUN383_JSON_ANSWER_NOT_SUPPORTED"
            )
        report_path.parent.mkdir(parents=True, exist_ok=True)
        atomic_write(report_path, dumps(report))
        print("RUN383_REPORT=" + json.dumps(report, sort_keys=True, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
