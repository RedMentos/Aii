from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile


CODE = Path(__file__).resolve().parents[1]
STAGER = CODE / "scripts" / "stage_integrated_candidate.py"


def _load_stager():
    spec = importlib.util.spec_from_file_location("v14_focal_scale_stager", STAGER)
    if spec is None or spec.loader is None:
        raise RuntimeError("pinned integrated stage builder unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_review_stage_applies_only_scale_aware_c4_overlay(tmp_path):
    source = CODE / "v13" / "focal.py"
    raw = source.read_bytes()
    before = hashlib.sha1(
        b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw
    ).hexdigest()
    assert before == "a0588a768cc91266ef02243bcfda2e631860d8ad"
    destination = tmp_path / "candidate"
    manifest = _load_stager().stage(CODE, destination)
    assert manifest["status"] == "SHADOW_REVIEW_ONLY"
    assert "v13/focal.py" in manifest["replaced_files"]
    assert manifest["files_sha256"]["v13/focal.py"]

    staged = (destination / "v13" / "focal.py").read_bytes()
    assert b"SCALE_AWARE_C4_RULE = 'DISJOINT_SAME_SOURCE_SPANS_ONLY'" in staged
    assert b"_has_disjoint_source_evidence" in staged
    assert b"_scale_aware_redundancy(c,a,threshold)" in staged
    assert b"CROSS_SCALE_REDUNDANCY_FACTOR" not in staged
    assert hashlib.sha256(staged).hexdigest() == manifest["files_sha256"]["v13/focal.py"]
    after_raw = source.read_bytes()
    after = hashlib.sha1(
        b"blob " + str(len(after_raw)).encode("ascii") + b"\0" + after_raw
    ).hexdigest()
    assert after == before, "the historical V13 focal.py source was modified"



def test_runtime_consumes_both_overlapping_body_offers_in_c3_context(tmp_path):
    destination = tmp_path / "candidate"
    _load_stager().stage(CODE, destination)

    script = r'''
import json
import sys
import time
from pathlib import Path
from unittest.mock import Mock

from v13.operator import Operator
from v13.runtime import Runtime
from v13 import focal

# Direct C4 negative controls: cross-scale overlap is discounted, but same-role
# duplicates and body/memory overlap still compete normally.
same = "The total budget is 391 rent 120 plus food 271"
def ref(start, end, source_id="source-1", digest="a"*64, modality="text"):
    return {"source_id": source_id, "sha256": digest, "char_start": start,
            "char_end": end, "modality": modality}

def candidate(kind, item_id, refs=(), text_value=None):
    return focal.item(kind, item_id, list(refs), same if text_value is None else text_value, "evt",
                      uncertainty=0.2, salience=0.0, goal=0.5,
                      utility=0.8, sq=1.0, cost=0.0)

b1 = candidate("B1_DETAIL", "b1", [ref(0, 12)], "Rent is 120.")
b2 = candidate("B2_GIST", "b2", [ref(20, 32)], "Food is 271.")
active, rest = focal.admit([b1, b2], 2, 0.45)
assert {item["source_kind"] for item in active} == {"B1_DETAIL", "B2_GIST"}

overlap = [
    candidate("B1_DETAIL", "b1-overlap", [ref(0, 20)]),
    candidate("B2_GIST", "b2-overlap", [ref(10, 30)]),
]
active, rest = focal.admit(overlap, 2, 0.45)
assert len(active) == 1, "overlapping source evidence must retain the full penalty"

cross_source = [
    candidate("B1_DETAIL", "b1-source", [ref(0, 12, "source-1")]),
    candidate("B2_GIST", "b2-source", [ref(20, 32, "source-2")]),
]
active, rest = focal.admit(cross_source, 2, 0.45)
assert len(active) == 1, "different source identities are not assumed complementary"

hash_mismatch = [
    candidate("B1_DETAIL", "b1-hash", [ref(0, 12, digest="a"*64)]),
    candidate("B2_GIST", "b2-hash", [ref(20, 32, digest="b"*64)]),
]
active, rest = focal.admit(hash_mismatch, 2, 0.45)
assert len(active) == 1, "different source digests must not receive a discount"

modality_mismatch = [
    candidate("B1_DETAIL", "b1-modality", [ref(0, 12, modality="text")]),
    candidate("B2_GIST", "b2-modality", [ref(20, 32, modality="audio")]),
]
active, rest = focal.admit(modality_mismatch, 2, 0.45)
assert len(active) == 1, "different modalities must retain the full redundancy penalty"

malformed_digest = [
    candidate("B1_DETAIL", "b1-bad-digest", [ref(0, 12, digest="g"*64)]),
    candidate("B2_GIST", "b2-bad-digest", [ref(20, 32, digest="g"*64)]),
]
active, rest = focal.admit(malformed_digest, 2, 0.45)
assert len(active) == 1, "non-hex digests must never receive a discount"

zero_length = [
    candidate("B1_DETAIL", "b1-zero", [ref(0, 12)]),
    candidate("B2_GIST", "b2-zero", [ref(20, 20)]),
]
active, rest = focal.admit(zero_length, 2, 0.45)
assert len(active) == 1, "zero-length spans must retain the full penalty"

reversed_span = [
    candidate("B1_DETAIL", "b1-reversed", [ref(0, 12)]),
    candidate("B2_GIST", "b2-reversed", [ref(32, 20)]),
]
active, rest = focal.admit(reversed_span, 2, 0.45)
assert len(active) == 1, "reversed spans must retain the full penalty"

redundant_paraphrase = [
    candidate("B1_DETAIL", "b1-paraphrase", [ref(0, 12)], "The budget total is 391."),
    candidate("B2_GIST", "b2-paraphrase", [ref(20, 32)], "391 is the total budget."),
]
active, rest = focal.admit(redundant_paraphrase, 2, 0.45)
assert len(active) == 1, "lexically redundant paraphrases retain the full penalty even with disjoint spans"

mixed_source_refs = [
    candidate("B1_DETAIL", "b1-mixed", [ref(0, 12), ref(40, 52, source_id="source-2")]),
    candidate("B2_GIST", "b2-mixed", [ref(20, 32)]),
]
active, rest = focal.admit(mixed_source_refs, 2, 0.45)
assert len(active) == 1, "mixed-source offers cannot claim one shared source signature"

same_role = candidate("B1_DETAIL", "b1-duplicate", [ref(20, 32)])
active, rest = focal.admit([candidate("B1_DETAIL", "b1", [ref(0, 12)]), same_role], 2, 0.45)
assert len(active) == 1 and same_role["admission"] == "BELOW_THRESHOLD"

memory = candidate("MEMORY", "memory", [ref(20, 32)])
active, rest = focal.admit([candidate("B1_DETAIL", "b1", [ref(0, 12)]), memory], 2, 0.45)
assert len(active) == 1 and memory["admission"] == "BELOW_THRESHOLD"

no_refs = [candidate("B1_DETAIL", "b1-no-ref"), candidate("B2_GIST", "b2-no-ref")]
active, rest = focal.admit(no_refs, 2, 0.45)
assert len(active) == 1, "missing source evidence must not receive a discount"

active, rest = focal.admit(
    [candidate("B1_DETAIL", "b1", [ref(0, 12)]),
     candidate("B2_GIST", "b2", [ref(20, 32)])], 1, 0.45
)
assert len(active) == 1, "scale diversity must not exceed configured capacity"

seen = {}
class Runner:
    def __init__(self, role):
        self.role = role
        self.model = "synthetic-no-native-model"
        self.memory = None
        self.last_metrics = {
            "role": role, "status": "FINAL", "generated_tokens": 8,
            "prompt_tokens": 24, "ttft_s": 0.01, "duration_s": 0.02,
        }
    @property
    def memory_delivery_binding(self):
        return None
    def pids(self):
        return []
    def generate(self, messages, *args, **kwargs):
        if self.role in ("B1_DETAIL", "B2_GIST"):
            offer = {
                "summary": "Rent is 120." if self.role == "B1_DETAIL" else "Food is 271.",
                "uncertainty": "low",
                "needs_reentry": False,
                "quotes": ["Rent is 120." if self.role == "B1_DETAIL" else "Food is 271."],
            }
            return iter([json.dumps(offer)])
        seen["c3_messages"] = messages
        return iter(["The total budget is 391."])

home = Path(sys.argv[1])
r = Runtime(home)
try:
    r.sleep.cycle.set_policy("enabled", "off")
    Operator(r).run(":effort max")
    r.cfg.update(deadline_seconds=60, observer_seconds=8, max_reentry=0,
                 b2_quote_select="off", offer_quote_context_chars=0)
    r._route = Mock(return_value=("both", {"source": "SYNTHETIC_SCALE_DIVERSITY"}))
    r.learner.decide = Mock(return_value={"learned": False, "action": "both"})
    r.learner.output_delta = Mock(return_value=None)
    r.pool.get = lambda role: Runner(role)

    r.submit("Compute the total budget: Rent is 120. Food is 271. Explain the detailed items and overall picture.")
    until = time.monotonic() + 25
    while not r.idle() and time.monotonic() < until:
        time.sleep(0.01)
    assert r.idle(), "synthetic Runtime did not finish"
    answer = r.last_answer()
    assert answer and answer["status"] == "FINAL", answer
    meta = json.loads(answer["metadata"])
    assert len(meta.get("selected_offer_ids", [])) == 2, meta.get("selected_offer_ids")

    rows = r.store.rows(
        "SELECT payload FROM packets WHERE kind='OfferPacket' AND event_id=? ORDER BY rowid",
        (answer["event_id"],),
    )
    roles = {json.loads(row["payload"])["role"] for row in rows}
    assert roles == {"B1_DETAIL", "B2_GIST"}, roles

    messages = seen.get("c3_messages")
    assert messages, "C3 did not receive a prompt"
    rendered = "\n".join(item.get("content", "") for item in messages if isinstance(item, dict))
    assert "B1_DETAIL" in rendered and "B2_GIST" in rendered, rendered
    assert "Rent is 120." in rendered and "Food is 271." in rendered, rendered
    print("PASS: real staged Runtime/SQLite selected both B1/B2 offers and delivered both to C3; model outputs were synthetic")
finally:
    r.close()
'''
    env = dict(os.environ)
    env["PYTHONPATH"] = str(destination)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    with tempfile.TemporaryDirectory(prefix="v14-focal-home-") as home:
        result = subprocess.run(
            [sys.executable, "-c", script, str(Path(home) / "private-home")],
            cwd=destination, env=env, text=True, capture_output=True, timeout=45,
        )
    assert result.returncode == 0, result.stdout + "\n" + result.stderr
    assert "PASS: real staged Runtime/SQLite" in result.stdout
