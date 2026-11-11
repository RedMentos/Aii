"""Same-job concurrent write/read must not corrupt V13 mini-checkpoints."""
import fcntl
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from v13.operator import Operator
from v13.procedural_batch import ProceduralBatch


def approved(tmp_path, name):
    op = Operator(SimpleNamespace(home=tmp_path, store=None))
    proposal = json.loads(op.run(f":fastbatch propose {name} 'row {{i}}: ok'"))
    op.run(f":fastbatch activate {name} {proposal['sha256']}")
    return op, ProceduralBatch(tmp_path)


def locked_job_path(batch, name, count):
    state_file, _, _ = batch._job_files(batch.plan(name), count, "")
    return state_file.with_suffix(".lock")


def test_busy_job_refuses_concurrent_writer_and_reader_without_mutation(tmp_path):
    op, batch = approved(tmp_path, "busy")
    saved = json.loads(op.run(":fastbatch run busy 200 --rows=7"))
    lock = locked_job_path(batch, "busy", 200)
    with lock.open("rb") as fd:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with pytest.raises(RuntimeError, match="job busy"):
            op.run(":fastbatch run busy 200")
        with pytest.raises(RuntimeError, match="job busy"):
            op.run(":fastbatch read busy 200")
        with pytest.raises(RuntimeError, match="job busy"):
            op.run(":fastbatch peek busy 200")
        with pytest.raises(RuntimeError, match="job busy"):
            list(batch.iter_output("busy", 200))
        fcntl.flock(fd, fcntl.LOCK_UN)
    assert Path(saved["output_path"]).read_text().count("\n") == 7
    resumed = json.loads(op.run(":fastbatch run busy 200"))
    assert resumed["status"] == "DONE"
    assert Path(saved["output_path"]).read_text().count("\n") == 200


def test_lock_is_per_job_not_global_other_jobs_keep_working(tmp_path):
    op, batch = approved(tmp_path, "unlocked")
    state_file, _, _ = batch._job_files(batch.plan("unlocked"), 400, "")
    lock = state_file.with_suffix(".lock")
    lock.touch(mode=0o600)
    with lock.open("rb") as fd:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with pytest.raises(RuntimeError, match="job busy"):
            op.run(":fastbatch run unlocked 400")
        result = json.loads(op.run(":fastbatch run unlocked 401"))
        assert result["status"] == "DONE" and result["total_rows"] == 401
        fcntl.flock(fd, fcntl.LOCK_UN)
    assert json.loads(op.run(":fastbatch run unlocked 400"))["status"] == "DONE"


def test_job_lock_symlink_and_hardlink_fail_closed(tmp_path):
    op, batch = approved(tmp_path, "protect")
    link = locked_job_path(batch, "protect", 120)
    unrelated = tmp_path / "unrelated.txt"
    unrelated.write_text("MUST_NOT_TOUCH")
    link.symlink_to(unrelated)
    with pytest.raises(ValueError, match="symbolic links"):
        op.run(":fastbatch run protect 120")
    assert unrelated.read_text() == "MUST_NOT_TOUCH"
    link.unlink()
    link.hardlink_to(unrelated)
    with pytest.raises(ValueError, match="unsafe fastbatch job lock"):
        op.run(":fastbatch run protect 120")
    assert unrelated.read_text() == "MUST_NOT_TOUCH"


def test_many_checkpoint_restarts_under_lock_preserve_exact_once_output(tmp_path):
    op, batch = approved(tmp_path, "resume")
    for _ in range(13):
        done = json.loads(op.run(":fastbatch run resume 600 --rows=49"))
        op = Operator(SimpleNamespace(home=tmp_path, store=None))
    assert done["status"] == "DONE" and done["rows"] == 600
    contents = Path(done["output_path"]).read_text()
    assert contents.startswith("row 1: ok\n")
    assert contents.endswith("row 600: ok\n")
    assert contents.count("\n") == 600
    assert json.loads(op.run(":fastbatch read resume 600"))["committed_bytes"] == done["bytes"]
