import hashlib
import json
import pytest
from v13.agi.body_dataset import compile_dataset


def fixture(tmp_path, n=150):
    p = tmp_path / "reviewed.jsonl"
    with p.open("w") as f:
        for i in range(n):
            for role in ("B1_DETAIL", "B2_GIST"):
                row = {"role": role, "source_id": f"src_{i}",
                       "source_sha256": hashlib.sha256(str(i).encode()).hexdigest(),
                       "prompt": f"input {i}", "target": f"answer {i}",
                       "reviewed": True, "permission": "TRAINING_APPROVED"}
                f.write(json.dumps(row) + "\n")
    return p


def test_source_disjoint_and_deterministic(tmp_path):
    p = fixture(tmp_path)
    a = compile_dataset(p, tmp_path/"a")
    b = compile_dataset(p, tmp_path/"b")
    assert a == b
    for role in ("b1_detail", "b2_gist"):
        tr = [json.loads(x) for x in (tmp_path/"a"/f"{role}_train.jsonl").read_text().splitlines()]
        ho = [json.loads(x) for x in (tmp_path/"a"/f"{role}_holdout.jsonl").read_text().splitlines()]
        assert tr and ho
        assert {r["source_id"] for r in tr}.isdisjoint({r["source_id"] for r in ho})
        assert (tmp_path/"a"/f"{role}_train.jsonl").read_bytes() == (tmp_path/"b"/f"{role}_train.jsonl").read_bytes()


def test_unreviewed_fails_before_output(tmp_path):
    p = fixture(tmp_path)
    lines = p.read_text().splitlines()
    row = json.loads(lines[0])
    row["reviewed"] = False
    lines[0] = json.dumps(row)
    p.write_text("\n".join(lines)+"\n")
    with pytest.raises(ValueError, match="invalid reviewed"):
        compile_dataset(p, tmp_path/"out")
    assert not (tmp_path/"out").exists()


def test_conflicting_source_hash_rejected(tmp_path):
    p = fixture(tmp_path)
    lines = p.read_text().splitlines()
    row = json.loads(lines[1])
    row["source_sha256"] = "0"*64
    lines[1] = json.dumps(row)
    p.write_text("\n".join(lines)+"\n")
    with pytest.raises(ValueError, match="changed content hash"):
        compile_dataset(p, tmp_path/"out")


def test_empty_holdout_fails_closed(tmp_path):
    p = fixture(tmp_path, n=1)
    with pytest.raises(ValueError, match="insufficient"):
        compile_dataset(p, tmp_path/"out")


def test_existing_output_not_overwritten(tmp_path):
    p = fixture(tmp_path)
    out = tmp_path/"out"
    out.mkdir()
    (out/"keep").write_text("old")
    with pytest.raises(ValueError, match="empty"):
        compile_dataset(p, out)
    assert (out/"keep").read_text() == "old"
