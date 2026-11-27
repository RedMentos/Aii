from __future__ import annotations

import hashlib
import importlib.util
import os
from pathlib import Path
import subprocess
import sys


CODE = Path(__file__).resolve().parents[1]
STAGER = CODE / "scripts" / "stage_integrated_candidate.py"


def _stage(code_dir: Path, destination: Path):
    spec = importlib.util.spec_from_file_location("v14_action_source_stager", STAGER)
    if spec is None or spec.loader is None:
        raise RuntimeError("V14 integrated Runtime stager unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.stage(code_dir, destination)


def test_staged_action_selection_retains_validated_current_and_organ_sources(tmp_path):
    source_focal = CODE / "v13" / "focal.py"
    before = hashlib.sha256(source_focal.read_bytes()).hexdigest()
    destination = tmp_path / "candidate"
    manifest = _stage(CODE, destination)

    assert manifest["status"] == "SHADOW_REVIEW_ONLY"
    overlay = manifest["action_source_overlay"]
    assert overlay["status"] == "SHADOW_REVIEW_ONLY"
    assert overlay["source_pins"]["v13/focal.py"] == "a0588a768cc91266ef02243bcfda2e631860d8ad"
    assert "v13/focal.py" in manifest["replaced_files"]
    assert hashlib.sha256(source_focal.read_bytes()).hexdigest() == before

    script = r'''
import json
import tempfile
from pathlib import Path

from v13.focal import ActionGate
from v13.runtime import Runtime


def event(runtime, text):
    envelope = runtime.store.event(runtime.session, text)
    return {
        "event_id": envelope["event_id"],
        "brain_generation_id": envelope["brain_generation_id"],
        "source_ref": envelope["source_ref"],
    }


def source(runtime, text):
    return runtime.store.source(text)


def select(gate, e, coalition):
    return gate.select(
        e,
        route="both",
        direct=False,
        resource_state="NORMAL",
        coalition=coalition,
        view={"uncertainty": 0.1, "conflict": 0.2},
        age={"tools": False},
    )


def last_packet(runtime, e):
    row = runtime.store.one(
        "SELECT payload FROM packets WHERE kind='ActionSelection' AND event_id=? "
        "ORDER BY rowid DESC LIMIT 1",
        (e["event_id"],),
    )
    return json.loads(row["payload"])


with tempfile.TemporaryDirectory(prefix="v14-action-context-") as root:
    runtime = Runtime(Path(root))
    try:
        runtime.sleep.cycle.set_policy("enabled", "off")
        gate = ActionGate(runtime.store)

        # Current user source plus B1/B2, Memory, World, Self and B3 sources.
        e = event(runtime, "user query")
        refs = {
            "B1_DETAIL": source(runtime, "precise body evidence"),
            "B2_GIST": source(runtime, "broad body evidence"),
            "MEMORY": source(runtime, "retrieved memory evidence"),
            "WORLD": source(runtime, "world transition evidence"),
            "SELF": source(runtime, "self-model evidence"),
            "B3_CALLOSUM": source(runtime, "callosum control context"),
        }
        coalition = [
            {"item_id": "b1-1", "source_kind": "B1_DETAIL", "priority": 0.8,
             "source_refs": [refs["B1_DETAIL"]]},
            {"item_id": "b2-1", "source_kind": "B2_GIST", "priority": 0.7,
             "source_refs": [refs["B2_GIST"], refs["B1_DETAIL"]]},
            {"item_id": "mem-1", "source_kind": "MEMORY", "priority": 0.5,
             "source_refs": [refs["MEMORY"]]},
            {"item_id": "world-1", "source_kind": "WORLD", "priority": 0.4,
             "source_refs": [refs["WORLD"]]},
            {"item_id": "self-1", "source_kind": "SELF", "priority": 0.3,
             "source_refs": [refs["SELF"]]},
            {"item_id": "b3-1", "source_kind": "B3_CALLOSUM", "priority": 0.2,
             "source_refs": [refs["B3_CALLOSUM"]]},
        ]
        result = select(gate, e, coalition)
        packet = last_packet(runtime, e)
        expected = [e["source_ref"], *refs.values()]
        assert packet["source_refs"] == expected
        assert packet["provenance"] == expected
        assert packet["source_ref_count"] == len(expected)
        assert packet["source_refs_truncated"] is False
        assert packet["context_input_organs"] == [
            "A_SOURCE", "B1_DETAIL", "B2_GIST", "MEMORY", "WORLD", "SELF", "B3_CALLOSUM"
        ]
        assert [x["item_id"] for x in packet["context_sources"]] == [
            "b1-1", "b2-1", "mem-1", "world-1", "self-1", "b3-1"
        ]
        assert all(x["source_bound"] for x in packet["context_sources"])
        assert result["source_refs"] == expected
        assert result["context_input_organs"] == packet["context_input_organs"]

        # Invalid or stale source bytes fail closed before a C5 action packet.
        e_bad = event(runtime, "query with invalid context")
        valid = source(runtime, "valid source")
        invalid = dict(valid, sha256="0" * 64)
        before = runtime.store.one(
            "SELECT COUNT(*) AS n FROM packets WHERE kind='ActionSelection' AND event_id=?",
            (e_bad["event_id"],),
        )["n"]
        try:
            select(gate, e_bad, [{
                "item_id": "bad-memory", "source_kind": "MEMORY",
                "priority": 1.0, "source_refs": [invalid],
            }])
        except ValueError:
            pass
        else:
            raise AssertionError("invalid source reference was admitted")
        after = runtime.store.one(
            "SELECT COUNT(*) AS n FROM packets WHERE kind='ActionSelection' AND event_id=?",
            (e_bad["event_id"],),
        )["n"]
        assert after == before

        # The per-item context view is bounded, while the full source union
        # remains in the packet provenance up to the separate 64-ref limit.
        e_many = event(runtime, "many context sources")
        many = []
        many_refs = []
        for index in range(18):
            ref = source(runtime, f"source {index}")
            many_refs.append(ref)
            many.append({
                "item_id": f"memory-{index}",
                "source_kind": "MEMORY",
                "priority": 1.0 / (index + 1),
                "source_refs": [ref],
            })
        select(gate, e_many, many)
        many_packet = last_packet(runtime, e_many)
        assert many_packet["source_refs"] == [e_many["source_ref"], *many_refs]
        assert many_packet["source_ref_count"] == 19
        assert many_packet["source_refs_truncated"] is False
        assert len(many_packet["context_sources"]) == 16
        assert many_packet["context_sources_truncated"] is True
        assert many_packet["context_input_organs"] == ["A_SOURCE", "MEMORY"]
        assert runtime.store.integrity(True) == []
    finally:
        runtime.close()

print("PASS: staged C5 ActionSelection carries validated current and multi-organ source context")
'''
    env = dict(os.environ)
    env["PYTHONPATH"] = str(destination)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=destination,
        env=env,
        text=True,
        capture_output=True,
        timeout=90,
    )
    assert result.returncode == 0, result.stdout + "\n" + result.stderr
    assert "PASS: staged C5 ActionSelection" in result.stdout
