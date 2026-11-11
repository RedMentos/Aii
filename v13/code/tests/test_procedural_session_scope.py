"""Learned fast procedures remain bound to the original local chat session."""
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from v13.operator import Operator
from v13.procedural_batch import ProceduralBatch
from v13.procedural_inputs import ProceduralInputs
from v13.store import Store


def _store(tmp_path):
    for path in ("data", "data/db", "data/blobs"):
        (tmp_path / path).mkdir(parents=True, exist_ok=True)
    return Store(tmp_path)


def _op(store, sid, home):
    return Operator(SimpleNamespace(store=store, session=sid, home=home))


def _learn(st, sid, home, name="plan"):
    event = st.event(sid, "List five consecutive tasks")["event_id"]
    mid = st.message(sid, event, "assistant",
                     "".join(f"Task {i}: valid\n" for i in range(1, 6)))
    st.finish_message(mid, "FINAL", {})
    op = _op(st, sid, home)
    proposed = json.loads(op.run(f":fastbatch discover {name}"))
    assert proposed["needs_operator_activation"]
    assert op.run(f":fastbatch activate {name} {proposed['sha256'][:12]}")
    return op, proposed


def test_learned_procedure_refuses_cross_chat_run_and_read_without_modification(tmp_path):
    st = _store(tmp_path)
    try:
        sid_a, sid_b = st.new_session(), st.new_session()
        op_a, _ = _learn(st, sid_a, tmp_path)
        first = json.loads(op_a.run(":fastbatch run plan 200 --rows=5"))
        output_path = Path(first["output_path"])
        original = output_path.read_bytes()
        op_b = _op(st, sid_b, tmp_path)
        for command in (":fastbatch run plan 200", ":fastbatch peek plan 200",
                        ":fastbatch read plan 200", ":fastbatch activate plan " +
                        json.loads(op_a.run(":fastbatch status plan"))["sha256"]):
            with pytest.raises(PermissionError, match="original chat session"):
                op_b.run(command)
        assert output_path.read_bytes() == original
        # Same session can resume after process/operator reconstruction.
        op_a = _op(st, sid_a, tmp_path)
        resumed = json.loads(op_a.run(":fastbatch run plan 200"))
        assert resumed["rows"] == 200
        assert output_path.read_text().count("\n") == 200
    finally:
        st.close()


def test_session_scope_propagates_to_input_transformation_and_stream(tmp_path):
    st = _store(tmp_path)
    try:
        sid_a, sid_b = st.new_session(), st.new_session()
        op_a, _ = _learn(st, sid_a, tmp_path)
        source = tmp_path / "reviewed_lines.txt"
        source.write_text("apple\nbanana\ncherry\n", encoding="utf-8")
        digest = hashlib.sha256(source.read_bytes()).hexdigest()
        op_a.run(f":fastbatch input import values {source} {digest}")
        partial = json.loads(op_a.run(":fastbatch input run plan values --rows=1"))
        out = Path(partial["output_path"])
        before = out.read_bytes()
        op_b = _op(st, sid_b, tmp_path)
        for cmd in (":fastbatch input run plan values",
                    ":fastbatch input read plan values"):
            with pytest.raises(PermissionError, match="original chat session"):
                op_b.run(cmd)
        with pytest.raises(PermissionError, match="original chat session"):
            list(ProceduralInputs(tmp_path, store=st, session=sid_b)
                 .iter_output("plan", "values"))
        assert out.read_bytes() == before
        result = json.loads(_op(st, sid_a, tmp_path).run(":fastbatch input run plan values"))
        assert result["rows"] == 3 and result["status"] == "DONE"
    finally:
        st.close()


def test_source_session_not_forged_through_digest_rehash_or_missing_store(tmp_path):
    st = _store(tmp_path)
    try:
        sid_a, sid_b = st.new_session(), st.new_session()
        op_a, p = _learn(st, sid_a, tmp_path)
        file = ProceduralBatch(tmp_path)._plan_path("plan")
        entry = json.loads(file.read_text(encoding="utf-8"))
        evidence = entry["code"]["source_evidence"]
        assert evidence["source_session_id"] == sid_a
        assert evidence["scope"] == "CURRENT_SESSION_ONLY"
        # A forged payload with recomputed code SHA is no substitute for
        # matching the active Store session and original authoritative event.
        entry["code"]["source_evidence"]["source_session_id"] = sid_b
        from v13.procedural_batch import _sha
        entry["sha256"] = _sha(entry["code"])
        file.write_text(json.dumps(entry), encoding="utf-8")
        with pytest.raises(ValueError, match="no longer FINAL"):
            _op(st, sid_b, tmp_path).run(":fastbatch run plan 40")
        # Original plan metadata still fails cross-chat execution when a Store
        # is supplied but the active session identifier is absent.
        entry["code"]["source_evidence"]["source_session_id"] = sid_a
        entry["sha256"] = _sha(entry["code"])
        file.write_text(json.dumps(entry), encoding="utf-8")
        with pytest.raises(PermissionError, match="original chat session"):
            ProceduralBatch(tmp_path, store=st).run("plan", 40)
        with pytest.raises(PermissionError, match="live V13 Store"):
            ProceduralBatch(tmp_path, session=sid_a).run("plan", 40)
    finally:
        st.close()


def test_local_manual_literal_plan_still_can_run_with_operator_in_other_chat(tmp_path):
    st = _store(tmp_path)
    try:
        sid_a, sid_b = st.new_session(), st.new_session()
        op_a = _op(st, sid_a, tmp_path)
        plan = json.loads(op_a.run(':fastbatch propose simple "Index {i}"'))
        op_a.run(f":fastbatch activate simple {plan['sha256'][:12]}")
        result = json.loads(_op(st, sid_b, tmp_path).run(":fastbatch run simple 25"))
        assert result["rows"] == 25
        assert result["model_calls"] == 0
        assert Path(result["output_path"]).read_text().endswith("Index 25\n")
    finally:
        st.close()
