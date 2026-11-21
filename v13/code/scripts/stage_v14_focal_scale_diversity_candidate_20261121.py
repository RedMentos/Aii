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
BASE_STAGER_GIT_BLOB = "ea9d16902d7c19837e0734f23dd9f307912ef896"
OVERLAY = "scripts/integrated_focal_scale_diversity_candidate_20261121.py"
OVERLAY_GIT_BLOB = "9987525960ba0955dd2fd57d421e32f4b76b892c"
ARITHMETIC_OVERLAY = "scripts/integrated_arithmetic_guard_candidate_20261121.py"
ARITHMETIC_OVERLAY_GIT_BLOB = "2428a07373ec42b8812836da2b8aacf0646b864f"


def _git_blob_sha1(raw: bytes) -> str:
    header = b"blob " + str(len(raw)).encode("ascii") + bytes([0])
    return hashlib.sha1(header + raw).hexdigest()


def _load(code_dir: Path, relative: str, expected_hash: str, label: str, *, git_blob=False):
    path = code_dir / relative
    if path.is_symlink() or not path.is_file():
        raise ValueError(label + " missing or unsafe")
    raw = path.read_bytes()
    observed = _git_blob_sha1(raw) if git_blob else hashlib.sha256(raw).hexdigest()
    if observed != expected_hash:
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

    stager = _load(code_dir, BASE_STAGER, BASE_STAGER_GIT_BLOB, "base_stager", git_blob=True)
    overlay = _load(code_dir, OVERLAY, OVERLAY_GIT_BLOB, "focal_overlay", git_blob=True)
    arithmetic_overlay = _load(code_dir, ARITHMETIC_OVERLAY, ARITHMETIC_OVERLAY_GIT_BLOB,
                               "arithmetic_overlay", git_blob=True)
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
        arithmetic_files = arithmetic_overlay.apply_staged_arithmetic(code_dir, base_destination)
        for relative, payload in arithmetic_files.items():
            target = base_destination / relative
            if target.is_symlink() or not target.is_file():
                raise ValueError("staged arithmetic target missing or unsafe: " + relative)
            target.write_bytes(payload)
        manifest = dict(manifest)
        manifest["overlay"] = {
            "name": OVERLAY,
            "git_blob_sha1": OVERLAY_GIT_BLOB,
            "source_focal_git_blob": overlay.SOURCE_FOCAL_GIT_BLOB,
            "cross_scale_rule": overlay.CROSS_SCALE_RULE,
            "effect": "cross-scale redundancy is discounted only for same-source, same-digest, same-modality, non-overlapping exact evidence spans when lexical relevance is below the active C4 threshold; high-overlap paraphrases retain the full penalty",
            "status": "SHADOW_REVIEW_ONLY",
        }
        manifest["arithmetic_overlay"] = {
            "name": ARITHMETIC_OVERLAY,
            "git_blob_sha1": ARITHMETIC_OVERLAY_GIT_BLOB,
            "source_pins": arithmetic_overlay.SOURCE_PINS,
            "effect": "the existing bounded C5 arithmetic action rejects date-shaped subtraction/division without explicit calculate/compute/berechne cue, records its exact result, and avoids model lookup for the non-model action",
            "status": "SHADOW_REVIEW_ONLY",
        }
        manifest["stage_wrapper"] = "scripts/stage_v14_focal_scale_diversity_candidate_20261121.py"
        replaced = {"v13/focal.py"} | set(arithmetic_files)
        manifest["replaced_files"] = sorted(set(manifest.get("replaced_files", [])) | replaced)
        manifest["files_sha256"] = dict(manifest["files_sha256"])
        manifest["files_sha256"]["v13/focal.py"] = hashlib.sha256(patched).hexdigest()
        for relative, payload in arithmetic_files.items():
            manifest["files_sha256"][relative] = hashlib.sha256(payload).hexdigest()
        limitations = list(manifest.get("limitations", []))
        limitations.extend([
            "C4 source-span and arithmetic refinements are disposable staged candidates; this is not evidence of normal updater integration or phone deployment",
            "synthetic Runtime/SQLite tests do not prove native B1/B2 model quality or Redmi latency",
            "exact arithmetic remains a bounded two-integer, one-operator reflex, not general model reasoning",
            "no latent injection, model/weight change, permission grant or Android action is included",
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
        "arithmetic_overlay": manifest["arithmetic_overlay"],
        "replaced_files": manifest["replaced_files"],
    }, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
