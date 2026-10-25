"""Run382 pinned Linux-native C3 instruction-only prompt A/B; no production edits.

Immutable public model and runner are verified by the workflow. No mocks, model
writes, Store writes, tools, history, teacher, Redmi or gate promotion.
"""
import argparse
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

CANDIDATE_SYS = (
    "Give exactly the requested final result as a single short answer. "
    "For arithmetic, calculate the value. For backwards text, reverse every character. "
    "For number sequences, continue the numerical pattern. Never explain your reasoning."
)
CASES = (
    ("arithmetic", "Compute: 8 + 6 = ?", "14"),
    ("arithmetic", "Compute: 5 + 9 = ?", "14"),
    ("arithmetic", "Compute: 11 - 4 = ?", "7"),
    ("arithmetic", "Compute: 3 * 4 = ?", "12"),
    ("backwards", "Write backwards: cat", "tac"),
    ("backwards", "Write backwards: sun", "nus"),
    ("backwards", "Write backwards: lamp", "pmal"),
    ("backwards", "Write backwards: blue", "eulb"),
    ("sequence", "Continue: 1, 3, 5, ?", "7"),
    ("sequence", "Continue: 5, 10, 15, ?", "20"),
    ("sequence", "Continue: 10, 8, 6, ?", "4"),
    ("sequence", "Continue: 3, 6, 9, ?", "12"),
)
ARMS = ("baseline", "candidate")
MIN_GAIN = 3
MAX_DURATION_RATIO = 1.5


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def finite(value):
    return value if type(value) in (int, float) and math.isfinite(value) else None


def summarize(rows):
    by_arm = {}
    for arm in ARMS:
        arm_rows = [r for r in rows if r["arm"] == arm]
        cats = {}
        for category in ("arithmetic", "backwards", "sequence"):
            xs = [r for r in arm_rows if r["category"] == category]
            cats[category] = {"correct": sum(r["correct_exact"] for r in xs), "total": len(xs)}
        durations = [r["duration_s"] for r in arm_rows if r["duration_s"] is not None]
        by_arm[arm] = {
            "correct": sum(r["correct_exact"] for r in arm_rows),
            "total": len(arm_rows), "categories": cats,
            "mean_duration_s": sum(durations) / len(durations) if len(durations) == len(arm_rows) and durations else None,
            "field_supported": sum(r["field_supported"] for r in arm_rows),
        }
    base, cand = by_arm["baseline"], by_arm["candidate"]
    duration_ratio = (
        cand["mean_duration_s"] / base["mean_duration_s"]
        if base["mean_duration_s"] and cand["mean_duration_s"] is not None else None
    )
    gain = cand["correct"] - base["correct"]
    category_no_regress = all(
        cand["categories"][cat]["correct"] >= base["categories"][cat]["correct"]
        for cat in ("arithmetic", "backwards", "sequence")
    )
    return {
        "arms": by_arm, "gain": gain, "category_no_regress": category_no_regress,
        "candidate_duration_ratio": duration_ratio,
        "thresholds": {"minimum_exact_gain": MIN_GAIN, "maximum_duration_ratio": MAX_DURATION_RATIO},
    }


def supported(summary, rows, process_reaped, remaining_pids):
    a = summary["arms"]
    ratio = summary["candidate_duration_ratio"]
    return bool(
        len(rows) == 24
        and a["baseline"]["total"] == 12 and a["candidate"]["total"] == 12
        and summary["gain"] >= MIN_GAIN
        and summary["category_no_regress"]
        and ratio is not None and ratio <= MAX_DURATION_RATIO
        and all(r["status"] == "FINAL" and r["field_supported"] and r["can_train_body"] is False for r in rows)
        and process_reaped is True and not remaining_pids
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
        "revision": "RUN382_PINNED_C3_PROMPT_ABLATION_V1",
        "evidence_level": "LINUX_NATIVE_C3_ONLY",
        "status": "STARTED",
        "model_sha256": sha256(model),
        "binary_sha256": sha256(binary),
        "baseline_system_prompt": SYS,
        "candidate_system_prompt": CANDIDATE_SYS,
        "case_count": len(CASES),
        "rows": [], "native_plumbing_pass": False,
        "prompt_utility_supported": False, "can_train_body": False,
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
        deadline = time.monotonic() + 600.0
        for index, (category, prompt, expected) in enumerate(CASES):
            order = ARMS if index % 2 == 0 else tuple(reversed(ARMS))
            for arm in order:
                system_prompt = SYS if arm == "baseline" else CANDIDATE_SYS
                text = "".join(runner.generate([
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                ], cancel, deadline, max_tokens=40, schema=SCHEMA, seed=13,
                    confidence_field="answer"))
                m = dict(runner.last_metrics)
                tc = m.get("token_confidence") or {}
                answer = extract(text)
                conf, conf_src = confidence(m)
                field_ok = (
                    conf_src in ("field_min_prob", "field_mean_prob")
                    and type(tc.get("field_tokens")) is int and tc["field_tokens"] > 0
                    and conf > 0
                )
                report["rows"].append({
                    "index": index, "category": category, "prompt": prompt,
                    "expected": expected, "arm": arm, "answer": answer[:200],
                    "correct_exact": answer.strip().casefold() == expected.casefold(),
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
                len(report["rows"]) == 24
                and all(r["status"] == "FINAL" and r["can_train_body"] is False for r in report["rows"])
                and report.get("process_reaped") is True
                and not report.get("remaining_pids")
            )
            report["prompt_utility_supported"] = supported(
                report["summary"], report["rows"],
                report.get("process_reaped"), report.get("remaining_pids")
            )
            report["status"] = (
                "RUN382_NATIVE_PROMPT_SUPPORTED" if report["prompt_utility_supported"]
                else "RUN382_NATIVE_PROMPT_NOT_SUPPORTED"
            )
        report_path.parent.mkdir(parents=True, exist_ok=True)
        atomic_write(report_path, dumps(report))
        print("RUN382_REPORT=" + json.dumps(report, sort_keys=True, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
