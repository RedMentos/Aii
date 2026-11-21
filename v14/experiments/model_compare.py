"""Read-only, sequential native C3 model comparison for V14-005.

No downloads, installed-manifest edits, model swaps, or production promotion.
Both local GGUFs use the pinned V13 LlamaRunner / llama-server path.
"""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import platform
import shutil
import stat
import statistics
import tempfile
import threading
import time
from pathlib import Path

MANIFEST_PATH = Path(__file__).with_name("model_candidates.json")
ROLE = "C3_LANGUAGE"
TASKS = (
    {"id": "p0_arithmetic_2_plus_2", "prompt": "Compute 2 + 2. Reply with exactly the integer and nothing else.", "expected": "4"},
    {"id": "source_exact_extraction", "prompt": "Read this source: 'Ticket Q7-19 is scheduled for Thursday.' Output only the exact ticket code.", "expected": "Q7-19"},
    {"id": "missing_information_abstention", "prompt": "Source: 'The meeting is on Thursday.' Question: What time is the meeting? If the source does not say, output exactly UNKNOWN.", "expected": "UNKNOWN"},
    {"id": "constraint_reasoning", "prompt": "Budget is 70 euros and the deadline is 6 days. Plan A costs 45 euros and takes 4 days. Plan B costs 65 euros and takes 8 days. Only plans within both limits qualify. Output only A, B, or NONE.", "expected": "A"},
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def has_symlink_component(path: Path) -> bool:
    current = Path(path)
    while True:
        if current.is_symlink():
            return True
        if current.parent == current:
            return False
        current = current.parent


def validate_gguf(path: Path, spec: dict) -> dict:
    path = Path(path).expanduser()
    if has_symlink_component(path):
        raise ValueError("model path contains a symlink")
    if not path.is_file():
        raise FileNotFoundError(str(path))
    if path.stat().st_size != spec["size"]:
        raise ValueError("model size mismatch")
    with path.open("rb") as stream:
        if stream.read(4) != b"GGUF":
            raise ValueError("model is not GGUF")
    digest = sha256_file(path)
    if digest != spec["sha256"]:
        raise ValueError("model SHA256 mismatch")
    return {"file_name": path.name, "size_bytes": spec["size"], "sha256": digest}


def stage_verified_file(source: Path, destination: Path, *, expected_size: int | None = None,
                        expected_sha256: str | None = None) -> dict:
    """Copy an installed artifact into a private lab directory and verify its exact bytes."""
    source = Path(source).expanduser()
    if has_symlink_component(source):
        raise ValueError("artifact source contains a symlink")
    source = source.resolve(strict=True)
    nofollow = getattr(os, "O_NOFOLLOW", None)
    if nofollow is None:
        raise RuntimeError("platform lacks O_NOFOLLOW; safe model staging unavailable")
    source_fd = os.open(source, os.O_RDONLY | nofollow)
    destination = Path(destination)
    created = False
    try:
        before = os.fstat(source_fd)
        if not stat.S_ISREG(before.st_mode):
            raise ValueError("artifact source is not a regular file")
        if expected_size is not None and before.st_size != expected_size:
            raise ValueError("model size mismatch")
        destination_fd = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        created = True
        digest = hashlib.sha256()
        total = 0
        with os.fdopen(destination_fd, "wb") as output:
            while True:
                chunk = os.read(source_fd, 1024 * 1024)
                if not chunk:
                    break
                output.write(chunk)
                digest.update(chunk)
                total += len(chunk)
            output.flush()
            os.fsync(output.fileno())
        after = os.fstat(source_fd)
        current = os.stat(source, follow_symlinks=False)
        identity = lambda item: (
            item.st_dev, item.st_ino, item.st_size, item.st_mtime_ns, item.st_ctime_ns
        )
        if identity(before) != identity(after) or identity(after) != identity(current):
            raise RuntimeError("artifact source changed during staging")
        if total != before.st_size:
            raise RuntimeError("artifact byte count changed during staging")
        digest_hex = digest.hexdigest()
        if expected_size is not None and total != expected_size:
            raise ValueError("model size mismatch")
        if expected_sha256 is not None and digest_hex != expected_sha256:
            raise ValueError("model SHA256 mismatch")
        if destination.stat().st_size != total or sha256_file(destination) != digest_hex:
            raise RuntimeError("staged artifact failed readback verification")
        os.chmod(destination, 0o400)
        return {"file_name": source.name, "size_bytes": total, "sha256": digest_hex}
    except Exception:
        if created:
            destination.unlink(missing_ok=True)
        raise
    finally:
        os.close(source_fd)


def read_candidate_manifest(path: Path) -> dict:
    if has_symlink_component(path) or not path.is_file():
        raise ValueError("candidate manifest missing or symlink")
    value = json.loads(path.read_text(encoding="utf-8"))
    if value.get("schema") != "v14.model-candidates/1":
        raise ValueError("unsupported candidate manifest schema")
    rows = value.get("candidates")
    if not isinstance(rows, list):
        raise ValueError("candidate manifest candidates must be a list")
    by_id = {}
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("id"), str) or row["id"] in by_id:
            raise ValueError("invalid or duplicate candidate id")
        required = ("role", "model_id", "revision", "license_id", "license_url", "file")
        if any(not row.get(key) for key in required):
            raise ValueError("candidate metadata incomplete")
        if len(row["revision"]) != 40 or any(c not in "0123456789abcdef" for c in row["revision"]):
            raise ValueError("candidate revision must be a pinned 40-character SHA")
        file_spec = row["file"]
        if not isinstance(file_spec, dict) or not all(file_spec.get(k) for k in ("local_name", "size", "sha256")):
            raise ValueError("candidate file metadata incomplete")
        if isinstance(file_spec["size"], bool) or not isinstance(file_spec["size"], int) or file_spec["size"] <= 0:
            raise ValueError("candidate file size invalid")
        if len(file_spec["sha256"]) != 64 or any(c not in "0123456789abcdef" for c in file_spec["sha256"]):
            raise ValueError("candidate file SHA256 invalid")
        expected_license_url = "https://huggingface.co/" + row["model_id"] + "/blob/" + row["revision"] + "/LICENSE"
        if row["license_url"] != expected_license_url:
            raise ValueError("candidate license URL must be pinned to the model revision")
        snapshot_sha = row.get("license_snapshot_sha256")
        if not isinstance(snapshot_sha, str) or len(snapshot_sha) != 64 or any(c not in "0123456789abcdef" for c in snapshot_sha):
            raise ValueError("candidate license snapshot SHA256 invalid")
        snapshot_path = row.get("license_snapshot_path")
        if (not isinstance(snapshot_path, str) or not snapshot_path
                or "\\" in snapshot_path or Path(snapshot_path).is_absolute()
                or ".." in Path(snapshot_path).parts):
            raise ValueError("candidate license snapshot path must be relative and traversal-free")
        if not str(row.get("license_snapshot_source", "")).startswith("https://"):
            raise ValueError("candidate license snapshot provenance incomplete")
        by_id[row["id"]] = row
    return by_id


