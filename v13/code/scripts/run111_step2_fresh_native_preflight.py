"""Run111 fresh STEP2 cohort binding: deterministic software preflight only.

No native execution, model load, mutation of original Z2 fixtures, or gate promotion.
"""
from __future__ import annotations

import argparse
import contextlib
from copy import deepcopy
import hashlib
import json
from pathlib import Path

from scripts import run109_step2_fresh_fixtures as corpus
from scripts import step2_z2b_seeds as z2b

# Z2b imports its Z2 harness as a top-level module. Never patch a second alias.
z2 = z2b.z2
ROOT = Path(__file__).resolve().parents[1]
SEEDS = (20, 21, 22)
ARMS = {
    "CQP": {"base": "C", "pointer": True, "body": "two_distinct"},
    "DQP": {"base": "D", "pointer": True, "body": "shared_dual_state"},
    "CQ": {"base": "C", "pointer": False, "body": "two_distinct"},
}
VARIANTS = ("b1_only", "b2_only", "both_none", "both_exact",
            "both_control", "same_policy_dual", "prompt_only_dual")
EXPECTED_PROJECTS = ("Atlas", "Borealis", "Cygnus", "Delta", "Epsilon", "Fornax")
CATALOG_BLOB = "7af05962af41d0bc3f7dd18ef01d4eba55eabf99"
FROZEN_BLOBS = {
    "scripts/run109_step2_fresh_fixtures.py": "6cc3d52524e8c9122710eae2a908d024f0f44f24",
    "scripts/step2_z2_timescale.py": "2ad62fbbf1f6463d99360cdb8198f1104cfdfaf7",
    "scripts/step2_z2b_seeds.py": "7c299616495450e4a38f9aab9921f7176ba67556",
    "scripts/step2_z2c_b2_rule.py": "59b794401c7b7445c411cd4440f45278b1c14e5d",
    "tests/integration_step2_utility.py": "a7ba12a8807a1ca8236f1c70d54dedb65c212caa",
    "v13/cognition.py": "1a9eb6f7c7cbfce83d91cc09b4ff9516cff310cf",
    "v13/runners.py": "efda7aa1aa5729e974d0d641870d4da05d21c961",
    "v13/config.py": "546b97946a5036b7006fb741376e5ca42c7e1440",
    "v13/agi/eligibility.py": "e1f1a2d09a614378a75e397819fdce96a46de22d",
    "scripts/step2_tool_replay.py": "e8d8c87de2474a764e4bbc28b4fe028413a316e1",
    "docs/canon/V13_v10.16.1_WORK_HANDOFF_SINGLE_SOURCE_B3_HARDENED.md":
        "218464b12a2d27d92524c751922fa8e1c3fb0ea7",
}
MODEL_SHA256 = {
    "body": "bb741ebb106d543e9de114b843a3d3d73d51c74b5801e69da2abde821a0cb3e1",
    "gist": "57d1997790d1744fba5b40a7317df71ea5e2acee28c47e78f0cce39c0703f8cf",
    "language": "3d10b6ab8fc91a919534b9558e266255aca0bbc7f6d015963599aa9e74e05b1d",
    "needle": "c9d915eca282ed42d1a09b143b592adb4cc6744ffe2d294adf5cfc5548170c38",
}
RUNNER_TAR_SHA256 = "9abf88aea48a55d0f80edb1ee20220b186848cca0b4e919d71518cfd7ca67443"
_active = False


def _blob_sha(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def _canonical_sha(value) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                     separators=(",", ":"), allow_nan=False)
                          .encode("utf-8")).hexdigest()


def verify_frozen():
    observed = {}
    for name, expected in FROZEN_BLOBS.items():
        path = ROOT / name
        actual = _blob_sha(path.read_bytes())
        if actual != expected:
            raise ValueError("FROZEN_SOURCE_DRIFT: " + name)
        observed[name] = actual
    raw = (ROOT / "specs/models.json").read_bytes()
    if _blob_sha(raw) != CATALOG_BLOB:
        raise ValueError("MODEL_CATALOG_DRIFT")
    catalog = json.loads(raw)
    for role, expected in MODEL_SHA256.items():
        if (len(catalog["models"][role]["files"]) != 1
                or catalog["models"][role]["files"][0]["sha256"] != expected):
            raise ValueError("MODEL_PIN_DRIFT: " + role)
    runner = catalog["runner"]
    if (runner["tag"] != "b10964"
            or runner["linux_binaries"]["linux-x86_64"]["sha256"] != RUNNER_TAR_SHA256):
        raise ValueError("RUNNER_PIN_DRIFT")
    return observed


