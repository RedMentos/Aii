"""Fast batch real file+operator tests. Synthetic data, zero LLM/model dependencies."""
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from v13.operator import Operator
from v13.procedural_batch import ProceduralBatch, MAX_OUTPUT_BYTES


def activated(tmp_path, template="Row {i}: {value}"):
    worker = ProceduralBatch(tmp_path)
    proposed = worker.propose("repeat_demo", template)
    worker.activate("repeat_demo", proposed["sha256"][:12])
    return worker


def test_reviewed_plan_required_no_arbitrary_expression(tmp_path):
    r = ProceduralBatch(tmp_path)
    for bad in ("{i.__class__}", "{i[0]}", "{i:03d}", "{evil}", "{", "{value!r}"):
        with pytest.raises(ValueError):
            r.propose("unsafe", bad)
    p = r.propose("step_list", "Item {i} | {value}")
    assert p["model_calls"] == 0
    with pytest.raises(PermissionError):
        r.run("step_list", 2, "x")
    with pytest.raises(ValueError):
        r.activate("step_list", "not-the-sha")
    assert r.plan("step_list")["stage"] == "CANDIDATE"
    r.activate("step_list", p["sha256"][:12])
    result = r.run("step_list", 2, "hi", max_seconds=60)
    assert result["status"] == "DONE" and result["model_calls"] == 0
    assert Path(result["output_path"]).read_text("utf-8") == "Item 1 | hi\nItem 2 | hi\n"


def test_large_output_is_batched_resumable_and_cached(tmp_path):
    r = activated(tmp_path)
    first = r.run("repeat_demo", 11001, "x", max_rows=3000, max_seconds=60)
    assert first["status"] == "PAUSED" and first["rows"] == 3000
    again = r.run("repeat_demo", 11001, "x", max_rows=20000, max_seconds=60)
    assert again["status"] == "DONE" and again["rows"] == 11001
    path = Path(again["output_path"])
    data = path.read_bytes()
    assert data.count(b"\n") == 11001
    assert data.startswith(b"Row 1: x\n") and data.endswith(b"Row 11001: x\n")
    assert again["sha256"] == hashlib.sha256(data).hexdigest()
    cached = r.run("repeat_demo", 11001, "x", max_seconds=60)
    assert cached["rows_this_call"] == 0 and cached["bytes_this_call"] == 0
    assert cached["model_calls"] == 0


def test_recovery_discards_uncommitted_append_without_duplicate_rows(tmp_path):
    r = activated(tmp_path)
    first = r.run("repeat_demo", 5, "ok", max_rows=3, max_seconds=60)
    path = Path(first["output_path"])
    with path.open("ab") as f:
        f.write(b"CORRUPTED-UNCOMMITTED-TAIL")
    recovered = r.run("repeat_demo", 5, "ok", max_seconds=60)
    assert recovered["status"] == "DONE"
    assert path.read_text("utf-8") == "".join(f"Row {i}: ok\n" for i in range(1,6))


def test_tampered_committed_prefix_and_truncation_fail_closed(tmp_path):
    for fault in ("replace", "truncate"):
        root = tmp_path / fault
        r = activated(root)
        state = r.run("repeat_demo", 5, "safe", max_rows=2, max_seconds=60)
        path = Path(state["output_path"])
        if fault == "replace":
            data = bytearray(path.read_bytes())
            data[0] = ord("X")
            path.write_bytes(data)
        else:
            path.write_bytes(path.read_bytes()[:2])
        with pytest.raises(ValueError):
            r.run("repeat_demo", 5, "safe", max_seconds=60)


def test_plan_digest_tamper_and_retirement_fail_closed(tmp_path):
    r = activated(tmp_path)
    plan_file = r._plan_path("repeat_demo")
    data = json.loads(plan_file.read_text())
    data["code"]["template"] = "{i}: BAD"
    plan_file.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="tampered"):
        r.run("repeat_demo", 2)
    r2 = activated(tmp_path / "other")
    r2.retire("repeat_demo")
    with pytest.raises(PermissionError):
        r2.run("repeat_demo", 2)


def test_resource_bounds_and_no_external_destinations(tmp_path):
    r = activated(tmp_path)
    for n in (0, -1, 1000001, True):
        with pytest.raises(ValueError):
            r.run("repeat_demo", n)
    with pytest.raises(ValueError):
        r.run("repeat_demo", 2, "x" * 1025)
    with pytest.raises(ValueError):
        r.run("repeat_demo", 10, max_rows=0)
    with pytest.raises(ValueError):
        r.run("repeat_demo", 10, max_seconds=1000)
    # All writes must be inside the private V13 home, never a caller-chosen path.
    out = r.run("repeat_demo", 1, "../outside", max_seconds=60)
    assert Path(out["output_path"]).resolve().is_relative_to(tmp_path.resolve())
    assert MAX_OUTPUT_BYTES == 64 * 1024 * 1024


def test_operator_real_entrypoint_not_chat_model(tmp_path):
    runtime = SimpleNamespace(home=tmp_path, store=object())
    op = Operator(runtime)
    plan = json.loads(op.run(':fastbatch propose greeting "Hallo {i}: {value}"'))
    assert plan["stage"] == "CANDIDATE"
    with pytest.raises(PermissionError):
        op.run(':fastbatch run greeting 5 "welt"')
    activation = json.loads(op.run(f':fastbatch activate greeting {plan["sha256"][:12]}'))
    assert activation["stage"] == "ACTIVE"
    result = json.loads(op.run(':fastbatch run greeting 5000 "welt" --rows=1200'))
    assert result["rows"] == 1200 and result["status"] == "PAUSED"
    result = json.loads(op.run(':fastbatch run greeting 5000 "welt"'))
    assert result["rows"] == 5000 and result["status"] == "DONE"
    preview = json.loads(op.run(':fastbatch peek greeting 5000 "welt"'))
    assert "Hallo 1: welt" in preview["preview"]
    assert json.loads(op.run(':fastbatch status greeting'))["stage"] == "ACTIVE"
    assert json.loads(op.run(':fastbatch retire greeting'))["stage"] == "RETIRED"


def test_symlink_destination_is_rejected(tmp_path):
    r = activated(tmp_path)
    output = r.run("repeat_demo", 2, "safe", max_seconds=60)
    target = Path(output["output_path"])
    target.unlink()
    outside = tmp_path / "unrelated.txt"
    outside.write_text("untouched")
    target.symlink_to(outside)
    with pytest.raises(ValueError, match="symbolic"):
        r.run("repeat_demo", 2, "safe")
    assert outside.read_text() == "untouched"


def test_mini_checkpoint_not_one_db_call_per_item(tmp_path):
    r = activated(tmp_path, "x")
    out = r.run("repeat_demo", 32000, max_seconds=60)
    assert out["status"] == "DONE" and out["bytes"] == 64000
    assert out["rows_per_second"] > 0
    assert Path(out["output_path"]).stat().st_size == 64000