def verify_license_snapshot(manifest_path: Path, row: dict) -> dict:
    """Verify the repository-pinned license text before a model is benchmarked."""
    relative = Path(row["license_snapshot_path"])
    if relative.is_absolute() or ".." in relative.parts or "\\" in row["license_snapshot_path"]:
        raise ValueError("candidate license snapshot path must be relative and traversal-free")
    manifest = Path(manifest_path).expanduser().resolve(strict=True)
    repo_manifest = MANIFEST_PATH.resolve()
    root = Path(__file__).resolve().parents[2] if manifest == repo_manifest else manifest.parent
    snapshot = root / relative
    if has_symlink_component(snapshot) or not snapshot.is_file():
        raise ValueError("candidate license snapshot missing or symlink")
    digest = sha256_file(snapshot)
    if digest != row["license_snapshot_sha256"]:
        raise ValueError("candidate license snapshot SHA256 mismatch")
    return {"sha256": digest, "size_bytes": snapshot.stat().st_size}


def acquire_home_lock(home: Path):
    lock_path = home / "data" / "coordinator.lock"
    if has_symlink_component(lock_path) or not lock_path.is_file():
        raise RuntimeError("V13 coordinator lock missing; use an initialized, idle V13 home")
    handle = lock_path.open("r+")
    try:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError as exc:
        handle.close()
        raise RuntimeError("V13 is already using this home; comparison refused") from exc
    return handle


def environment_name() -> str:
    if os.environ.get("ANDROID_ROOT") or "com.termux" in os.environ.get("PREFIX", ""):
        return "TERMUX_ANDROID"
    if platform.system() == "Linux":
        return "LOCAL_LINUX"
    return platform.system().upper()


