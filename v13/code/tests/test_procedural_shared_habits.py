"""Explicit local consent turns a learned *pure* text pattern into a shared habit."""
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from v13.operator import Operator
from v13.procedural_batch import ProceduralBatch
from v13.store import Store


@pytest.fixture
def shared(tmp_path):
    for name in ("data", "data/db", "data/blobs"):
        (tmp_path / name).mkdir(parents=True, exist_ok=True)
    store = Store(tmp_path)
    a, b = store.new_session(), store.new_session()
    for val in ("orange", "apple"):
        e = store.event(a, "Write tasks")["event_id"]
        m = store.message(a, e, "assistant",
                          "".join(f"Task {i}: {val}\n" for i in range(1, 6)))
        store.finish_message(m, "FINAL", {})
    opa = Operator(SimpleNamespace(home=tmp_path, store=store, session=a))
    opb = Operator(SimpleNamespace(home=tmp_path, store=store, session=b))
    proposed = json.loads(opa.run(":fastbatch discover shared"))
    assert proposed["kind"] == "PARAMETRIC_NUMBERED_REPEAT"
    opa.run(f":fastbatch activate shared {proposed['sha256'][:12]}")
    yield store, a, b, opa, opb, proposed, tmp_path
    store.close()


def _approve(shared):
    _, _, _, opa, _, proposal, _ = shared
    return json.loads(opa.run(f":fastbatch share shared {proposal['sha256']} YES"))


def test_cross_chat_sharing_requires_full_sha_and_explicit_yes(shared):
    store, a, b, opa, opb, p, home = shared
    with pytest.raises(PermissionError, match="original chat"):
        opb.run(':fastbatch run shared 500 "new"')
    for command in (f":fastbatch share shared {p['sha256'][:12]} YES",
                    f":fastbatch share shared {p['sha256']} Y"):
        with pytest.raises(PermissionError, match="full SHA256"):
            opa.run(command)
    with pytest.raises(PermissionError, match="only originating chat"):
        opb.run(f":fastbatch share shared {p['sha256']} YES")
    with pytest.raises(ValueError, match="lokale Operator"):
        opa.run(f":fastbatch share shared {p['sha256']} YES", origin="MODEL")
    saved = _approve(shared)
    assert saved["share_scope"] == "PROMOTED_PURE_TEXT"
    assert saved["permissions"] == "PURE_TEXT_ONLY_NO_TOOLS"
    run = json.loads(opb.run(':fastbatch run shared 500 "new"'))
    assert run["status"] == "DONE" and run["rows"] == 500
    assert Path(run["output_path"]).read_text().endswith("Task 500: new\n")
    assert json.loads(opb.run(":fastbatch status shared"))["share_scope"] == "PROMOTED_PURE_TEXT"


def test_unshare_revokes_later_chunks_and_future_cross_chat_runs(shared):
    st, a, b, opa, opb, p, home = shared
    _approve(shared)
    result = json.loads(opb.run(':fastbatch run shared 100 "new"'))
    source_reader = ProceduralBatch(home, store=st, session=b)
    generator = source_reader.iter_output("shared", 100, "new", chunk_bytes=7)
    assert next(generator).startswith("Task")
    assert json.loads(opa.run(":fastbatch unshare shared"))["share_scope"] == "SOURCE_SESSION"
    with pytest.raises(PermissionError, match="original chat"):
        next(generator)
    generator.close()
    with pytest.raises(PermissionError, match="original chat"):
        opb.run(':fastbatch read shared 100 "new"')
    assert Path(result["output_path"]).read_text().count("\n") == 100
    # Exact approved plan still works in its original session.
    assert json.loads(opa.run(':fastbatch read shared 100 "new"'))["text"].startswith("Task 1")


def test_source_deletion_refuses_even_explicitly_shared_input_and_output(shared):
    st, a, b, opa, opb, p, home = shared
    _approve(shared)
    source = home / "input.txt"
    source.write_text("a\nb\nc\n", encoding="utf-8")
    h = hashlib.sha256(source.read_bytes()).hexdigest()
    opa.run(f":fastbatch input import pairs {source} {h}")
    partial = json.loads(opb.run(":fastbatch input run shared pairs --rows=1"))
    original = Path(partial["output_path"]).read_bytes()
    event = p["source_event_ids"][0]
    e = st.one("SELECT source_id FROM events WHERE id=?", (event,))
    with st.tx() as c:
        c.execute("UPDATE sources SET deleted=1 WHERE id=?", (e["source_id"],))
    with pytest.raises(ValueError, match="no longer FINAL"):
        opb.run(":fastbatch input run shared pairs")
    with pytest.raises(ValueError, match="no longer FINAL"):
        opb.run(":fastbatch input read shared pairs")
    with pytest.raises(ValueError, match="no longer FINAL"):
        opb.run(':fastbatch run shared 5 "fresh"')
    assert Path(partial["output_path"]).read_bytes() == original


def test_no_sharing_literal_or_tampered_receipts(shared):
    st, a, b, opa, opb, p, home = shared
    # A source-only static output may contain private text. Never share it.
    only = st.event(a, "Text")["event_id"]
    m = st.message(a, only, "assistant",
                   "".join(f"Secret {i}: fixed\n" for i in range(1, 6)))
    st.finish_message(m, "FINAL", {})
    literal = json.loads(opa.run(":fastbatch discover literal --history=1"))
    assert literal["kind"] == "LITERAL_NUMBERED_REPEAT"
    opa.run(f":fastbatch activate literal {literal['sha256'][:12]}")
    with pytest.raises(PermissionError, match="only reviewed parametric"):
        opa.run(f":fastbatch share literal {literal['sha256']} YES")
    file = ProceduralBatch(home)._plan_path("shared")
    plan = json.loads(file.read_text())
    plan["share_scope"] = "PROMOTED_PURE_TEXT"
    file.write_text(json.dumps(plan))
    with pytest.raises(ValueError, match="unverified local plan"):
        opb.run(':fastbatch run shared 10 "fake"')


def test_retiring_shared_habit_closes_sharing_and_prevents_reactivation(shared):
    st, a, b, opa, opb, p, home = shared
    _approve(shared)
    retired = json.loads(opa.run(":fastbatch retire shared"))
    assert retired["stage"] == "RETIRED"
    plan = ProceduralBatch(home).plan("shared")
    assert "share_sha256" not in plan and "share_scope" not in plan
    with pytest.raises(PermissionError):
        opb.run(':fastbatch run shared 20 "again"')
    with pytest.raises(ValueError, match="retired"):
        opa.run(f":fastbatch activate shared {p['sha256']}")
