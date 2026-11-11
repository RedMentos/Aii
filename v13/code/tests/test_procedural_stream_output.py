"""Compiled V13 fast-output: bounded UTF-8 streaming, mini-checkpoints and restart.

The stream reproduces committed bytes with no LLM calls, never inventing new
text or allowing model callers to access an unrestricted path.
"""
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from v13.operator import Operator
from v13.procedural_batch import ProceduralBatch


def _operator(tmp_path):
    # Manual (non-learned) procedures need no Store, but the normal operator
    # still has the same read-only parameter shape as the actual Runtime.
    return Operator(SimpleNamespace(home=tmp_path, store=None))


def _activate(op, name, template):
    proposal = json.loads(op.run(f":fastbatch propose {name} '{template}'"))
    op.run(f":fastbatch activate {name} {proposal['sha256'][:12]}")
    return proposal


def test_read_utf8_cursor_across_restart_and_generator_snapshot(tmp_path):
    op = _operator(tmp_path)
    _activate(op, "utf8", "🧠 {i}: ää Ω")
    first = json.loads(op.run(":fastbatch run utf8 1200 --rows=150"))
    assert first["status"] == "PAUSED" and first["rows"] == 150
    op = _operator(tmp_path)  # fresh operator and procedure instance
    done = json.loads(op.run(":fastbatch run utf8 1200"))
    assert done["status"] == "DONE"
    original = Path(done["output_path"]).read_text(encoding="utf-8")
    reader = ProceduralBatch(tmp_path)
    assert "".join(reader.iter_output("utf8", 1200, chunk_bytes=7)) == original
    assert hashlib.sha256(original.encode()).hexdigest() == done["sha256"]
    cursor = 0
    chunks = []
    for _ in range(30000):
        result = json.loads(op.run(f":fastbatch read utf8 1200 --cursor={cursor} --bytes=19"))
        assert result["model_calls"] == 0
        assert result["cursor_bytes"] == cursor
        assert result["next_cursor_bytes"] >= cursor
        assert len(result["text"].encode("utf-8")) <= 19
        chunks.append(result["text"])
        cursor = result["next_cursor_bytes"]
        if not result["more_committed"]:
            break
    assert cursor == done["bytes"]
    assert "".join(chunks) == original
    assert result["needs_run"] is False
    assert result["status"] == "DONE"


def test_paused_output_read_never_advances_writer(tmp_path):
    op = _operator(tmp_path)
    _activate(op, "paused", "Task {i}: done")
    with pytest.raises(FileNotFoundError, match="run procedure"):
        op.run(":fastbatch read paused 200 --cursor=0")
    p = json.loads(op.run(":fastbatch run paused 200 --rows=3"))
    read = json.loads(op.run(":fastbatch read paused 200 --bytes=4096"))
    assert read["text"] == "Task 1: done\nTask 2: done\nTask 3: done\n"
    assert read["needs_run"] is True and read["more_committed"] is False
    assert read["committed_bytes"] == p["bytes"]
    assert read["next_cursor_bytes"] == p["bytes"]
    assert json.loads(op.run(":fastbatch status paused"))["stage"] == "ACTIVE"
    assert "".join(ProceduralBatch(tmp_path).iter_output("paused", 200)) == read["text"]


def test_fail_closed_invalid_utf8_cursor_or_bounds(tmp_path):
    op = _operator(tmp_path)
    _activate(op, "unicode", "Ä {i}")
    state = json.loads(op.run(":fastbatch run unicode 8"))
    for cursor in (-1, state["bytes"] + 1, 1):
        with pytest.raises(ValueError):
            op.run(f":fastbatch read unicode 8 --cursor={cursor}")
    for n in (0, 1, 3, 65537):
        with pytest.raises(ValueError):
            op.run(f":fastbatch read unicode 8 --bytes={n}")
    with pytest.raises(ValueError):
        op.run(":fastbatch read unicode 8 --bytes=foo")
    with pytest.raises(ValueError):
        op.run(":fastbatch read unicode 8 --bad=x")
    with pytest.raises(ValueError):
        op.run(":fastbatch read unicode 8 --cursor=1 --cursor=2")
    with pytest.raises(ValueError):
        op.run(":fastbatch read unicode 8 --cursor=2 --bytes=12 --bad=5")
    for n in (0, 3, 65537):
        with pytest.raises(ValueError):
            list(ProceduralBatch(tmp_path).iter_output("unicode", 8, chunk_bytes=n))


