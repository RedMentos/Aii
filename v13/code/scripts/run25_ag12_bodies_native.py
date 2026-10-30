"""Run25: two distinct pinned Linux-native body AG12 observations, serial and non-promoting.

Original seed13 German/English AG12 suites and solver are unchanged.
No training, holdout prompts, private data, Age promotion, or phone claim.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import time
from urllib.parse import urlsplit

from v13.agi import hub
from v13.agi import solver as sv
from v13.agi.generality import build_suite
from v13.bootstrap import extract
from v13.common import atomic_write, dumps, file_hash
from v13.config import initialize
from v13.models import ModelManager, catalog, download_file, platform_tag
from v13.runtime import Runtime

RUNNER_TAG = "b10964"
RUNNER_SHA = "9abf88aea48a55d0f80edb1ee20220b186848cca0b4e919d71518cfd7ca67443"
RUNNER_BYTES = 16825086
DEADLINE_S = 720
BODIES = {
    "b1": {
        "key": "body", "role": "B1_DETAIL",
        "id": "LiquidAI/LFM2.5-1.2B-Instruct-GGUF",
        "revision": "6767265158422fb8a19c62ceb45f16f05363615b",
        "license": "LFM Open License 1.0", "bytes": 695755488,
        "sha": "bb741ebb106d543e9de114b843a3d3d73d51c74b5801e69da2abde821a0cb3e1",
    },
    "b2": {
        "key": "gist", "role": "B2_GIST",
        "id": "ggml-org/Qwen3.5-0.8B-GGUF",
        "revision": "8fea620810c4afa23dd6443f999a48574c1611a3",
        "license": "Apache-2.0", "bytes": 563036064,
        "sha": "57d1997790d1744fba5b40a7317df71ea5e2acee28c47e78f0cce39c0703f8cf",
    },
}


def _official_url(value, *, model=False):
    parsed = urlsplit(value)
    return (parsed.scheme == "https" and not parsed.username and not parsed.password
            and not parsed.query and not parsed.fragment and parsed.port is None
            and parsed.hostname == ("huggingface.co" if model else "github.com"))


def pinned_catalog():
    specs = catalog()
    runner = specs["runner"]["linux_binaries"]["linux-x86_64"]
    if (specs["runner"]["tag"] != RUNNER_TAG
            or runner["size"] != RUNNER_BYTES or runner["sha256"] != RUNNER_SHA
            or not _official_url(runner["url"])):
        raise ValueError("RUN25_RUNNER_PIN_RED")
    selected = {}
    for name, expected in BODIES.items():
        model = specs["models"][expected["key"]]
        file = model["files"][0]
        if (model["model_id"] != expected["id"]
                or model["revision"] != expected["revision"]
                or model["license_id"] != expected["license"]
                or model["main_file"] != file["local_name"]
                or len(model["files"]) != 1
                or file["size"] != expected["bytes"]
                or file["sha256"] != expected["sha"]
                or not _official_url(file["url"], model=True)
                or "/resolve/" + expected["revision"] + "/" not in file["url"]):
            raise ValueError("RUN25_" + name.upper() + "_MODEL_PIN_RED")
        selected[name] = model
    if selected["b1"]["model_id"] == selected["b2"]["model_id"]:
        raise ValueError("RUN25_DISTINCT_BODIES_REQUIRED")
    return runner, selected


def install(home, name):
    expected = BODIES[name]
    runner_spec, _ = pinned_catalog()
    initialize(home)
    manager = ModelManager(home)
    manager.install(expected["key"])
    model = manager.path_for(expected["role"])
    if file_hash(model) != expected["sha"]:
        raise ValueError("RUN25_MODEL_BYTES_RED")
    archive = home / "tmp/llama-native.tar.gz"
    download_file(runner_spec, archive)
    if file_hash(archive) != RUNNER_SHA:
        raise ValueError("RUN25_RUNNER_BYTES_RED")
    dest = home / "bin" / RUNNER_TAG
    extract(archive, dest)
    servers = [p for p in dest.rglob("llama-server") if p.is_file()]
    if len(servers) != 1:
        raise ValueError("RUN25_UNIQUE_RUNNER_REQUIRED")
    server = servers[0]
    server.chmod(0o700)
    link = home / "bin/llama-server"
    if link.exists() or link.is_symlink():
        raise FileExistsError("RUN25_FRESH_RUNNER_REQUIRED")
    link.symlink_to(server)
    version = subprocess.run([str(link), "--version"], capture_output=True,
                             text=True, timeout=15)
    if version.returncode:
        raise RuntimeError("RUN25_RUNNER_VERSION_RED:" + version.stderr[-200:])
    atomic_write(home / "config/runner.json", dumps({
        "tag": RUNNER_TAG, "platform": platform_tag(),
        "binary_sha256": file_hash(link),
        "version": (version.stdout + version.stderr).strip(),
        "phone_runner_proof": None,
    }))
    return model, archive, link


def _rows_valid(rows, lang):
    suite = build_suite(seed=13, lang=lang)
    if (type(rows) is not dict or rows.get("status") != "DONE"
            or rows.get("items") != 88 or rows.get("suite_hash") != suite["hash"]
            or type(rows.get("results")) is not list or len(rows["results"]) != 88):
        return False
    for expected, item in zip(suite["items"], rows["results"]):
        if (type(item) is not dict or set(item) != {"id", "correct", "confidence"}
                or item["id"] != expected["id"]
                or type(item["correct"]) is not int or item["correct"] not in (0, 1)
                or type(item["confidence"]) not in (int, float)
                or not 0 <= item["confidence"] <= 1):
            return False
    return True


def observe_body(root, out, name):
    """One fresh Store and exactly one installed native model; always close."""
    expected = BODIES[name]
    home = root / name
    target = out / name
    if home.exists() or target.exists():
        raise FileExistsError("RUN25_FRESH_PATHS_REQUIRED")
    target.mkdir()
    record = {
        "model_id": expected["id"], "revision": expected["revision"],
        "role": expected["role"], "model_sha256": None,
        "runner_tar_sha256": None, "runner_binary_sha256": None,
        "runs": {}, "closed": False, "process_reaped": False,
        "no_events": False, "no_messages": False, "status": "INCOMPLETE",
    }
    runtime = None
    began = time.monotonic()
    try:
        model, archive, binary = install(home, name)
        record.update(model_sha256=file_hash(model),
                      runner_tar_sha256=file_hash(archive),
                      runner_binary_sha256=file_hash(binary))
        runtime = Runtime(home)
        runtime.sleep.cycle.set_policy("enabled", "off")
        cfg = runtime.cfg
        if (cfg["learning_mode"] != "RECORD_ONLY" or cfg["system_stage"] != 0
                or cfg.get("jepa_weight", 0) != 0 or cfg["latents_enabled"]):
            raise ValueError("RUN25_AGE0_NEGATIVE_GATE_RED")
        if runtime.models.path_for(expected["role"]) != model:
            raise ValueError("RUN25_ROLE_MODEL_BINDING_RED")
        for other in ("C3_LANGUAGE", "B2_GIST" if name == "b1" else "B1_DETAIL"):
            try:
                runtime.models.path_for(other)
            except Exception:
                pass
            else:
                raise ValueError("RUN25_CROSS_ROLE_INSTALLED_RED")
        growth = hub(runtime)
        events_before = runtime.store.one("SELECT COUNT(*) n FROM events")["n"]
        messages_before = runtime.store.one("SELECT COUNT(*) n FROM messages")["n"]
        for lang in ("de", "en"):
            start = time.monotonic()
            result = sv.run(growth, runtime, name, lang=lang, label="run25-linux-native",
                            deadline=time.monotonic() + DEADLINE_S)
            record["runs"][lang] = result | {"elapsed_s": round(time.monotonic() - start, 3)}
            exported = home / "exports" / ("generality-last-de.json" if lang == "de" else "generality-last.json")
            if exported.is_file():
                rows = json.loads(exported.read_text(encoding="utf-8"))
                if not _rows_valid(rows, lang):
                    raise ValueError("RUN25_" + lang.upper() + "_ROWS_RED")
                shutil.copy2(exported, target / ("AG12_" + lang.upper() + "_ROWS.json"))
            if (result["status"] != "DONE" or result["roles"] != [expected["role"]]
                    or result["stats"].get(expected["role"], {}).get("items") != 88
                    or result["stats"][expected["role"]].get("errors") != 0):
                break
        record["no_events"] = runtime.store.one("SELECT COUNT(*) n FROM events")["n"] == events_before
        record["no_messages"] = runtime.store.one("SELECT COUNT(*) n FROM messages")["n"] == messages_before
        record["native_calls"] = sum(
            r.get("stats", {}).get(expected["role"], {}).get("items", 0)
            for r in record["runs"].values())
    except Exception as exc:
        record["error"] = type(exc).__name__ + ": " + str(exc)[:300]
    finally:
        if runtime is not None:
            try:
                runtime.close()
                record["closed"] = runtime.closed is True
                record["process_reaped"] = not runtime.pool.pids()
            except Exception as exc:
                record["close_error"] = type(exc).__name__ + ": " + str(exc)[:200]
        record["elapsed_s"] = round(time.monotonic() - began, 3)
        record["status"] = ("DONE" if (
            record.get("error") is None and record["closed"] and record["process_reaped"]
            and record["no_events"] and record["no_messages"]
            and record.get("native_calls") == 176
            and all(record["runs"].get(lang, {}).get("status") == "DONE"
                    and (target / ("AG12_" + lang.upper() + "_ROWS.json")).is_file()
                    for lang in ("de", "en"))) else "RED")
        (target / "REPORT.json").write_text(
            json.dumps(record, sort_keys=True, indent=2, allow_nan=False) + "\n",
            encoding="utf-8")
    return record


def run(root, out):
    root, out = Path(root), Path(out)
    if platform.system() != "Linux" or platform.machine().lower() not in ("x86_64", "amd64"):
        raise ValueError("RUN25_LINUX_X86_64_ONLY")
    if root.exists() or out.exists():
        raise FileExistsError("RUN25_FRESH_PATHS_REQUIRED")
    pinned_catalog()
    out.mkdir(parents=True)
    report = {
        "schema": "v13.run25.ag12_distinct_bodies_linux_native.v1",
        "evidence_kind": "LINUX_NATIVE_B1_B2_AG12_ONLY",
        "platform": platform.platform(),
        "seed": 13, "language_order": ["de", "en"],
        "per_language_deadline_s": DEADLINE_S,
        "models": {}, "expected_native_calls": 352,
        "learning_mode": "RECORD_ONLY", "jepa_weight": 0,
        "b3_promoted": False, "step2_promoted": False,
        "body_jepa_promoted": False, "redmi_measured": False,
        "learned_german_transfer_proven": False,
        "whole_system_complete": False,
    }
    for name in ("b1", "b2"):
        try:
            report["models"][name] = observe_body(root, out, name)
        except Exception as exc:
            report["models"][name] = {"status": "RED", "error":
                                      type(exc).__name__ + ": " + str(exc)[:300]}
    report["native_calls"] = sum(r.get("native_calls", 0)
                                 for r in report["models"].values())
    report["status"] = ("DONE" if report["native_calls"] == 352
                        and all(r.get("status") == "DONE"
                                for r in report["models"].values()) else "RED")
    (out / "REPORT.json").write_text(
        json.dumps(report, sort_keys=True, indent=2, allow_nan=False) + "\n",
        encoding="utf-8")
    if report["status"] != "DONE":
        raise RuntimeError("RUN25_NATIVE_INCOMPLETE_OR_RED; closed raw retained")
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    result = run(args.root, args.out)
    print(json.dumps({"evidence_kind": result["evidence_kind"],
                      "native_calls": result["native_calls"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
