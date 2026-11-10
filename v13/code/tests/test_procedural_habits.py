"""AG4 adjacent: FINAL-trace discovery -> human SHA activation -> fastbatch output.

Synthetic fixtures, no model weight downloads or external communication.
"""
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from v13.operator import Operator
from v13.procedural_batch import ProceduralBatch
from v13.procedural_habits import _extract, _generalise, discover


class MessageStore:
    def __init__(self, rows):
        self.items = rows

    def rows(self, sql, args=()):
        if "m.event_id=?" in sql:
            # Mock exactly the read-only joined query used on every activation.
            event = args[0]
            rows = [x for x in self.items if x["event_id"] == event
                    and x["role"] == "assistant"]
            return [{"text": x["text"], "status": x["status"],
                     "deleted": x.get("deleted", 0)}
                    for x in reversed(rows[:])][:1]
        assert "session_id=?" in sql
        assert "status='FINAL'" in sql
        assert "role='assistant'" in sql
        assert "s.deleted=0" in sql
        session, limit = args
        results = [
            row for row in self.items
            if row["session_id"] == session
            and row["status"] == "FINAL"
            and row["role"] == "assistant"
            and row.get("event_id")
            and row.get("deleted", 0) == 0
        ]
        return list(reversed(results))[:limit]


def message(event_id, text, session="chat_main", status="FINAL", role="assistant"):
    return {
        "event_id": event_id, "text": text, "session_id": session,
        "status": status, "role": role
    }


def fixture(tmp_path, rows):
    r = SimpleNamespace(store=MessageStore(rows), session="chat_main", home=tmp_path)
    return r, Operator(r)


def numbered(value, n=5, prefix="Task "):
    return "".join(f"{prefix}{i}: {value}\n" for i in range(1, n + 1))


def test_exact_histories_infer_parametric_repeat_without_leaking_experiences(tmp_path):
    first = numbered("orange", 5)
    second = numbered("apple", 5)
    r, op = fixture(tmp_path, [
        message("evt_older", first), message("evt_latest", second)
    ])
    out = json.loads(op.run(":fastbatch discover recurring"))
    assert out["stage"] == "CANDIDATE"
    assert out["kind"] == "PARAMETRIC_NUMBERED_REPEAT"
    assert out["template"] == "Task {i}: {value}"
    assert out["sample_values"] == ["apple", "orange"]
    assert out["source_count"] == 2 and out["observed_rows"] == [5, 5]
    assert out["model_calls"] == 0 and out["needs_operator_activation"]
    p = ProceduralBatch(tmp_path).plan("recurring")
    ev = p["code"]["source_evidence"]
    assert ev["source_event_ids"] == ["evt_latest", "evt_older"]
    assert ev["source_output_sha256"] == [
        hashlib.sha256(second.encode()).hexdigest(),
        hashlib.sha256(first.encode()).hexdigest()
    ]
    assert p["sha256"] == out["sha256"]
    with pytest.raises(PermissionError):
        op.run(':fastbatch run recurring 100 "banana"')
    assert json.loads(op.run(f":fastbatch activate recurring {out['sha256'][:12]}"))["stage"] == "ACTIVE"
    result = json.loads(op.run(':fastbatch run recurring 15000 "banana"'))
    assert result["status"] == "DONE"
    assert result["model_calls"] == 0
    assert result["rows"] == 15000
    rendered = Path(result["output_path"]).read_text()
    assert rendered.startswith("Task 1: banana\n")
    assert rendered.endswith("Task 15000: banana\n")
    assert rendered.count("\n") == 15000


def test_one_observed_completion_learns_only_literal_counter(tmp_path):
    r, op = fixture(tmp_path, [
        message("evt_one", numbered("fixed", 4))
    ])
    result = json.loads(op.run(":fastbatch discover literal"))
    assert result["kind"] == "LITERAL_NUMBERED_REPEAT"
    assert result["template"] == "Task {i}: fixed"
    assert result["source_count"] == 1
    assert "sample_values" not in result
    with pytest.raises(ValueError):
        op.run(":fastbatch activate literal BAD")
    op.run(f":fastbatch activate literal {result['sha256']}")
    path = json.loads(op.run(":fastbatch run literal 100"))["output_path"]
    assert Path(path).read_text().endswith("Task 100: fixed\n")


def test_only_final_current_session_source_is_eligible(tmp_path):
    bad = numbered("secret", 5)
    r, _ = fixture(tmp_path, [
        message("evt_cancelled", bad, status="CANCELLED"),
        message("evt_other", bad, session="chat_other"),
        message("evt_user", bad, role="user"),
        message("evt_draft", bad, status="DRAFT"),
    ])
    with pytest.raises(ValueError, match="no repeated numbered FINAL"):
        discover(r, "nothere")


