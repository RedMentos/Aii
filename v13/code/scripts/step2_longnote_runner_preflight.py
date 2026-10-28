"""STEP2 next-cohort four-arm dry-run only; native inference intentionally disabled.

This reversible preflight binds the new long-note fixtures to the existing
Z2b harness *without editing* the frozen Z2/Z2b/Z2c modules. A separately
registered native experiment must be implemented before any real model call.
"""
import argparse
import contextlib
import hashlib
import json
from pathlib import Path

from scripts import step2_z2_timescale as z2
from scripts import step2_z2b_seeds as z2b
from scripts import step2_longnote_revision_fixtures as corpus

ROOT = Path(__file__).resolve().parents[1]
REVISION = "step2-longnote-runner-preflight-v1"
SEEDS = (27, 28, 29)
ARMS = {
    "TC": {"base": "C", "query": True, "pointer": False, "body": "two_distinct"},
    "TP": {"base": "C", "query": True, "pointer": True, "body": "two_distinct"},
    "SC": {"base": "D", "query": True, "pointer": False, "body": "shared_dual_state"},
    "SP": {"base": "D", "query": True, "pointer": True, "body": "shared_dual_state"},
}


def candidate_settings(arm, seed):
    if arm not in ARMS or type(seed) is not int or seed not in SEEDS:
        raise ValueError("Unregistered STEP2 long-note arm/seed")
    spec = ARMS[arm]
    # The exact original C/D control settings are preserved; only the new
    # seed and explicitly registered quote-selection arm are overlaid.
    return dict(z2.ARMS[spec["base"]], seed=seed,
                b2_quote_select="pointer" if spec["pointer"] else "off")


@contextlib.contextmanager
def configured():
    """Temporary reversible Z2b binding, never a live Runtime mutation."""
    original = (z2.FIXTURES, z2b.ARMS, z2b.SEEDS, z2b.settings)
    try:
        z2.FIXTURES = corpus.FIXTURES
        z2b.ARMS = {arm: {"base": spec["base"], "query": spec["query"]}
                    for arm, spec in ARMS.items()}
        z2b.SEEDS = SEEDS
        z2b.settings = candidate_settings
        yield z2b
    finally:
        z2.FIXTURES, z2b.ARMS, z2b.SEEDS, z2b.settings = original


def _digest(value):
    raw = json.dumps(value, sort_keys=True, ensure_ascii=False,
                     separators=(",", ":"), allow_nan=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _source_hashes():
    paths = (Path(__file__).resolve(), Path(corpus.__file__).resolve(),
             Path(z2.__file__).resolve(), Path(z2b.__file__).resolve(),
             ROOT / "v13/agi/eligibility.py")
    return {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in paths}


def dry_run():
    """Deterministic source/fixture/control manifest; no model or inference."""
    with configured():
        assert tuple(z2b.SEEDS) == SEEDS
        assert len(z2.FIXTURES) == 10
        arms = {arm: {"body": spec["body"], "query": spec["query"],
                      "pointer": spec["pointer"],
                      "settings": candidate_settings(arm, SEEDS[0])}
                for arm, spec in ARMS.items()}
        fixture_hash = _digest(z2.FIXTURES)
    source_hashes = _source_hashes()
    registered = {"revision": REVISION, "seeds": list(SEEDS),
                  "arms": arms, "fixture_sha256": fixture_hash,
                  "source_sha256": source_hashes}
    return {"proof_kind": "STEP2_LONGNOTE_RUNNER_DRY_RUN_ONLY",
            "native_execution": False, "models_loaded": False,
            "gate_promotion": False, "registered": registered,
            "registration_sha256": _digest(registered),
            "requirements_for_native": [
                "Separate preregistered source/model/runner/seed hashes",
                "Pinned native artifacts and resource owner/cgroup check",
                "Measured TP/TC/SP/SC with frozen STEP2 criterion 3",
                "Closed raw evidence and no live age/learning promotion",
            ]}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--execute-native", action="store_true")
    args = parser.parse_args(argv)
    if args.execute_native:
        parser.error("native execution is not implemented/authorized by this preflight")
    print(json.dumps(dry_run(), sort_keys=True, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
