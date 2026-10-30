"""Read-only semantic audit of the exact 2026-10-30 native STEP12 ZIP.

This is a *single-arm diagnostic* of real native output, not a STEP2
complementarity gate or new native execution. Never promotes any V13 gate.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import zipfile

EXPECTED_ZIP_SHA = "ad961abb8eea8d567f58cbc4f1fed67f7a79920e36564bb5527b7ea08fa4f3f7"
EXPECTED_HEAD = "3c9e961d123e5bed1826802fc3e236c19078f5ee"
EXPECTED_CANON = "218464b12a2d27d92524c751922fa8e1c3fb0ea7"
EXPECTED_CATALOG = "7af05962af41d0bc3f7dd18ef01d4eba55eabf99"
EXPECTED_TOOLS = "954a3f468f10195fbce12d27f68585ee7edee2c9"
EXPECTED_PROOFS_SHA = "c757aac40a4a267ad7dd338042fb7a2a02fb0de395c7543ef77a4e3d55b2ce9b"
SCHEMA = "v13.step2.currentchain_native_semantic_gap.v1"
MAX_ZIP_BYTES = 2_000_000
MAX_TOTAL_UNCOMPRESSED = 4_000_000
_LEFT = re.compile(r"\b(?:remain(?:s|ing)?|left|remainder|balance|rest|"
                   r"übrig|bleib(?:t|en)|verbleib(?:t|en))\b", re.I)
_EURO = r"(?:euros?|eur|€)"
_NUM = lambda n: rf"(?<!\d){n}(?!\d|[.,]\d)\s*{_EURO}(?!\w)"


def _bound_remainder(text: str, option: str, other: str, amount: int) -> bool:
    """Only count a typed remainder bound to the right option, not copied costs."""
    names = {"Rot": r"(?:Rot|Red)", "Blau": r"(?:Blau|Blue)"}
    label, foreign = names[option], names[other]
    # Stop at the other option or a sentence/clause boundary, so swapped
    # amounts in 'Rot has 10; Blau has 40' cannot accidentally score.
    between = rf"(?:(?!\b{foreign}\b)[^.!?;\n]){{0,90}}?"
    patterns = (rf"\b{label}\b{between}{_NUM(amount)}",
                rf"{_NUM(amount)}{between}\b{label}\b")
    for pattern in patterns:
        for m in re.finditer(pattern, text, re.I):
            if _LEFT.search(m.group(0)):
                return True
    return False


def score_output(text: str) -> dict:
    if not isinstance(text, str):
        raise ValueError("FINAL_TEXT_REQUIRED")
    red = _bound_remainder(text, "Rot", "Blau", 40)
    blue = _bound_remainder(text, "Blau", "Rot", 10)
    return {"rot_40_euro_remainder": red,
            "blau_10_euro_remainder": blue,
            "correct_remainders": int(red) + int(blue),
            "required_remainders": 2}


def _closed_files(z: zipfile.ZipFile) -> dict[str, bytes]:
    infos = z.infolist()
    if not infos or len(infos) > 100 or sum(i.file_size for i in infos) > MAX_TOTAL_UNCOMPRESSED:
        raise ValueError("ZIP_BOUNDS")
    names = [i.filename for i in infos]
    if len(names) != len(set(names)) or any(
            n.startswith("/") or ".." in Path(n).parts or n.endswith("/")
            for n in names):
        raise ValueError("ZIP_NAMES")
    if z.testzip() is not None:
        raise ValueError("ZIP_CRC")
    raw = {name: z.read(name) for name in names}
    manifest = raw.get("SHA256SUMS.txt")
    if manifest is None:
        raise ValueError("MISSING_SHA256SUMS")
    try:
        entries = [line.split("  ", 1) for line in manifest.decode("ascii").splitlines()]
        declared = {}
        for h, name in entries:
            name = name.removeprefix("./")
            if name in declared or not re.fullmatch(r"[a-f0-9]{64}", h):
                raise ValueError("DUPLICATE_OR_INVALID_MANIFEST")
            declared[name] = h
    except (UnicodeDecodeError, ValueError) as exc:
        raise ValueError("INVALID_MANIFEST") from exc
    if set(declared) != set(raw) - {"SHA256SUMS.txt"}:
        raise ValueError("MANIFEST_SET_MISMATCH")
    if any(hashlib.sha256(raw[name]).hexdigest() != h for name, h in declared.items()):
        raise ValueError("INNER_SHA256_MISMATCH")
    return raw


def audit(path: Path, *, expected_zip_sha=EXPECTED_ZIP_SHA,
          expected_head=EXPECTED_HEAD,
          expected_proofs_sha=EXPECTED_PROOFS_SHA) -> dict:
    path = Path(path)
    if not path.is_file() or path.stat().st_size > MAX_ZIP_BYTES:
        raise ValueError("ZIP_MISSING_OR_OVERSIZE")
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    if actual != expected_zip_sha:
        raise ValueError("ZIP_SHA256_MISMATCH")
    with zipfile.ZipFile(path) as z:
        raw = _closed_files(z)
    for name, expected in (
            ("HEAD.txt", expected_head), ("CANON_BLOB.txt", EXPECTED_CANON),
            ("CATALOG_BLOB.txt", EXPECTED_CATALOG),
            ("TOOLS_BLOB.txt", EXPECTED_TOOLS)):
        if raw.get(name, b"").decode("ascii", errors="replace").strip() != expected:
            raise ValueError("PIN_MISMATCH_" + name)
    try:
        jef = json.loads(raw["proofs/jef-modes-proof.json"])
        step = json.loads(raw["proofs/step12-proof.json"])
    except (KeyError, UnicodeDecodeError, ValueError) as exc:
        raise ValueError("PROOF_MISSING_OR_INVALID") from exc
    if (jef.get("status") != "JEF_MODES_PASS"
            or step.get("proof_kind") != "STEP12_VERTICAL_INTERMEDIATE"
            or step.get("status") != "VERTICAL_CHECKS_PASS"
            or step.get("source_hashes", {}).get("v13/proofs.py") != expected_proofs_sha
            or step.get("cycles") != 1
            or step.get("step2_observed_both_roles") is not True
            or step.get("full_runner_proof") is not False
            or step.get("complementarity_proven") is not False
            or len(step.get("turns", [])) != 2):
        raise ValueError("PROOF_SCOPE_MISMATCH")
    turn = step["turns"][-1]
    cfg = turn.get("output_metadata", {}).get("effective_config", {})
    if (turn.get("checks", {}).get("final_output") is not True
            or turn.get("checks", {}).get("actual_model_output") is not True
            or cfg.get("learning_mode") != "RECORD_ONLY"
            or cfg.get("system_stage") != 0
            or cfg.get("jepa_weight", 0) != 0
            or cfg.get("latents_enabled") is not False):
        raise ValueError("NOT_FROZEN_AGE0_NATIVE_FINAL")
    scored = score_output(turn.get("output"))
    return {
        "schema": SCHEMA, "original_zip_sha256": actual,
        "original_head": expected_head,
        "native_output_role": turn["output_metadata"].get("runner", {}).get("role"),
        "step12_structural_status": step["status"],
        "semantic_status": ("REQUIREMENTS_PRESENT_DIAGNOSTIC_ONLY"
                            if scored["correct_remainders"] == 2
                            else "SEMANTIC_REQUIREMENT_FAIL"),
        "score": scored, "native_executed_here": False,
        "comparative_utility_proven": False, "step2_gate_promoted": False,
        "redmi_measured": False, "jepa_weight": 0,
        "claim_limit": "One archived native answer, no paired baseline or STEP2 utility proof",
    }


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--zip", required=True, type=Path)
    p.add_argument("--out", required=True, type=Path)
    args = p.parse_args(argv)
    if args.out.exists():
        raise ValueError("FRESH_OUTPUT_REQUIRED")
    result = audit(args.zip)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, sort_keys=True))
    return 0  # A negative semantic result is valid diagnostic evidence, not a pass.


if __name__ == "__main__":
    raise SystemExit(main())
