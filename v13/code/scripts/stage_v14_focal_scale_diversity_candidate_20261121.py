"""Build a review-only V14 stage with scale-aware B1/B2 C4 admission.

This wraps the existing hash-pinned integrated stage. It does not edit the
frozen source tree, installed launcher, models, permissions or user data.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import secrets
import shutil

BASE_STAGER = "scripts/stage_integrated_candidate.py"
BASE_STAGER_SHA256 = "4b8c5f2b90595dff830ffe0636947c22bf1802f2f2661da4db1748b2104a9dc5"
OVERLAY = "scripts/integrated_focal_scale_diversity_candidate_20261121.py"
OVERLAY_SHA256 = "f4baf5120aa80dcea202088544c9c487e88cf6d66d6ab2b2b07184db8f418d4a"
ARITHMETIC_OVERLAY = "scripts/integrated_arithmetic_date_guard_candidate_20261121.py"
ARITHMETIC_OVERLAY_SHA256 = "8d9609f0bf247b2e4eeff763158524013f9022259b473884f638462a45d26f94"


def _load(code_dir: Path, relative: str, expected_sha256: str, label: str):
    path = code_dir / relative
    if path.is_symlink() or not path.is_file():
        raise ValueError(label + " missing or unsafe")
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected_sha256:
        raise ValueError(label + " source hash changed")
    spec = importlib.util.spec_from_file_location("v14_focal_" + label, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(label + " cannot be loaded")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def stage(code_dir: Path, destination: Path) -> dict:
    code_dir = Path(code_dir).resolve(strict=True)
    destination = Path(destination).expanduser()
    if destination.is_symlink():
        raise ValueError("destination cannot be a symlink")
    if destination.exists():
        raise FileExistsError("destination must not exist")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination = destination.parent.resolve() / destination.name
    if destination == code_dir or code_dir in destination.parents:
        raise ValueError("destination overlaps source tree")

    stager = _load(code_dir, BASE_STAGER, BASE_STAGER_SHA256, "base_stager")
    overlay = _load(code_dir, OVERLAY, OVERLAY_SHA256, "focal_overlay")
    arithmetic_overlay = _load(code_dir, ARITHMETIC_OVERLAY, ARITHMETIC_OVERLAY_SHA256, "arithmetic_overlay")
    base_destination = destination.parent / (".v14-focal-base-" + secrets.token_hex(8))
    try:
        manifest = stager.stage(code_dir, base_destination)
        if manifest.get("status") != "SHADOW_REVIEW_ONLY":
            raise ValueError("base stage did not remain review-only")
        focal_path = base_destination / "v13" / "focal.py"
        if focal_path.is_symlink() or not focal_path.is_file():
            raise ValueError("staged focal.py missing or unsafe")
        patched = overlay.apply_staged_focal(code_dir, focal_path.read_bytes())
        focal_path.write_bytes(patched)
        arithmetic_path = base_destination / "v13" / "arithmetic_reflex.py"
        if arithmetic_path.is_symlink() or not arithmetic_path.is_file():
            raise ValueError("staged arithmetic_reflex.py missing or unsafe")
        patched_arithmetic = arithmetic_overlay.apply_staged_arithmetic(code_dir, arithmetic_path.read_bytes())
        arithmetic_path.write_bytes(patched_arithmetic)

        manifest = dict(manifest)
        manifest["overlay"] = {
            "name": OVERLAY,
            "sha256": OVERLAY_SHA256,
            "source_focal_git_blob": overlay.SOURCE_FOCAL_GIT_BLOB,
            "cross_scale_redundancy_factor": overlay.CROSS_SCALE_REDUNDANCY_FACTOR,
            "effect": "B1/B2 cross-scale lexical redundancy penalty is discounted; same-role and body/memory penalties are unchanged",
            "status": "SHADOW_REVIEW_ONLY",
        }
        manifest["stage_wrapper"] = "scripts/stage_v14_focal_scale_diversity_candidate_20261121.py"
        manifest["arithmetic_overlay"] = {
            "name": ARITHMETIC_OVERLAY,
            "sha256": ARITHMETIC_OVERLAY_SHA256,
            "source_arithmetic_git_blob": arithmetic_overlay.SOURCE_ARITHMETIC_GIT_BLOB,
            "effect": "bare year-month date shapes are not rendered as arithmetic; explicit calculate/berechne remains eligible",
            "status": "SHADOW_REVIEW_ONLY",
        }
        manifest["replaced_files"] = sorted(set(manifest.get("replaced_files", [])) | {"v13/focal.py", "v13/arithmetic_reflex.py"})
        manifest["files_sha256"] = dict(manifest["files_sha256"])
        manifest["files_sha256"]["v13/focal.py"] = hashlib.sha256(patched).hexdigest()
        manifest["files_sha256"]["v13/arithmetic_reflex.py"] = hashlib.sha256(patched_arithmetic).hexdigest()
        limitations = list(manifest.get("limitations", []))
        limitations.extend([
            "C4 scale-diversity overlay is a disposable staged candidate, not the installed Runtime",
            "synthetic Runtime/SQLite tests do not prove native B1/B2 model quality or Redmi latency",
            "no latent injection, model/weight change, permission grant or Android action is included",
            "date guard covers only bare year-month forms and is not a general date or math parser",
        ])
        manifest["limitations"] = list(dict.fromkeys(limitations))
        (base_destination / "INTEGRATION_STAGE.json").write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        stager._publish(base_destination, destination)
        return manifest
    except BaseException:
        shutil.rmtree(base_destination, ignore_errors=True)
        raise


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--code-dir", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        manifest = stage(args.code_dir, args.output)
    except (OSError, ValueError, RuntimeError, ImportError, FileExistsError) as exc:
        parser.exit(2, "BLOCKED: " + str(exc) + "\n")
    print(json.dumps({
        "output": str(args.output.resolve()),
        "status": manifest["status"],
        "overlay": manifest["overlay"],
        "replaced_files": manifest["replaced_files"],
    }, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