@pytest.mark.parametrize("output", [
    "Task 1: x\nTask 2: x\n",
    "Task 1: x\nTask 2: x\nTask 3: x\nTask 5: x\n",
    "Task 01: x\nTask 02: x\nTask 03: x\nTask 04: x\n",
    "Task 1: x\nTask 2: x\nTask 3: x\nTask 4: x",
    "Task 1: x\nTask 2: y\nTask 3: x\nTask 4: x\n",
    "1 1\n2 2\n3 3\n4 4\n",
    "\n".join(f"{i}" for i in range(1, 68)) + "\n",
    "ignored unrelated plain text\n",
])
def test_fail_closed_on_inexact_malformed_or_ambiguous_histories(output):
    assert _extract(output) is None


def test_literal_braces_stay_literal_without_code_evaluation(tmp_path):
    source = "".join(f'{{"type": "list"}} {i}: OK\n' for i in range(1, 5))
    r, op = fixture(tmp_path, [message("evt_brace", source)])
    out = json.loads(op.run(":fastbatch discover braces"))
    assert "{{" in out["template"]
    op.run(f":fastbatch activate braces {out['sha256'][:12]}")
    result = json.loads(op.run(":fastbatch run braces 6"))
    text = Path(result["output_path"]).read_text()
    assert text == "".join(f'{{"type": "list"}} {i}: OK\n' for i in range(1, 7))


def test_different_prefix_cannot_overgeneralise_from_unrelated_outputs(tmp_path):
    rows = [message("evt_first", numbered("banana", 4, prefix="Count ")),
            message("evt_second", numbered("apple", 4, prefix="Task "))]
    r, op = fixture(tmp_path, rows)
    info = json.loads(op.run(":fastbatch discover narrow"))
    assert info["template"] == "Task {i}: apple"
    assert info["source_count"] == 1
    assert info["kind"] == "LITERAL_NUMBERED_REPEAT"


def test_history_bounds_and_source_hash_evidence_reject_tamper(tmp_path):
    r, op = fixture(tmp_path, [message("evt_one", numbered("safe"))])
    for cmd in (":fastbatch discover x --history=0", 
                ":fastbatch discover x --history=65", 
                ":fastbatch discover x --history=banana"):
        with pytest.raises(ValueError):
            op.run(cmd)
    data = json.loads(op.run(":fastbatch discover valid --history=2"))
    worker = ProceduralBatch(tmp_path)
    path = worker._plan_path("valid")
    payload = json.loads(path.read_text())
    payload["code"]["source_evidence"]["source_event_ids"] = ["evt_intruder"]
    path.write_text(json.dumps(payload))
    with pytest.raises(ValueError, match="tampered"):
        worker.activate("valid", data["sha256"][:12])


def test_must_use_the_local_operator_approval_boundary(tmp_path):
    r, op = fixture(tmp_path, [message("evt_one", numbered("safe"))])
    with pytest.raises(ValueError, match="lokale Operator"):
        op.run(":fastbatch discover exploit", origin="MODEL")
    assert not (tmp_path / "procedures").exists()


def test_value_generalisation_does_not_split_common_word_suffixes():
    a = _extract(numbered("apple", 4))
    b = _extract(numbered("orange", 4))
    v = _generalise(a, b)
    assert v["template"] == "Task {i}: {value}"
    assert v["sample_values"] == ("apple", "orange")


