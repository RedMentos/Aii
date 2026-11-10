import hashlib
import json
import sqlite3

import pytest
from v13.agi.body_dataset_store import compile_from_store, verify_store_sources


def make_store(tmp_path, n=150):
    home = tmp_path/"home"
    (home/"data"/"db").mkdir(parents=True)
    (home/"data"/"blobs").mkdir()
    con = sqlite3.connect(home/"data"/"db"/"brain.sqlite3")
    con.execute("CREATE TABLE sources(id TEXT PRIMARY KEY, hash TEXT, deleted INTEGER)")
    inp = tmp_path/"reviewed.jsonl"
    with inp.open("w") as f:
        for i in range(n):
            content = ("source text "+str(i)).encode()
            digest = hashlib.sha256(content).hexdigest()
            (home/"data"/"blobs"/digest).write_bytes(content)
            con.execute("INSERT INTO sources VALUES (?,?,0)", (f"src_{i}", digest))
            for role in ("B1_DETAIL", "B2_GIST"):
                f.write(json.dumps({"role":role, "source_id":f"src_{i}",
                                    "source_sha256":digest, "prompt":f"prompt {i}",
                                    "target":f"target {i}", "reviewed":True,
                                    "permission":"TRAINING_APPROVED"})+"\n")
    con.commit()
    con.close()
    return inp, home


def test_store_verified_compilation(tmp_path):
    inp, home = make_store(tmp_path)
    result = compile_from_store(inp, home, tmp_path/"output")
    assert result["source_verification"]["verified_sources"] == 150
    assert result["dataset"]["rows"] == 300
    assert (tmp_path/"output"/"manifest.json").is_file()


def test_store_deleted_source_rejected_before_output(tmp_path):
    inp, home = make_store(tmp_path)
    con = sqlite3.connect(home/"data"/"db"/"brain.sqlite3")
    con.execute("UPDATE sources SET deleted=1 WHERE id='src_0'")
    con.commit()
    con.close()
    with pytest.raises(ValueError, match="deleted"):
        compile_from_store(inp, home, tmp_path/"output")
    assert not (tmp_path/"output").exists()


def test_store_corrupt_blob_rejected(tmp_path):
    inp, home = make_store(tmp_path)
    digest = json.loads(inp.read_text().splitlines()[0])["source_sha256"]
    (home/"data"/"blobs"/digest).write_bytes(b"wrong")
    with pytest.raises(ValueError, match="hash mismatch"):
        verify_store_sources(inp, home)
