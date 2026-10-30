"""Run27 real native AG12 three-organ BodySolver vote; never a live JEF proof."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import platform
import shutil
import subprocess
import time

from scripts.run25_ag12_bodies_native import (
    BODIES, RUNNER_BYTES, RUNNER_SHA, RUNNER_TAG, pinned_catalog,
)
from scripts.run24_ag12_german_c3_native import MODEL_SHA as C3_SHA
from v13.agi import hub
from v13.agi import solver as sv
from v13.agi.generality import build_suite
from v13.bootstrap import extract
from v13.common import atomic_write, dumps, file_hash
from v13.config import initialize
from v13.models import ModelManager, download_file, platform_tag
from v13.runtime import Runtime

DEADLINE_S = 1200
RUNNER_BINARY_SHA = "79e312188dc1d75c28201771f106e91de470b5cebdd838d31bb4db25eecf5d39"
ROLES = ("B1_DETAIL", "B2_GIST", "C3_LANGUAGE")


def install(home):
    runner_spec, _ = pinned_catalog()
    initialize(home)
    manager = ModelManager(home)
    for key in ("language", "body", "gist"):
        manager.install(key)
    expected = {
        "C3_LANGUAGE": C3_SHA,
        "B1_DETAIL": BODIES["b1"]["sha"],
        "B2_GIST": BODIES["b2"]["sha"],
    }
    paths = {}
    for role, sha in expected.items():
        path = manager.path_for(role)
        if file_hash(path) != sha:
            raise ValueError("RUN27_" + role + "_MODEL_BYTES_RED")
        paths[role] = path
    if len({p.resolve() for p in paths.values()}) != 3:
        raise ValueError("RUN27_DISTINCT_MODEL_PATHS_RED")
    archive = home / "tmp/llama-native.tar.gz"
    download_file(runner_spec, archive)
    if archive.stat().st_size != RUNNER_BYTES or file_hash(archive) != RUNNER_SHA:
        raise ValueError("RUN27_RUNNER_BYTES_RED")
    dest = home / "bin" / RUNNER_TAG
    extract(archive, dest)
    servers = [p for p in dest.rglob("llama-server") if p.is_file()]
    if len(servers) != 1:
        raise ValueError("RUN27_UNIQUE_NATIVE_RUNNER_RED")
    server = servers[0]
    server.chmod(0o700)
    link = home / "bin/llama-server"
    if link.exists() or link.is_symlink():
        raise FileExistsError("RUN27_FRESH_RUNNER_REQUIRED")
    link.symlink_to(server)
    version = subprocess.run([str(link), "--version"], capture_output=True,
                             text=True, timeout=15)
    if version.returncode:
        raise RuntimeError("RUN27_RUNNER_VERSION_RED:" + version.stderr[-200:])
    atomic_write(home / "config/runner.json", dumps({
        "tag": RUNNER_TAG, "platform": platform_tag(),
        "binary_sha256": file_hash(link),
        "version": (version.stdout + version.stderr).strip(),
        "phone_runner_proof": None,
    }))
    return paths, archive, link


def _rows_valid(rows, lang):
    suite = build_suite(seed=13, lang=lang)
    if (type(rows) is not dict or rows.get("status") != "DONE"
            or rows.get("items") != 88 or rows.get("suite_hash") != suite["hash"]
            or type(rows.get("results")) is not list or len(rows["results"]) != 88):
        return False
    for row, item in zip(rows["results"], suite["items"]):
        if (type(row) is not dict or set(row) != {"id", "correct", "confidence"}
                or row["id"] != item["id"]
                or type(row["correct"]) is not int or row["correct"] not in (0, 1)
                or type(row["confidence"]) not in (int, float)
                or not 0 <= row["confidence"] <= 1):
            return False
    return True


def run(home, out):
    home, out = Path(home), Path(out)
    if platform.system() != "Linux" or platform.machine().lower() not in ("x86_64", "amd64"):
        raise ValueError("RUN27_LINUX_X86_64_ONLY")
    if home.exists() or out.exists():
        raise FileExistsError("RUN27_FRESH_PATHS_REQUIRED")
    pinned_catalog()
    out.mkdir(parents=True)
    report = {
        "schema": "v13.run27.ag12_three_organ_vote_linux_native.v1",
        "evidence_kind": "LINUX_NATIVE_AG12_BODYSOLVER_VOTE_ONLY",
        "platform": platform.platform(),
        "seed": 13, "language_order": ["de", "en"],
        "per_language_deadline_s": DEADLINE_S,
        "roles": list(ROLES),
        "model_sha256": {}, "runner_tar_sha256": None,
        "runner_binary_sha256": None,
        "native_role_calls": 0, "voted_items": 0, "runs": {},
        "exclusive_native_residency": False,
        "runtime_closed": False, "process_reaped": False,
        "no_events": False, "no_messages": False,
        "learning_mode": "RECORD_ONLY", "jepa_weight": 0,
        "step2_promoted": False, "b3_promoted": False,
        "body_jepa_promoted": False, "redmi_measured": False,
        "learned_german_transfer_proven": False,
        "actual_live_jef_fusion_proven": False,
        "whole_system_complete": False,
    }
    runtime = None
    began = time.monotonic()
    try:
        paths, archive, binary = install(home)
        report["model_sha256"] = {role: file_hash(path) for role, path in paths.items()}
        report["runner_tar_sha256"] = file_hash(archive)
        report["runner_binary_sha256"] = file_hash(binary)
        if (report["model_sha256"] != {
                "C3_LANGUAGE": C3_SHA,
                "B1_DETAIL": BODIES["b1"]["sha"],
                "B2_GIST": BODIES["b2"]["sha"]}
                or report["runner_tar_sha256"] != RUNNER_SHA
                or report["runner_binary_sha256"] != RUNNER_BINARY_SHA):
            raise ValueError("RUN27_POST_INSTALL_PIN_RED")
        runtime = Runtime(home)
        runtime.sleep.cycle.set_policy("enabled", "off")
        cfg = runtime.cfg
        if (cfg["learning_mode"] != "RECORD_ONLY" or cfg["system_stage"] != 0
                or cfg.get("jepa_weight", 0) != 0 or cfg["latents_enabled"]):
            raise ValueError("RUN27_AGE0_NEGATIVE_GATE_RED")
        for role, path in paths.items():
            if runtime.models.path_for(role) != path:
                raise ValueError("RUN27_ROLE_BINDING_RED")
        # AG12 measurement control: one native process resident at a time.
        # Does not change the production BodyFabric or live JEF route.
        runtime.pool.unload()
        runtime.pool.fabric = None
        report["exclusive_native_residency"] = True
        growth = hub(runtime)
        before_events = runtime.store.one("SELECT COUNT(*) n FROM events")["n"]
        before_messages = runtime.store.one("SELECT COUNT(*) n FROM messages")["n"]
        for lang in ("de", "en"):
            started = time.monotonic()
            result = sv.run(growth, runtime, "v13", lang=lang,
                            label="run27-three-organ-vote",
                            deadline=time.monotonic() + DEADLINE_S)
            report["runs"][lang] = result | {"elapsed_s": round(time.monotonic()-started, 3)}
            export = home / "exports" / ("generality-last-de.json" if lang == "de" else "generality-last.json")
            if export.is_file():
                rows = json.loads(export.read_text(encoding="utf-8"))
                if not _rows_valid(rows, lang):
                    raise ValueError("RUN27_" + lang.upper() + "_ROWS_RED")
                shutil.copy2(export, out / ("AG12_" + lang.upper() + "_ROWS.json"))
            if (result["status"] != "DONE" or result["roles"] != list(ROLES)
                    or any(result["stats"].get(role, {}).get("items") != 88
                           or result["stats"][role].get("errors") != 0
                           for role in ROLES)):
                break
        report["no_events"] = runtime.store.one("SELECT COUNT(*) n FROM events")["n"] == before_events
        report["no_messages"] = runtime.store.one("SELECT COUNT(*) n FROM messages")["n"] == before_messages
        report["native_role_calls"] = sum(
            sum(run.get("stats", {}).get(role, {}).get("items", 0) for role in ROLES)
            for run in report["runs"].values())
        report["voted_items"] = 88 * sum(
            run.get("status") == "DONE" for run in report["runs"].values())
    except Exception as exc:
        report["error"] = type(exc).__name__ + ": " + str(exc)[:300]
    finally:
        if runtime is not None:
            try:
                runtime.close()
                report["runtime_closed"] = runtime.closed is True
                report["process_reaped"] = not runtime.pool.pids()
            except Exception as exc:
                report["close_error"] = type(exc).__name__ + ": " + str(exc)[:200]
        report["elapsed_s"] = round(time.monotonic() - began, 3)
        report["status"] = ("DONE" if (
            report.get("error") is None and report["runtime_closed"]
            and report["process_reaped"] and report["no_events"] and report["no_messages"]
            and report["exclusive_native_residency"]
            and report["native_role_calls"] == 528 and report["voted_items"] == 176
            and all(report["runs"].get(lang, {}).get("status") == "DONE"
                    and (out / ("AG12_" + lang.upper() + "_ROWS.json")).is_file()
                    for lang in ("de", "en"))) else "RED")
        (out / "REPORT.json").write_text(
            json.dumps(report, sort_keys=True, indent=2, allow_nan=False) + "\n",
            encoding="utf-8")
    if report["status"] != "DONE":
        raise RuntimeError("RUN27_NATIVE_INCOMPLETE_OR_RED; closed raw retained")
    return report


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--home", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args(argv)
    r = run(args.home, args.out)
    print(json.dumps({"evidence_kind": r["evidence_kind"],
                      "native_role_calls": r["native_role_calls"],
                      "voted_items": r["voted_items"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