def safe_metrics(metrics: dict) -> dict:
    stages = metrics.get("stage_durations_s") if isinstance(metrics.get("stage_durations_s"), dict) else {}
    timings = metrics.get("timings") if isinstance(metrics.get("timings"), dict) else {}
    generated = metrics.get("generated_tokens")
    stream_s = stages.get("stream_s")
    return {
        "status": metrics.get("status", "UNKNOWN"),
        "load_s": stages.get("load_s"),
        "template_s": stages.get("template_s"),
        "prefill_to_first_token_s": stages.get("prefill_to_first_token_s"),
        "stream_s": stream_s,
        "ttft_s": metrics.get("ttft_s"),
        "duration_s": metrics.get("duration_s"),
        "prompt_tokens": metrics.get("prompt_tokens"),
        "generated_tokens": generated,
        "decode_tokens_per_s": generated / stream_s if isinstance(generated, (int, float)) and isinstance(stream_s, (int, float)) and stream_s > 0 else None,
        "prompt_eval_ms": timings.get("prompt_ms"),
        "decode_eval_ms": timings.get("predicted_ms"),
        "sampled_peak_rss_bytes": metrics.get("sampled_peak_rss_bytes"),
        "sampled_peak_pss_bytes": metrics.get("sampled_peak_pss_bytes"),
    }


def verified_runner_binary(runner, expected_binary: Path, *, loaded: bool = False) -> dict:
    """Fail closed unless LlamaRunner is configured to launch the verified binary.

    LlamaRunner honors V13_LLAMA_SERVER before its home/bin default. Compare the
    resolved path after construction and again after load so the report cannot
    attribute a different executable's output to the installed binary.
    """
    attribute = "_loaded_binary" if loaded else "binary"
    configured = getattr(runner, attribute, None)
    if not isinstance(configured, (str, os.PathLike)) or not str(configured):
        raise RuntimeError("LlamaRunner executable identity unavailable")
    try:
        actual = Path(configured).expanduser().resolve(strict=True)
        expected = Path(expected_binary).expanduser().resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise RuntimeError("LlamaRunner executable path cannot be verified") from exc
    if actual != expected:
        raise RuntimeError("LlamaRunner executable differs from verified installed binary")
    if not actual.is_file() or not os.access(actual, os.X_OK):
        raise RuntimeError("LlamaRunner executable is not a regular executable file")
    return {
        "file_name": actual.name,
        "size_bytes": actual.stat().st_size,
        "sha256": sha256_file(actual),
    }


def run_model(runner_cls, lab_home: Path, model_path: Path, cfg: dict,
              timeout_s: float, max_tokens: int, expected_binary: Path,
              expected_binary_info: dict) -> dict:
    runner = runner_cls(lab_home, ROLE, model_path, cfg, purpose="generate")
    cancel = threading.Event()
    rows = []
    release = {"process_reaped": False}
    try:
        runner_binary = verified_runner_binary(runner, expected_binary)
        if runner_binary != expected_binary_info:
            raise RuntimeError("runner executable digest differs from locked preflight")
        loaded_binary = None
        for task in TASKS:
            messages = [
                {"role": "system", "content": "Follow the user's instruction exactly. Do not add a preamble."},
                {"role": "user", "content": task["prompt"]},
            ]
            try:
                output = "".join(runner.generate(
                    messages, cancel, time.monotonic() + timeout_s,
                    max_tokens=max_tokens, seed=cfg.get("seed", 13)))
            except Exception as exc:
                rows.append({"task_id": task["id"], "status": "ERROR", "error_type": type(exc).__name__})
                break
            loaded_binary = verified_runner_binary(runner, expected_binary, loaded=True)
            if loaded_binary != expected_binary_info or loaded_binary != runner_binary:
                raise RuntimeError("loaded LlamaRunner executable changed during comparison")
            metrics = safe_metrics(dict(runner.last_metrics or {}))
            final = metrics["status"] == "FINAL"
            rows.append({
                "task_id": task["id"],
                "status": "FINAL" if final else metrics["status"],
                "exact_match": bool(final and output.strip() == task["expected"]),
                "output_chars": len(output),
                "output_sha256": hashlib.sha256(output.encode("utf-8")).hexdigest(),
                "metrics": metrics,
            })
            if not final:
                break
    finally:
        try:
            release = runner.unload()
        except Exception as exc:
            release = {"process_reaped": False, "error_type": type(exc).__name__}
    complete = len(rows) == len(TASKS) and all(row["status"] == "FINAL" for row in rows)
    ttfts = [r["metrics"].get("ttft_s") for r in rows if isinstance(r.get("metrics", {}).get("ttft_s"), (int, float))]
    durations = [r["metrics"].get("duration_s") for r in rows if isinstance(r.get("metrics", {}).get("duration_s"), (int, float))]
    rss = [r["metrics"].get("sampled_peak_rss_bytes") for r in rows if isinstance(r.get("metrics", {}).get("sampled_peak_rss_bytes"), (int, float))]
    pss = [r["metrics"].get("sampled_peak_pss_bytes") for r in rows if isinstance(r.get("metrics", {}).get("sampled_peak_pss_bytes"), (int, float))]
    exact = sum(1 for r in rows if r.get("exact_match") is True)
    return {
        "status": "INFERENCE_COMPLETE" if complete and release.get("process_reaped") is True else "INFERENCE_PARTIAL",
        "tasks": rows,
        "quality": {"exact_matches": exact, "task_count": len(TASKS), "exact_match_rate": exact / len(TASKS)},
        "summary": {
            "median_ttft_s": statistics.median(ttfts) if ttfts else None,
            "median_total_s": statistics.median(durations) if durations else None,
            "max_sampled_rss_bytes": max(rss) if rss else None,
            "max_sampled_pss_bytes": max(pss) if pss else None,
        },
        "release": {"process_reaped": release.get("process_reaped") is True, "error_type": release.get("error_type")},
        "runner_binary": loaded_binary or runner_binary,
        "runner_launch_verified": loaded_binary is not None,
    }


