"""Run37 disjoint Elyndra C3 rule-use factorial, source-only envelopes.

No native model, Runtime/Store, B1/B2 inference, learning or gate promotion.
A separate exclusive native runner may consume these exact envelopes later.
"""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

from scripts import run33_b2_c3_counterfactual_envelopes as cf
from tests import integration_step2_utility as frozen_consumer
from v13.common import dumps
from v13.models import catalog

ROOT = Path(__file__).resolve().parents[1]
RUN33_SOURCE_BLOB = "b1d58d7e0c3937787cf15dd801e278de25845879"
FROZEN_CONSUMER_BLOB = "a7ba12a8807a1ca8236f1c70d54dedb65c212caa"
CATALOG_BLOB = "7af05962af41d0bc3f7dd18ef01d4eba55eabf99"
MODEL_SHA256 = "3d10b6ab8fc91a919534b9558e266255aca0bbc7f6d015963599aa9e74e05b1d"
MODEL_REVISION = "657e078c94084481950a2d555a941481f715536b"
RUNNER_TAR_SHA256 = "9abf88aea48a55d0f80edb1ee20220b186848cca0b4e919d71518cfd7ca67443"
FIXTURE = "Elyndra"
SEED = 20261122
ARMS = ("B1_ONLY", "DISTRACTOR_FROZEN", "EXACT_FROZEN",
        "DISTRACTOR_HINT", "EXACT_HINT")
SOURCE_ARMS = {
    "B1_ONLY": "B1_ONLY",
    "DISTRACTOR_FROZEN": "B1_B2_DISTRACTOR",
    "EXACT_FROZEN": "B1_B2_EXACT",
    "DISTRACTOR_HINT": "B1_B2_DISTRACTOR",
    "EXACT_HINT": "B1_B2_EXACT",
}
HINT = ("Use only the current source and source-exact verified quotes. "
        "If the quoted rules specify a budget, compute each option's remaining "
        "amount from that budget and its cost; if the rules specify a decision "
        "procedure, apply it to choose action rather than defaulting to NONE. "
        "Do not invent missing rules or quote text. Return only the required JSON schema.")
HINT_SHA256 = "5ac5fa2aa13a7d82edeb66b960eff443e7ed60b4ebf8f775987cb4fd4739a9c7"


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _blob(path):
    raw = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") +
                        b"\0" + raw).hexdigest()


def prereg():
    original = cf.prereg()
    if (_blob(ROOT / "scripts/run33_b2_c3_counterfactual_envelopes.py")
            != RUN33_SOURCE_BLOB or
            _blob(ROOT / "tests/integration_step2_utility.py")
            != FROZEN_CONSUMER_BLOB or
            _blob(ROOT / "specs/models.json") != CATALOG_BLOB or
            _sha(HINT.encode("utf-8")) != HINT_SHA256):
        raise ValueError("run37_frozen_source_or_hint_changed")
    specs = catalog()
    c3 = specs["models"]["language"]
    runner = specs["runner"]
    if (c3["revision"] != MODEL_REVISION or
            len(c3["files"]) != 1 or
            c3["files"][0]["sha256"] != MODEL_SHA256 or
            runner["tag"] != "b10964" or
            runner["linux_binaries"]["linux-x86_64"]["sha256"] != RUNNER_TAR_SHA256 or
            FIXTURE not in {f["id"] for f in cf.FIXTURES} or
            SEED not in cf.SEEDS or
            original["native_executed"] is not False):
        raise ValueError("run37_model_or_cohort_changed")
    return {
        "schema": "v13.run37.c3_rule_use.prereg.v1",
        "fixture_id": FIXTURE, "seed": SEED, "arms": list(ARMS),
        "source_arms": dict(SOURCE_ARMS),
        "hint_sha256": HINT_SHA256,
        "run33_source_blob": RUN33_SOURCE_BLOB,
        "frozen_consumer_blob": FROZEN_CONSUMER_BLOB,
        "model_sha256": MODEL_SHA256,
        "model_revision": MODEL_REVISION,
        "runner_tar_sha256": RUNNER_TAR_SHA256,
        "evidence_level": "SYNTHETIC_SOURCE_ONLY_NO_C3",
        "native_executed": False, "canonical_gate_pass": False,
        "phone_measured": False, "jepa_weight": 0,
        "whole_system_complete": False,
    }


def build_envelope(arm):
    prereg()
    if type(arm) is not str or arm not in SOURCE_ARMS:
        raise ValueError("run37_unregistered_arm")
    base = cf.build_envelope(FIXTURE, SOURCE_ARMS[arm], SEED)
    cf.verify_envelope(base)
    env = copy.deepcopy(base)
    env["schema"] = "v13.run37.c3_rule_use.envelope.v1"
    env["experiment_arm"] = arm
    env["base_run33_envelope_sha256"] = _sha(dumps(base).encode("utf-8"))
    env["hint_sha256"] = HINT_SHA256 if arm.endswith("_HINT") else None
    if arm.endswith("_HINT"):
        env["messages"][0]["content"] = frozen_consumer.SYSTEM + "\n" + HINT
    context = json.loads(env["messages"][1]["content"])
    if set(context) != {"current_source", "analysts"}:
        raise ValueError("run37_oracle_or_hidden_context")
    return env


def verify_envelope(env):
    if not isinstance(env, dict) or env != build_envelope(env.get("experiment_arm")):
        raise ValueError("run37_envelope_changed_or_unregistered")
    return True


def main():
    print(dumps(prereg()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
