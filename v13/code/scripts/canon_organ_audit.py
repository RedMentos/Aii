"""Read-only V13 Canon organ/objective coverage and authority audit.

A consistent manifest is NOT proof that an organ works or that the full
architecture is complete. This script never changes any Age/learning gate.
Stdlib only; suitable for CI and an offline source-only installation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

SCHEMA = "V13_CANON_ORGAN_OBJECTIVE_AUDIT_V1"
EXPECTED_COMPONENTS = tuple(
    "A0 A1 A2 A3 A4 A5 B1 B2 B3 B4 B5 C0 C1 C2 C3 C4 C5 C6 C7 "
    "F1 F2 F3 F4 F5 F6 F7 F8 F9 F10 F11".split()
)
EXPECTED_OBJECTIVES = tuple("""
explicit-human-route-cross-entropy-v1 A3_alignment B_local_JEPA
A_to_B_cross_JEPA B_to_A_cross_JEPA B3_latent_alignment C_executive_JEPA
World_JEPA C_wake_halt_calibration C_output_adapter semantic_skill_consolidation
metaplasticity_homeostasis explicit-human-wake-readout-v1
explicit-human-halt-readout-v1 dense-body-future-state-predictor-v1
a3-text-teacher-alignment-reconstruction-v1 world-digital-action-latent-v1
explicit-human-native-first-route-agreement-v1 source-bound-semantic-retrieval-v1
c3-native-first-token-delta-v2 c5-action-values-v1 jef-bridge-utility-v1
fast-forward-proceduralization-v1 context-policy-recall-v1
memory-admission-heldout-logistic-v1 neuromod-metaplasticity-retention-v1
attention-policy-v1 deliberation-mode-values-v1 callosum-channel-utility-v1
gist-readout-grouping
""".split())
MODES = frozenset(("IMPLEMENTED", "PARTIAL", "UNAVAILABLE"))


def _read_json(path: Path):
    if path.is_symlink() or not path.is_file():
        raise ValueError("Expected regular non-symlink JSON file: " + str(path))
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("Duplicate JSON key: " + key)
            result[key] = value
        return result
    obj = json.loads(path.read_bytes(), object_pairs_hook=unique)
    if not isinstance(obj, dict):
        raise ValueError("Expected JSON object: " + str(path))
    return obj


def _regular_within(root: Path, relative: str) -> Path | None:
    if not isinstance(relative, str) or not relative:
        return None
    rel = Path(relative)
    if rel.is_absolute() or any(part in ("..", ".") for part in rel.parts):
        return None
    candidate = root / rel
    try:
        resolved = candidate.resolve(strict=True)
        if not resolved.is_relative_to(root) or not resolved.is_file():
            return None
        current = candidate
        while current != root:
            if current.is_symlink():
                return None
            current = current.parent
        return resolved
    except (OSError, ValueError, RuntimeError):
        return None


def audit(root: Path, *, contracts=None, objectives=None):
    root = Path(root).resolve()
    contract_path = root / "specs/component-contracts.json"
    objective_path = root / "specs/learning-objectives.json"
    contract_bytes = contract_path.read_bytes()
    objective_bytes = objective_path.read_bytes()
    if contracts is None:
        contracts = _read_json(contract_path)
    if objectives is None:
        objectives = _read_json(objective_path)
    errors = []
    def fail(code):
        if code not in errors:
            errors.append(code)

    if contracts.get("schema_version") != 1 or objectives.get("schema_version") != 1:
        fail("UNSUPPORTED_MANIFEST_SCHEMA")
    if contracts.get("canonical_architecture_complete") is not False:
        fail("UNSUPPORTED_COMPLETION_CLAIM")

    canon_rel = contracts.get("canon_file")
    canon_path = _regular_within(root, canon_rel)
    canon_sha = hashlib.sha256(canon_path.read_bytes()).hexdigest() if canon_path else None
    if canon_path is None:
        fail("CANON_FILE_MISSING_OR_UNSAFE")
    if canon_sha != contracts.get("canon_sha256"):
        fail("CANON_HASH_MISMATCH")

    components = contracts.get("components")
    if not isinstance(components, list):
        components = []
        fail("INVALID_COMPONENT_LIST")
    seen = set()
    by_mode = {mode: [] for mode in sorted(MODES)}
    for row in components:
        if not isinstance(row, dict):
            fail("INVALID_COMPONENT_ROW")
            continue
        cid = row.get("component_id")
        if not isinstance(cid, str):
            fail("INVALID_COMPONENT_ID")
            continue
        if cid in seen:
            fail("DUPLICATE_COMPONENT:" + cid)
        seen.add(cid)
        if cid not in EXPECTED_COMPONENTS:
            fail("UNKNOWN_COMPONENT:" + cid)
        mode = row.get("current_mode")
        if mode not in MODES:
            fail("INVALID_COMPONENT_MODE:" + cid)
        else:
            by_mode[mode].append(cid)
        if not isinstance(row.get("canon_source"), str) or not row["canon_source"].strip():
            fail("MISSING_CANON_SOURCE:" + cid)
        if mode != "IMPLEMENTED" and not row.get("known_limits"):
            fail("MISSING_COMPONENT_LIMITS:" + cid)
        files = row.get("implementation_files")
        if not isinstance(files, list):
            fail("INVALID_IMPLEMENTATION_FILES:" + cid)
            files = []
        if mode != "UNAVAILABLE" and not files:
            fail("MISSING_IMPLEMENTATION_FILES:" + cid)
        for relative in files:
            if _regular_within(root, relative) is None:
                fail("MISSING_IMPLEMENTATION_FILE:" + cid + ":" + str(relative))
        for right in ("latent_read_authority", "latent_learn_authority"):
            if type(row.get(right)) is not int or row[right] != 0:
                fail("UNPROVEN_LATENT_AUTHORITY:" + cid + ":" + right)
    for cid in EXPECTED_COMPONENTS:
        if cid not in seen:
            fail("MISSING_COMPONENT:" + cid)

    objective_rows = objectives.get("objectives")
    if not isinstance(objective_rows, list):
        objective_rows = []
        fail("INVALID_OBJECTIVE_LIST")
    seen_objectives = set()
    objective_modes = {mode: [] for mode in sorted(MODES)}
    for row in objective_rows:
        if not isinstance(row, dict):
            fail("INVALID_OBJECTIVE_ROW")
            continue
        oid = row.get("objective_id")
        if not isinstance(oid, str):
            fail("INVALID_OBJECTIVE_ID")
            continue
        if oid in seen_objectives:
            fail("DUPLICATE_OBJECTIVE:" + oid)
        seen_objectives.add(oid)
        if oid not in EXPECTED_OBJECTIVES:
            fail("UNKNOWN_OBJECTIVE:" + oid)
        mode = row.get("status")
        if mode not in MODES:
            fail("INVALID_OBJECTIVE_MODE:" + oid)
        else:
            objective_modes[mode].append(oid)
        if mode != "IMPLEMENTED" and (type(row.get("learn_gain")) not in (int, float) or row["learn_gain"] != 0):
            fail("UNAUTHORIZED_OBJECTIVE_GAIN:" + oid)
        targets = row.get("applicable_components")
        if not isinstance(targets, list) or not targets:
            fail("INVALID_OBJECTIVE_COMPONENTS:" + oid)
            targets = []
        for cid in targets:
            if cid not in EXPECTED_COMPONENTS or cid not in seen:
                fail("UNKNOWN_OBJECTIVE_COMPONENT:" + str(cid))
        files = row.get("implementation_files", [])
        if not isinstance(files, list):
            fail("INVALID_OBJECTIVE_FILES:" + oid)
            files = []
        if mode == "IMPLEMENTED" and not files:
            fail("MISSING_OBJECTIVE_IMPLEMENTATION:" + oid)
        for relative in files:
            if _regular_within(root, relative) is None:
                fail("MISSING_OBJECTIVE_FILE:" + oid + ":" + str(relative))
    for oid in EXPECTED_OBJECTIVES:
        if oid not in seen_objectives:
            fail("MISSING_OBJECTIVE:" + oid)

    return {
        "schema": SCHEMA,
        "status": "CONTRACT_INVALID" if errors else "CONSISTENT_BUT_INCOMPLETE",
        "canonical_architecture_complete": False,
        "component_count": len(components),
        "objective_count": len(objective_rows),
        "components_by_mode": {key: sorted(value) for key, value in by_mode.items()},
        "objectives_by_mode": {key: sorted(value) for key, value in objective_modes.items()},
        "hashes": {
            "canon_sha256": canon_sha,
            "contracts_sha256": hashlib.sha256(contract_bytes).hexdigest(),
            "objectives_sha256": hashlib.sha256(objective_bytes).hexdigest(),
        },
        "errors": errors,
        "claim_limits": [
            "Manifest consistency is not native execution or semantic utility.",
            "File presence does not prove an organ is implemented or trained.",
            "All original STEP2/B3/Body-JEPA/Redmi/learning gates remain external.",
        ],
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)
    try:
        report = audit(args.root)
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        report = {"schema": SCHEMA, "status": "CONTRACT_INVALID",
                  "canonical_architecture_complete": False,
                  "errors": [type(exc).__name__ + ": " + str(exc)[:300]]}
    encoded = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(encoded, encoding="utf-8")
    print(encoded, end="")
    return 0 if not report["errors"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