def compare(home: Path, candidate_id: str, candidate_path: Path | None = None,
            timeout_s: float = 90.0, max_tokens: int = 32, order: str = "baseline-first",
            manifest_path: Path = MANIFEST_PATH, *, model_manager_cls=None,
            runner_cls=None, defaults=None, config_validator=None, catalog_fn=None) -> dict:
    if not 5 <= timeout_s <= 600 or not 8 <= max_tokens <= 128:
        raise ValueError("timeout must be 5..600 seconds and max_tokens 8..128")
    if order not in {"baseline-first", "candidate-first"}:
        raise ValueError("order must be baseline-first or candidate-first")
    raw_home = Path(home).expanduser()
    if has_symlink_component(raw_home):
        raise ValueError("V13 home path contains a symlink")
    home = raw_home.resolve()
    if not home.is_dir():
        raise ValueError("V13 home missing")
    candidates = read_candidate_manifest(Path(manifest_path))
    if candidate_id not in candidates:
        raise ValueError("unknown candidate id")
    candidate = candidates[candidate_id]
    if candidate["role"] != ROLE:
        raise ValueError("this first comparison slice supports C3_LANGUAGE only")
    license_snapshot = verify_license_snapshot(manifest_path, candidate)

    if model_manager_cls is None or defaults is None or config_validator is None or catalog_fn is None or runner_cls is None:
        import sys
        repo_code = Path(__file__).resolve().parents[2] / "v13" / "code"
        if str(repo_code) not in sys.path:
            sys.path.insert(0, str(repo_code))
        if model_manager_cls is None:
            from v13.models import ModelManager as model_manager_cls
        if defaults is None or config_validator is None:
            from v13.config import DEFAULTS, validate
            defaults = defaults or DEFAULTS
            config_validator = config_validator or validate
        if catalog_fn is None:
            from v13.models import catalog as catalog_fn
        if runner_cls is None:
            from v13.runners import LlamaRunner as runner_cls

    # Lock first: all installed settings, registry and model paths are read under it.
    lock = acquire_home_lock(home)
    try:
        settings_path = home / "config" / "settings.json"
        if has_symlink_component(settings_path) or not settings_path.is_file():
            raise RuntimeError("existing V13 config/settings.json required; no initialization or writes performed")
        cfg = dict(defaults)
        cfg.update(json.loads(settings_path.read_text(encoding="utf-8")))
        config_validator(cfg)
        if cfg.get("c3_decode_mode", "server") != "server":
            raise RuntimeError("C3 is not using the standard llama-server path; comparison refused")

        models = model_manager_cls(home, cfg.get("b2_control", "two_body"))
        registry = catalog_fn()
        baseline_spec = registry["models"]["language"]
        if models.revision(ROLE) != baseline_spec["revision"]:
            raise RuntimeError("installed C3 revision differs from the pinned registry baseline")
        baseline_path = Path(models.path_for(ROLE))
        baseline_file = next((f for f in baseline_spec["files"] if f["local_name"] == baseline_spec["main_file"]), None)
        if baseline_file is None:
            raise RuntimeError("registry baseline main file missing")

        candidate_path = Path(candidate_path).expanduser() if candidate_path is not None else home / "models" / "language" / candidate["file"]["local_name"]
        if has_symlink_component(candidate_path):
            raise ValueError("candidate path contains a symlink")
        if not candidate_path.exists():
            return {
                "schema": "v14.model-compare/1", "status": "CANDIDATE_NOT_INSTALLED",
                "role": ROLE, "candidate_id": candidate_id,
                "candidate": {"model_id": candidate["model_id"], "revision": candidate["revision"],
                              "license_id": candidate["license_id"], "license_url": candidate["license_url"],
                              "license_snapshot_sha256": license_snapshot["sha256"],
                              "license_snapshot_verified": True,
                              "expected_size_bytes": candidate["file"]["size"], "expected_sha256": candidate["file"]["sha256"]},
                "download_performed": False, "manifest_mutated": False, "production_swap": False,
                "next_step": "Place the exact pinned GGUF in the isolated lab slot only after separate explicit download consent; then rerun this read-only comparison.",
            }

        binary = home / "bin" / "llama-server"
        if has_symlink_component(binary) or not binary.is_file() or not os.access(binary, os.X_OK):
            raise RuntimeError("installed llama-server missing or not executable")
        binary_resolved = binary.resolve(strict=True)
        override = os.environ.get("V13_LLAMA_SERVER")
        if override:
            try:
                override_resolved = Path(override).expanduser().resolve(strict=True)
            except (OSError, RuntimeError) as exc:
                raise RuntimeError("V13_LLAMA_SERVER override cannot be verified") from exc
            if override_resolved != binary_resolved:
                raise RuntimeError("V13_LLAMA_SERVER override differs from verified installed binary")

        binary_before = binary_resolved.stat()
        binary_info = {
            "file_name": binary_resolved.name,
            "size_bytes": binary_before.st_size,
            "sha256": sha256_file(binary_resolved),
        }
        binary_after = binary_resolved.stat()
        binary_identity = lambda item: (
            item.st_dev, item.st_ino, item.st_size, item.st_mtime_ns, item.st_ctime_ns
        )
        if binary_identity(binary_before) != binary_identity(binary_after):
            raise RuntimeError("installed llama-server changed during preflight")

        # Keep large copies on the V13 data volume, not a possibly RAM-backed /tmp.
        with tempfile.TemporaryDirectory(prefix="v14-model-compare-", dir=str(home / "data")) as tmp:
            lab_home = Path(tmp)
            for folder in ("bin", "logs", "tmp", "config", "models"):
                (lab_home / folder).mkdir()
            (lab_home / "bin" / "llama-server").symlink_to(binary_resolved)

            required_bytes = baseline_file["size"] + candidate["file"]["size"] + 32 * 1024 * 1024
            if shutil.disk_usage(lab_home).free < required_bytes:
                raise RuntimeError("insufficient free disk for two verified model staging copies")

            staged_baseline = lab_home / "models" / "baseline.gguf"
            staged_candidate = lab_home / "models" / "candidate.gguf"
            stage_verified_file(
                baseline_path, staged_baseline,
                expected_size=baseline_file["size"], expected_sha256=baseline_file["sha256"])
            stage_verified_file(
                candidate_path, staged_candidate,
                expected_size=candidate["file"]["size"], expected_sha256=candidate["file"]["sha256"])
            baseline_info = {**validate_gguf(staged_baseline, baseline_file), "file_name": baseline_path.name}
            candidate_info = {**validate_gguf(staged_candidate, candidate["file"]), "file_name": candidate_path.name}
            if candidate_info["sha256"] == baseline_info["sha256"]:
                raise ValueError("candidate and installed baseline are the same artifact")

            model_rows = {
                "baseline": {"model_id": baseline_spec["model_id"], "revision": baseline_spec["revision"],
                             "license_id": baseline_spec["license_id"], "license_url": baseline_spec.get("license_url"),
                             "quant_format": baseline_spec.get("quant_format"), **baseline_info},
                "candidate": {"model_id": candidate["model_id"], "revision": candidate["revision"],
                              "license_id": candidate["license_id"], "license_url": candidate["license_url"],
                              "license_snapshot_sha256": license_snapshot["sha256"],
                              "license_snapshot_verified": True,
                              "license_snapshot_path": candidate["license_snapshot_path"],
                              "license_evidence": candidate.get("license_evidence"),
                              "quant_format": candidate.get("quant_format"), **candidate_info},
            }
            sequence = ["baseline", "candidate"] if order == "baseline-first" else ["candidate", "baseline"]
            specs = {"baseline": baseline_file, "candidate": candidate["file"]}
            staged_paths = {"baseline": staged_baseline, "candidate": staged_candidate}
            results = {}
            for label in sequence:
                path = staged_paths[label]
                validate_gguf(path, specs[label])
                results[label] = run_model(
                    runner_cls, lab_home, path, cfg, timeout_s, max_tokens,
                    expected_binary=binary_resolved, expected_binary_info=binary_info)
                validate_gguf(path, specs[label])
                if not results[label]["release"]["process_reaped"]:
                    break
            runner_infos = [results[label]["runner_binary"] for label in sequence if label in results]
            if len({info["sha256"] for info in runner_infos}) > 1:
                raise RuntimeError("LlamaRunner executable changed between candidate runs")
            runner_launch_verified = bool(runner_infos) and all(
                results[label]["runner_launch_verified"] for label in sequence if label in results)
            complete = all(label in results and results[label]["status"] == "INFERENCE_COMPLETE" for label in ("baseline", "candidate"))
            return {
                "schema": "v14.model-compare/1",
                "status": "COMPARISON_COMPLETE" if complete else "COMPARISON_PARTIAL",
                "environment": environment_name(), "platform_machine": platform.machine(),
                "role": ROLE, "order": order, "model": model_rows, "results": results,
                "runner": {
                    **runner_infos[0],
                    "identity": "MATCHED_INSTALLED_BINARY",
                    "launch_verified": runner_launch_verified,
                },
                "runtime_config": {k: cfg.get(k) for k in ("threads", "context_tokens", "native_batch_tokens", "temperature", "answer_tokens", "c3_sampling", "c3_decode_mode", "native_cache_ram_mb", "native_ctx_checkpoints")},
                "selection": {"winner": None, "automatic_promotion": False,
                              "reason": "Diagnostic four-task comparison only; no production selection or swap is inferred."},
                "safety": {"download_performed": False, "manifest_mutated": False, "production_swap": False,
                           "chat_history_read": False, "sqlite_database_read": False,
                           "active_lora_applied": False, "user_memory_applied": False, "context_os_applied": False,
                           "max_concurrent_native_runners": 1, "coordinator_lock_acquired": True,
                           "model_files_staged": True, "staged_model_files_read_only": True},
                "limits": ["C3 isolated native model probe, not full Runtime/Context OS/B1/B2 E2E.",
                           "Four exact-output tasks are diagnostic, not a broad quality benchmark.",
                           "No active LoRA, user memory or Context OS prompt is applied.",
                           "Installed model files are copied and hash-verified under the coordinator lock before inference.",
                           "The temporary staging directory is on the V13 data volume, not a RAM-backed default temp path.",
                           "One model runs at a time; run both order settings on a cool device to expose thermal/order bias.",
                           "Linux/Termux measurements do not prove Redmi performance unless executed on the actual phone."],
            }
    finally:
        fcntl.flock(lock, fcntl.LOCK_UN)
        lock.close()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--home", required=True, help="existing V13 home; never initialized or modified")
    parser.add_argument("--candidate", required=True, help="candidate id from model_candidates.json")
    parser.add_argument("--candidate-path", help="optional existing local GGUF path; no download is performed")
    parser.add_argument("--timeout", type=float, default=90.0)
    parser.add_argument("--max-tokens", type=int, default=32)
    parser.add_argument("--order", choices=("baseline-first", "candidate-first"), default="baseline-first")
    parser.add_argument("--out", help="optional report path; raw model output is never stored")
    args = parser.parse_args(argv)
    try:
        report = compare(args.home, args.candidate, args.candidate_path, args.timeout, args.max_tokens, args.order)
        encoded = json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2)
        if args.out:
            Path(args.out).expanduser().write_text(encoded + "\n", encoding="utf-8")
        print(encoded)
        return 0 if report["status"] in {"COMPARISON_COMPLETE", "CANDIDATE_NOT_INSTALLED"} else 2
    except Exception as exc:
        print(json.dumps({"status": "ERROR", "error_type": type(exc).__name__}, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
