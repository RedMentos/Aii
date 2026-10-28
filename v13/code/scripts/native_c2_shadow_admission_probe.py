"""Real pinned Needle3 route96 SHADOW admission probe; no Runtime route application.

Frozen author-labelled corpus is evaluation only. Every failed native attempt is
kept. This is Linux native parser evidence, not a calibrated C2 route-quality PASS.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import threading
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from v13 import c2_route_admission_shadow as admission
from v13.cognition import scaffold_route
from v13.common import atomic_write, dumps
from v13.config import initialize
from v13.control_calibration_worker import observation
from v13.runtime import Runtime

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_ITEMS_SHA256 = "54f3da390fb79c3f966edd61d3390d94dc59d850987174c644ef45ef531a54e6"


def corpus():
    data = json.loads((ROOT / "specs/c2-benchmark.json").read_text())
    raw = json.dumps(data["items"], ensure_ascii=False, sort_keys=True).encode()
    if (data["items_sha256"] != EXPECTED_ITEMS_SHA256
            or hashlib.sha256(raw).hexdigest() != EXPECTED_ITEMS_SHA256
            or len(data["items"]) != 96
            or len({item["id"] for item in data["items"]}) != 96):
        raise ValueError("Frozen C2 route96 corpus changed")
    return data


def _verified(models):
    rows = models.verify(deep=True)
    if not rows or not all(isinstance(v, dict) and v.get("ok") is True
                           and v.get("hash_checked") is True
                           for v in rows.values()):
        raise ValueError("Pinned model deep-hash verification failed")
    return {k: {"ok": v["ok"], "hash_checked": v["hash_checked"],
                "revision": v.get("revision"), "errors": v.get("errors", [])}
            for k, v in rows.items()}


def _peak_rss(pid):
    if not pid:
        return None
    try:
        for line in Path(f"/proc/{pid}/status").read_text().splitlines():
            if line.startswith("VmHWM:"):
                return int(line.split()[1]) * 1024
    except (OSError, ValueError, IndexError):
        pass
    return None


def run(installed_home, output):
    data = corpus()
    report = {
        "schema": "v13.c2.shadow_native96_probe.v1",
        "status": "RUNNING", "host": os.uname().machine,
        "corpus_sha256": EXPECTED_ITEMS_SHA256,
        "source_revision": admission.REVISION, "seed": 13,
        "scope": "LINUX_NATIVE_C2_PARSER_SHADOW_ONLY",
        "age_authority": 0, "weight_updates": False,
        "runtime_route_modified": False, "redmi_measured": False,
        "rows": [], "native_attempts": 0, "valid_native": 0,
    }

    def save():
        atomic_write(output, dumps(report))

    save()
    with tempfile.TemporaryDirectory(prefix="v13-c2-shadow-native-") as folder:
        home = Path(folder)
        initialize(home)
        for name in ("models", "bin"):
            shutil.rmtree(home / name)
            (home / name).symlink_to(installed_home / name, target_is_directory=True)
        shutil.copyfile(installed_home / "config/models.json", home / "config/models.json")
        r = Runtime(home)
        cancel = threading.Event()
        try:
            if (r.cfg["learning_mode"] != "RECORD_ONLY"
                    or r.cfg["system_stage"] != 0
                    or r.learner.active("control_calibration") is not None):
                raise ValueError("Fresh Age0 no-approved-calibration required")
            r.sleep.cycle.set_policy("enabled", "off")
            before = _verified(r.models)
            report["model_hashes_before"] = before
            save()
            r.needle.load(cancel, time.monotonic() + 120)
            for item in data["items"]:
                start = time.monotonic()
                row = {
                    "id": item["id"], "label": item["label"],
                    "text_sha256": hashlib.sha256(item["text"].encode()).hexdigest(),
                    "scaffold": scaffold_route(item["text"]),
                    "native_attempted": True, "native_returned": False,
                    "native_valid": False, "native_route": None,
                    "native_confidence": None, "native_ambiguous": None,
                    "native_proposal_count": None, "error_type": None,
                }
                report["native_attempts"] += 1
                try:
                    raw = r.needle.control(item["text"], cancel, time.monotonic() + 30)
                    row["native_returned"] = True
                    row["native_metrics"] = dict(r.needle.last_metrics)
                    try:
                        obs = observation(raw)
                        row.update(native_valid=True, native_route=obs["route"],
                                   native_confidence=obs["raw_confidence"],
                                   native_ambiguous=obs["ambiguous"],
                                   native_proposal_count=obs["proposal_count"])
                        report["valid_native"] += 1
                    except (ValueError, TypeError, KeyError) as exc:
                        row["error_type"] = "validation:" + type(exc).__name__
                    decision = admission.evaluate(row["scaffold"], raw, None)
                except Exception as exc:
                    row["error_type"] = type(exc).__name__
                    row["native_metrics"] = dict(r.needle.last_metrics)
                    decision = admission.evaluate(row["scaffold"], None, None)
                row["decision"] = decision
                row["duration_s"] = round(time.monotonic() - start, 6)
                row["peak_worker_rss_bytes"] = _peak_rss(r.needle.proc.pid if r.needle.proc else None)
                report["rows"].append(row)
                save()
            after = _verified(r.models)
            report["model_hashes_after"] = after
            report["model_hashes_unchanged"] = before == after
        finally:
            try:
                r.close()
            finally:
                report["process_reaped"] = not r.needle.pids()
                save()
    report["all_rows_recorded"] = len(report["rows"]) == 96
    report["all_shadow_veto"] = all(
        not row["decision"]["would_admit"]
        and row["decision"]["applied"] is False
        and row["decision"]["age_authority"] == 0
        and row["decision"]["model_called"] is False
        and row["decision"]["weight_updates"] is False
        for row in report["rows"])
    ok = (report["all_rows_recorded"] and report["all_shadow_veto"]
          and report["native_attempts"] == 96 and report["valid_native"] >= 1
          and report.get("model_hashes_unchanged") is True
          and report.get("process_reaped") is True)
    report["status"] = ("PASS_SCOPED_WITH_NATIVE_NEGATIVES" if ok and report["valid_native"] < 96
                        else "PASS_SCOPED" if ok else "FAIL")
    save()
    return report


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--installed-home", required=True)
    p.add_argument("--out", required=True)
    args = p.parse_args(argv)
    installed = Path(args.installed_home).resolve()
    out = Path(args.out).resolve()
    if not installed.is_dir() or not (installed / "config/models.json").is_file():
        raise ValueError("Existing pinned installed home required")
    if not out.parent.is_dir() or out.exists():
        raise ValueError("Fresh report path required")
    report = run(installed, out)
    print(json.dumps({k: report[k] for k in
                      ("status", "native_attempts", "valid_native",
                       "all_rows_recorded", "all_shadow_veto", "process_reaped")},
                     sort_keys=True))
    return 0 if report["status"].startswith("PASS_SCOPED") else 2


if __name__ == "__main__":
    raise SystemExit(main())
