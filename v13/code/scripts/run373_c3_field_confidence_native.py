"""Run373 preregistered pinned Linux-native C3 answer-field confidence diagnostic.

No model downloads here, no mocks, no learning, no source/seed changes.
Workflow provides hash-verified public GGUF and native binary.
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
from v13.agi.solver import BodySolver
from v13.common import atomic_write, dumps


CASES = (
    ("Compute: 7 + 5 = ?", "12"),
    ("Compute: 9 + 1 = ?", "10"),
    ("Write backwards: dog", "god"),
    ("Continue: 2, 4, 6, ?", "8"),
)
PLAIN = (
    "What is two plus two?",
    "Compute: 7 + 5 = ?",
)


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def finite_number(value):
    return value if type(value) in (int, float) and math.isfinite(value) else None


class SingleNativePool:
    def __init__(self, runner):
        self.runner = runner

    def get(self, role):
        if role != "C3_LANGUAGE":
            raise ValueError("Run373 only owns C3_LANGUAGE")
        return self.runner


def metrics(runner):
    m = dict(runner.last_metrics)
    tc = m.get("token_confidence") or {}
    return {
        "status": m.get("status"),
        "generated_tokens": m.get("generated_tokens"),
        "duration_s": finite_number(m.get("duration_s")),
        "ttft_s": finite_number(m.get("ttft_s")),
        "sampled_peak_rss_bytes": finite_number(m.get("sampled_peak_rss_bytes")),
        "can_train_body": m.get("CAN_TRAIN_BODY"),
        "token_confidence": {
            "field": tc.get("field"),
            "field_tokens": tc.get("field_tokens"),
            "field_min_prob": finite_number(tc.get("field_min_prob")),
            "field_mean_prob": finite_number(tc.get("field_mean_prob")),
            "mean_prob": finite_number(tc.get("mean_prob")),
        },
    }


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
        "revision": "RUN373_PINNED_C3_FIELD_CONFIDENCE_V1",
        "evidence_level": "LINUX_NATIVE_C3_ONLY",
        "status": "STARTED",
        "model_sha256": sha256(model),
        "binary_sha256": sha256(binary),
        "native_plumbing_pass": False,
        "field_confidence_supported": False,
        "can_train_body": False,
        "step2_exit": False,
        "b3_promoted": False,
        "jepa_weight_promoted": False,
        "phone_measured": False,
        "grammar_cases": [],
        "plain_controls": [],
    }
    runner = None
    all_final = True
    try:
        cfg = initialize(home)
        cfg.update(context_tokens=512, answer_tokens=40, threads=2, temperature=0.0,
                   native_cache_ram_mb=32, native_ctx_checkpoints=2, offer_logprobs=True)
        os.environ["V13_LLAMA_SERVER"] = str(binary)
        runner = LlamaRunner(home, "C3_LANGUAGE", model, cfg)
        cancel = threading.Event()
        deadline = time.monotonic() + 180.0
        for prompt in PLAIN:
            text = "".join(runner.generate([
                {"role": "system", "content": "Answer briefly in plain text."},
                {"role": "user", "content": prompt},
            ], cancel, deadline, max_tokens=32))
            m = metrics(runner)
            all_final = all_final and m["status"] == "FINAL" and m["can_train_body"] is False
            report["plain_controls"].append({"prompt": prompt, "text": text[:200], "metrics": m})
        solver = BodySolver(SingleNativePool(runner), ("C3_LANGUAGE",), cfg,
                            name="run373_native_c3", item_seconds=90)
        for prompt, expected in CASES:
            out = solver.ask("C3_LANGUAGE", {"prompt": prompt}, cancel=cancel, deadline=deadline)
            m = metrics(runner)
            answer = out["answer"]
            exact = answer.casefold().strip() == expected.casefold()
            field = m["token_confidence"]
            field_supported = (
                out["confidence_source"] in ("field_min_prob", "field_mean_prob")
                and type(field["field_tokens"]) is int and field["field_tokens"] > 0
                and finite_number(field["field_min_prob"]) is not None
            )
            all_final = all_final and m["status"] == "FINAL" and m["can_train_body"] is False
            report["grammar_cases"].append({
                "prompt": prompt, "expected": expected, "answer": answer[:200],
                "correct_exact": exact, "field_supported": field_supported,
                "confidence": finite_number(out["confidence"]),
                "confidence_source": out["confidence_source"], "metrics": m,
            })
        supported = sum(row["correct_exact"] and row["field_supported"] for row in report["grammar_cases"])
        report["supported_count"] = supported
        report["field_confidence_supported"] = supported >= 3
        report["status"] = "FIELD_CONFIDENCE_SUPPORTED" if supported >= 3 else "FIELD_CONFIDENCE_NOT_SUPPORTED"
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
        report["native_plumbing_pass"] = bool(
            all_final and len(report["plain_controls"]) == 2
            and len(report["grammar_cases"]) == 4
            and report.get("process_reaped") is True and not report.get("remaining_pids")
        )
        if not report["native_plumbing_pass"] and report["status"] != "ERROR":
            report["status"] = "NATIVE_PLUMBING_NOT_SUPPORTED"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        atomic_write(report_path, dumps(report))
        print("RUN373_REPORT=" + json.dumps(report, sort_keys=True, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