def settings(arm: str, seed: int):
    if arm not in ARMS or type(seed) is not int or seed not in SEEDS:
        raise ValueError("UNREGISTERED_ARM_OR_SEED")
    spec = ARMS[arm]
    return dict(z2.ARMS[spec["base"]], seed=seed,
                b2_quote_select="pointer" if spec["pointer"] else "off")


@contextlib.contextmanager
def configured():
    """Private reversible module binding; nested or overlapping use is refused."""
    global _active
    if _active:
        raise RuntimeError("STEP2_PREFLIGHT_ALREADY_ACTIVE")
    original = (z2.FIXTURES, z2b.ARMS, z2b.SEEDS, z2b.settings)
    _active = True
    try:
        z2.FIXTURES = deepcopy(corpus.fixtures())
        z2b.ARMS = {arm: {"base": spec["base"], "query": True}
                    for arm, spec in ARMS.items()}
        z2b.SEEDS = SEEDS
        z2b.settings = settings
        yield z2b
    finally:
        z2.FIXTURES, z2b.ARMS, z2b.SEEDS, z2b.settings = original
        _active = False


def dry_run():
    frozen = verify_frozen()
    original = _canonical_sha(z2.FIXTURES)
    with configured():
        cases = z2.FIXTURES
        if tuple(f["id"] for f in cases) != EXPECTED_PROJECTS:
            raise ValueError("FIXTURE_IDS_DRIFT")
        if tuple(f["fixture_kind"] for f in cases) != (
                "LONG", "LONG", "LONG", "REVISED", "REVISED", "REVISED"):
            raise ValueError("FIXTURE_TYPES_DRIFT")
        checks = corpus.inspect()["checks"]
        if not all(checks.values()) or _canonical_sha(cases) != corpus.inspect()["fixture_sha256"]:
            raise ValueError("FIXTURE_ORACLE_OR_CONTENT_DRIFT")
        fixture_sha = _canonical_sha(cases)
        arms = {name: {"body": spec["body"], "query": True,
                       "pointer": spec["pointer"], "settings_by_seed":
                           {str(seed): settings(name, seed) for seed in SEEDS}}
                for name, spec in ARMS.items()}
        registration = {
            "schema": "v13.run111.step2_fresh_preflight.v1",
            "projects": list(EXPECTED_PROJECTS), "fixture_sha256": fixture_sha,
            "source_git_blobs": frozen, "catalog_git_blob": CATALOG_BLOB,
            "model_sha256": MODEL_SHA256, "runner_tar_sha256": RUNNER_TAR_SHA256,
            "seeds": list(SEEDS), "arms": arms, "variants": list(VARIANTS),
            "registered_native_rows": len(cases) * len(VARIANTS) * len(ARMS) * len(SEEDS),
        }
    if _canonical_sha(z2.FIXTURES) != original:
        raise RuntimeError("ORIGINAL_Z2_MUTATED")
    return {
        "schema": "v13.run111.step2_fresh_preflight_report.v1",
        "status": "PREPARED_NOT_NATIVE_REGISTERED",
        "registration": registration,
        "registration_sha256": _canonical_sha(registration),
        "native_execution": False, "models_loaded": False, "native_calls": 0,
        "canonical_gate_pass": False, "step2_status": "UTILITY_FAIL",
        "redmi_measured": False, "whole_system_complete": False,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--execute-native", action="store_true")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)
    if args.execute_native:
        parser.error("Native execution is not authorized by Run111 preflight")
    report = dry_run()
    if args.out is not None:
        path = args.out.expanduser().resolve()
        if path.exists():
            raise FileExistsError("FRESH_EVIDENCE_FILE_REQUIRED")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n",
                        encoding="utf-8")
    print(json.dumps({"status": report["status"],
                      "registration_sha256": report["registration_sha256"],
                      "native_calls": 0}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