def test_real_store_final_to_discovered_plan_to_restart_and_12k_output(tmp_path):
    """Full local SQLite -> operator -> reviewed SHA -> checkpoint -> restart."""
    from v13.store import Store
    for name in ("data", "data/db", "data/blobs"):
        (tmp_path / name).mkdir(parents=True, exist_ok=True)
    st = Store(tmp_path)
    try:
        sid = st.new_session()
        for name in ("alpha", "beta"):
            event = st.event(sid, f"Please write numbered {name} rows")["event_id"]
            mid = st.message(sid, event, "assistant", numbered(name, 5))
            st.finish_message(mid, "FINAL", {
                "output_owner": "C5_REPORT_BROKER",
                "model_generated": True
            })
        runtime = SimpleNamespace(store=st, session=sid, home=tmp_path)
        op = Operator(runtime)
        proposed = json.loads(op.run(":fastbatch discover realhabit"))
        assert proposed["kind"] == "PARAMETRIC_NUMBERED_REPEAT"
        assert proposed["sample_values"] == ["beta", "alpha"]
        assert proposed["source_count"] == 2
        assert proposed["template"] == "Task {i}: {value}"
        st.close()
        st = None
        # The learned candidate must survive a full Store shutdown. Nothing
        # is automatically active after restart.
        reopened = Store(tmp_path)
        try:
            op = Operator(SimpleNamespace(store=reopened, session=sid, home=tmp_path))
            with pytest.raises(PermissionError):
                op.run(':fastbatch run realhabit 12000 "new" --rows=800')
            op.run(f':fastbatch activate realhabit {proposed["sha256"][:12]}')
            first = json.loads(op.run(':fastbatch run realhabit 12000 "new" --rows=800'))
            assert first["status"] == "PAUSED" and first["rows"] == 800
        finally:
            reopened.close()
        reopened = Store(tmp_path)
        try:
            op = Operator(SimpleNamespace(store=reopened, session=sid, home=tmp_path))
            finished = json.loads(op.run(':fastbatch run realhabit 12000 "new"'))
            assert finished["rows"] == 12000 and finished["status"] == "DONE"
            body = Path(finished["output_path"]).read_text()
            assert body.startswith("Task 1: new\n")
            assert body.endswith("Task 12000: new\n")
            assert body.count("\n") == 12000
            assert finished["sha256"] == hashlib.sha256(body.encode()).hexdigest()
            assert finished["model_calls"] == 0
        finally:
            reopened.close()
    finally:
        if st is not None:
            st.close()


def test_deleted_source_cannot_be_proposed_or_activated_in_real_store(tmp_path):
    from v13.store import Store
    for folder in ("data", "data/db", "data/blobs"):
        (tmp_path / folder).mkdir(parents=True, exist_ok=True)
    st = Store(tmp_path)
    try:
        sid = st.new_session()
        event = st.event(sid, "Number the rows")
        mid = st.message(sid, event["event_id"], "assistant", numbered("safe", 6))
        st.finish_message(mid, "FINAL", {})
        op = Operator(SimpleNamespace(store=st, session=sid, home=tmp_path))
        payload = json.loads(op.run(":fastbatch discover traced"))
        source_id = event["source_ref"]["source_id"]
        with st.tx() as connection:
            connection.execute("UPDATE sources SET deleted=1 WHERE id=?", (source_id,))
        with pytest.raises(ValueError, match="no longer FINAL"):
            op.run(f":fastbatch activate traced {payload['sha256'][:12]}")
        with pytest.raises(ValueError, match="no repeated numbered FINAL"):
            op.run(":fastbatch discover deleted")
        assert not ProceduralBatch(tmp_path)._plan_path("deleted").exists()
    finally:
        st.close()


def test_active_habit_refuses_revoked_or_changed_final_source(tmp_path):
    from v13.store import Store
    for folder in ("data", "data/db", "data/blobs"):
        (tmp_path / folder).mkdir(parents=True, exist_ok=True)
    st = Store(tmp_path)
    try:
        sid = st.new_session()
        e = st.event(sid, "Number the items")
        mid = st.message(sid, e["event_id"], "assistant", numbered("old", 6))
        st.finish_message(mid, "FINAL", {})
        op = Operator(SimpleNamespace(store=st, session=sid, home=tmp_path))
        proposal = json.loads(op.run(":fastbatch discover sensitive"))
        op.run(f":fastbatch activate sensitive {proposal['sha256'][:12]}")
        result = json.loads(op.run(":fastbatch run sensitive 50 --rows=10"))
        assert result["status"] == "PAUSED" and result["rows"] == 10
        with st.tx() as connection:
            connection.execute("UPDATE messages SET text=? WHERE id=?",
                               (numbered("changed", 6), mid))
        with pytest.raises(ValueError, match="source changed since review"):
            op.run(":fastbatch run sensitive 50")
        with pytest.raises(ValueError, match="source changed since review"):
            op.run(":fastbatch peek sensitive 50")
        with st.tx() as connection:
            connection.execute("UPDATE messages SET text=? WHERE id=?",
                               (numbered("old", 6), mid))
            connection.execute("UPDATE sources SET deleted=1 WHERE id=?",
                               (e["source_ref"]["source_id"],))
        with pytest.raises(ValueError, match="no longer FINAL"):
            op.run(":fastbatch run sensitive 50")
        # The generated source-derived output is not extended after revocation.
        assert Path(result["output_path"]).read_text().count("\n") == 10
        # Without a bound Store, direct API callers may not evade revocation.
        with pytest.raises(PermissionError, match="require the live V13 Store"):
            ProceduralBatch(tmp_path).run("sensitive", 50)
    finally:
        st.close()
