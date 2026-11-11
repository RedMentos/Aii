"""End-to-end imported line values -> approved template -> durable fast execution."""
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from v13.operator import Operator
from v13.procedural_batch import ProceduralBatch
from v13.procedural_inputs import ProceduralInputs


def files(tmp_path, values):
    source = tmp_path / "source.txt"
    source.write_text("".join(x + "\n" for x in values), encoding="utf-8")
    return source, hashlib.sha256(source.read_bytes()).hexdigest()


def op_for(tmp_path):
    return Operator(SimpleNamespace(home=tmp_path / "brain", store=None))


def active_plan(op):
    p = json.loads(op.run(':fastbatch propose dynamic "Task {i}: {value}"'))
    op.run(f":fastbatch activate dynamic {p['sha256'][:12]}")
    return p


def test_operator_import_approved_plan_resume_5000_distinct_values(tmp_path):
    values = [f"Ä / record {i} / Ω" for i in range(1, 5001)]
    source, h = files(tmp_path, values)
    op = op_for(tmp_path)
    active_plan(op)
    imported = json.loads(op.run(f":fastbatch input import testlines {source} {h}"))
    assert imported == {
        "name": "testlines", "rows": 5000, "bytes": source.stat().st_size,
        "sha256": h, "status": "IMPORTED", "model_calls": 0,
    }
    status = json.loads(op.run(":fastbatch input status testlines"))
    assert status["source_bytes_verified"] is True
    first = json.loads(op.run(":fastbatch input run dynamic testlines --rows=800"))
    assert first["status"] == "PAUSED" and first["rows"] == 800
    assert first["model_calls"] == 0
    op = op_for(tmp_path)
    done = json.loads(op.run(":fastbatch input run dynamic testlines"))
    assert done["status"] == "DONE" and done["rows"] == 5000
    result = Path(done["output_path"]).read_text(encoding="utf-8")
    assert result == "".join(f"Task {i}: {value}\n" for i, value in enumerate(values, 1))
    assert hashlib.sha256(result.encode()).hexdigest() == done["sha256"]
    second = json.loads(op.run(":fastbatch input run dynamic testlines"))
    assert second["rows_this_call"] == 0 and second["sha256"] == done["sha256"]
    assert Path(done["output_path"]).stat().st_size == done["bytes"]


def test_wrong_sha_and_missing_approval_never_write_output(tmp_path):
    source, sha = files(tmp_path, ["a", "b", "c"])
    op = op_for(tmp_path)
    with pytest.raises(ValueError, match="digest mismatch"):
        op.run(f":fastbatch input import bad {source} {'0' * 64}")
    brain = tmp_path / "brain"
    assert not (brain / "procedures" / "fastbatch" / "inputs" / "bad.txt").exists()
    proposal = json.loads(op.run(':fastbatch propose candidate "row {i}: {value}"'))
    op.run(f":fastbatch input import good {source} {sha}")
    with pytest.raises(PermissionError, match="activate"):
        op.run(":fastbatch input run candidate good")
    assert not list((brain / "procedures" / "fastbatch" / "jobs").glob("input_candidate*.txt"))
    with pytest.raises(ValueError):
        op.run(":fastbatch input run candidate good --rows=0")


@pytest.mark.parametrize("raw", [
    b"abc", b"\n", b"hello\r\n", b"\xff\n",
    b"a\x00b\n", b"z" * 1025 + b"\n",
])
def test_invalid_sources_fail_before_publish(tmp_path, raw):
    source = tmp_path / "raw.txt"
    source.write_bytes(raw)
    digest = hashlib.sha256(raw).hexdigest()
    op = op_for(tmp_path)
    with pytest.raises(ValueError):
        op.run(f":fastbatch input import invalid {source} {digest}")
    assert not (tmp_path / "brain" / "procedures" / "fastbatch" / "inputs" / "invalid.json").exists()


def test_import_rejects_symlink_and_hardlinked_source(tmp_path):
    source, digest = files(tmp_path, ["one", "two"])
    op = op_for(tmp_path)
    linked = tmp_path / "linked.txt"
    linked.symlink_to(source)
    with pytest.raises(ValueError, match="ordinary regular"):
        op.run(f":fastbatch input import symlink {linked} {digest}")
    linked.unlink()
    linked.hardlink_to(source)
    with pytest.raises(ValueError, match="unsafe or oversized"):
        op.run(f":fastbatch input import hardlinked {linked} {digest}")
    assert source.read_text() == "one\ntwo\n"


def test_tampered_imported_bytes_or_metadata_fail_before_resume(tmp_path):
    source, digest = files(tmp_path, ["one", "two", "three"])
    op = op_for(tmp_path)
    active_plan(op)
    op.run(f":fastbatch input import lines {source} {digest}")
    result = json.loads(op.run(":fastbatch input run dynamic lines --rows=1"))
    path = Path(result["output_path"])
    old_output = path.read_bytes()
    imported = tmp_path / "brain" / "procedures" / "fastbatch" / "inputs" / "lines.txt"
    imported.chmod(0o600)
    imported.write_text("bad\ntwo\nthree\n")
    with pytest.raises(ValueError, match="source bytes changed"):
        op.run(":fastbatch input run dynamic lines")
    assert path.read_bytes() == old_output
    imported.write_bytes(source.read_bytes())
    metadata = imported.with_suffix(".json")
    obj = json.loads(metadata.read_text())
    obj["rows"] = 100
    metadata.write_text(json.dumps(obj))
    with pytest.raises(ValueError, match="tampered input metadata"):
        op.run(":fastbatch input run dynamic lines")
    assert path.read_bytes() == old_output


def test_input_prefix_cursor_tamper_rejected_and_durable_rows_unchanged(tmp_path):
    source, digest = files(tmp_path, ["alpha", "beta", "gamma", "delta", "epsilon"])
    op = op_for(tmp_path)
    active_plan(op)
    op.run(f":fastbatch input import vals {source} {digest}")
    result = json.loads(op.run(":fastbatch input run dynamic vals --rows=2"))
    output = Path(result["output_path"])
    original = output.read_bytes()
    bank = ProceduralInputs(tmp_path / "brain")
    state, _, _ = bank._job_files(bank.batch.plan("dynamic"), "vals", bank._metadata("vals"))
    payload = json.loads(state.read_text())
    payload["input_offset"] += 1
    state.write_text(json.dumps(payload))
    with pytest.raises(ValueError, match="input checkpoint cursor or prefix hash"):
        op.run(":fastbatch input run dynamic vals")
    assert output.read_bytes() == original


def test_imported_data_requires_explicit_operator_origin(tmp_path):
    source, digest = files(tmp_path, ["one", "two"])
    op = op_for(tmp_path)
    with pytest.raises(ValueError, match="lokale Operator"):
        op.run(f":fastbatch input import private {source} {digest}", origin="MODEL")
    assert not (tmp_path / "brain" / "procedures").exists()
