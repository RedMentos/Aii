"""Run369 pinned Linux-native C3 + AG12 solver probe.

No mock inference, training, model download or approval changes. The workflow
provides verified public GGUF and llama-server paths; this script runs them.
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


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


class SingleNativePool:
    def __init__(self, runner):
        self.runner = runner

    def get(self, role):
        if role != "C3_LANGUAGE":
            raise ValueError("Only C3_LANGUAGE is in the pinned native probe")
        return self.runner


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
        "revision": "RUN369_PINNED_C3_NATIVE_V1",
        "evidence_level": "LINUX_NATIVE_C3_ONLY",
        "status": "STARTED",
        "model_sha256": sha256(model),
        "binary_sha256": sha256(binary),
        "native_model_loaded": False,
        "native_solver_executed": False,
        "can_train_body": False,
        "step2_exit": False,
        "b3_promoted": False,
        "jepa_weight_promoted": False,
        "phone_measured": False,
    }
    runner = None
    try:
        cfg = initialize(home)
        cfg.update(context_tokens=512, answer_tokens=32, threads=2, temperature=0.0,
                   native_cache_ram_mb=32, native_ctx_checkpoints=2, offer_logprobs=True)
        os.environ["V13_LLAMA_SERVER"] = str(binary)
        runner = LlamaRunner(home, "C3_LANGUAGE", model, cfg)
        cancel = threading.Event()
        deadline = time.monotonic() + 180.0
        text = "".join(runner.generate([
            {"role": "system", "content": "Answer briefly in plain text."},
            {"role": "user", "content": "What is two plus two?"},
        ], cancel, deadline, max_tokens=24))
        m1 = dict(runner.last_metrics)
        if not text.strip():
            raise AssertionError("Native C3 plain generation returned no visible text")
        if m1.get("status") != "FINAL" or m1.get("CAN_TRAIN_BODY") is not False:
            raise AssertionError("Native C3 did not complete a read-only FINAL generation")
        if not isinstance(m1.get("duration_s"), (float, int)) or not math.isfinite(m1["duration_s"]):
            raise AssertionError("Native C3 generation timing missing/nonfinite")
        report["native_model_loaded"] = True
        report["plain_generation"] = {
            "text": text[:200],
            "generated_tokens": m1.get("generated_tokens"),
            "duration_s": m1.get("duration_s"),
            "ttft_s": m1.get("ttft_s"),
            "sampled_peak_rss_bytes": m1.get("sampled_peak_rss_bytes"),
            "resource_sample_count": m1.get("resource_sample_count"),
            "status": m1.get("status"),
        }
        solver = BodySolver(SingleNativePool(runner), ("C3_LANGUAGE",), cfg, name="run369_native_c3", item_seconds=90)
        answer = solver.ask("C3_LANGUAGE", {"prompt": "Compute 7 + 5. Reply with the result only."},
                            cancel=cancel, deadline=deadline)
        m2 = dict(runner.last_metrics)
        if not answer["answer"].strip():
            raise AssertionError("Native AG12 grammar returned an empty answer")
        if not math.isfinite(answer["confidence"]) or not 0.0 <= answer["confidence"] <= 1.0:
            raise AssertionError("Native AG12 confidence nonfinite/out of range")
        if answer["confidence_source"] == "none":
            raise AssertionError("No native answer-token confidence was observed")
        if m2.get("status") != "FINAL" or m2.get("CAN_TRAIN_BODY") is not False:
            raise AssertionError("Native AG12 generation did not finish read-only")
        report["native_solver_executed"] = True
        report["ag12_solver"] = {
            "answer": answer["answer"][:200],
            "confidence": answer["confidence"],
            "confidence_source": answer["confidence_source"],
            "generated_tokens": m2.get("generated_tokens"),
            "duration_s": m2.get("duration_s"),
            "ttft_s": m2.get("ttft_s"),
            "sampled_peak_rss_bytes": m2.get("sampled_peak_rss_bytes"),
            "status": m2.get("status"),
        }
        report["status"] = "LINUX_NATIVE_C3_SOLVER_PASS"
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
        report_path.parent.mkdir(parents=True, exist_ok=True)
        atomic_write(report_path, dumps(report))
        print("RUN369_REPORT=" + json.dumps(report, sort_keys=True, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