def test_read_refuses_corrupted_committed_prefix_even_when_cursored(tmp_path):
    op = _operator(tmp_path)
    _activate(op, "protect", "Task {i}")
    done = json.loads(op.run(":fastbatch run protect 150"))
    path = Path(done["output_path"])
    before = path.read_bytes()
    path.write_bytes(b"X" + before[1:])
    with pytest.raises(ValueError, match="hash mismatch"):
        op.run(":fastbatch read protect 150 --cursor=20")
    with pytest.raises(ValueError, match="hash mismatch"):
        list(ProceduralBatch(tmp_path).iter_output("protect", 150))
    assert path.read_bytes() == b"X" + before[1:]


def test_read_disallows_retired_plans_without_erasing_checkpoint(tmp_path):
    op = _operator(tmp_path)
    _activate(op, "retired", "Task {i}")
    done = json.loads(op.run(":fastbatch run retired 20"))
    op.run(":fastbatch retire retired")
    with pytest.raises(PermissionError):
        op.run(":fastbatch read retired 20")
    with pytest.raises(PermissionError):
        list(ProceduralBatch(tmp_path).iter_output("retired", 20))
    assert Path(done["output_path"]).is_file()


def test_uncommitted_tail_trimmed_before_visible_read(tmp_path):
    op = _operator(tmp_path)
    _activate(op, "crashed", "Row {i}")
    result = json.loads(op.run(":fastbatch run crashed 30 --rows=5"))
    path = Path(result["output_path"])
    with path.open("ab") as f:
        f.write(b"UNCOMMITTED-TEXT")
    read = json.loads(op.run(":fastbatch read crashed 30"))
    assert read["text"].endswith("Row 5\n")
    assert "UNCOMMITTED" not in read["text"]
    assert path.stat().st_size == result["bytes"]


def test_stream_decent_throughput_without_ooming_small_window(tmp_path):
    op = _operator(tmp_path)
    _activate(op, "manyrows", "repeat {i}")
    done = json.loads(op.run(":fastbatch run manyrows 80000"))
    assert done["status"] == "DONE" and done["model_calls"] == 0
    result = ProceduralBatch(tmp_path)
    hasher = hashlib.sha256()
    count, max_seen = 0, 0
    for part in result.iter_output("manyrows", 80000, chunk_bytes=16384):
        encoded = part.encode("utf-8")
        max_seen = max(max_seen, len(encoded))
        count += part.count("\n")
        hasher.update(encoded)
    assert count == 80000
    assert max_seen <= 16388  # UTF-8 boundary max overhead, never full file
    assert hasher.hexdigest() == done["sha256"]


def test_learned_stream_rechecks_revoked_final_source_between_chunks(tmp_path):
    """A paused live stream must not keep exposing a revoked learned habit."""
    from v13.store import Store
    for folder in ("data", "data/db", "data/blobs"):
        (tmp_path / folder).mkdir(parents=True, exist_ok=True)
    store = Store(tmp_path)
    try:
        session = store.new_session()
        event = store.event(session, "Number the outputs")
        mid = store.message(session, event["event_id"], "assistant",
                            "".join(f"row {i}: prior\n" for i in range(1, 7)))
        store.finish_message(mid, "FINAL", {})
        runtime = SimpleNamespace(store=store, session=session, home=tmp_path)
        op = Operator(runtime)
        proposal = json.loads(op.run(":fastbatch discover streamhabit"))
        op.run(f":fastbatch activate streamhabit {proposal['sha256'][:12]}")
        checkpoint = json.loads(op.run(":fastbatch run streamhabit 100 --rows=50"))
        assert checkpoint["status"] == "PAUSED"
        worker = ProceduralBatch(tmp_path, store=store, session=session)
        output = worker.iter_output("streamhabit", 100, chunk_bytes=16)
        assert next(output).startswith("row 1")
        with store.tx() as tx:
            tx.execute("UPDATE sources SET deleted=1 WHERE id=?",
                       (event["source_ref"]["source_id"],))
        with pytest.raises(ValueError, match="no longer FINAL"):
            next(output)
        # A failed reader cannot truncate the already durable output.
        assert Path(checkpoint["output_path"]).read_text().count("\n") == 50
        with pytest.raises(ValueError, match="no longer FINAL"):
            op.run(":fastbatch read streamhabit 100")
    finally:
        store.close()
