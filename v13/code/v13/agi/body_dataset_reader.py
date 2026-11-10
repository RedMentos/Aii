"""Hash-checked, read-only B1/B2 dataset loading; never grants training authority."""
import hashlib
import json
from pathlib import Path
from .body_dataset import ROLES, MAX_LINE, MAX_ROWS, _validate

def load_role_dataset(directory, role, *, max_rows=MAX_ROWS):
    """Validate every partition before yielding one role's train/holdout rows.

    Review flags in the dataset are NOT authenticated operator approval.
    Existing AG6 human/age/retention gates remain the trainer's responsibility.
    """
    if role not in ROLES or type(max_rows) is not int or not 1 <= max_rows <= MAX_ROWS:
        raise ValueError("invalid role or row cap")
    root = Path(directory)
    if root.is_symlink() or not root.is_dir():
        raise ValueError("invalid dataset directory")
    manifest_file = root / "manifest.json"
    if manifest_file.is_symlink() or not manifest_file.is_file() or manifest_file.stat().st_size > 16384:
        raise ValueError("invalid manifest")
    manifest = json.loads(manifest_file.read_bytes())
    names = {r.lower()+"_"+part+".jsonl" for r in ROLES for part in ("train", "holdout")}
    if (type(manifest) is not dict
            or set(manifest) != {"schema", "input_sha256", "holdout_percent", "rows", "files"}
            or manifest["schema"] != "v13-reviewed-body-dataset-v1"
            or type(manifest["rows"]) is not int or not 1 <= manifest["rows"] <= MAX_ROWS
            or type(manifest["files"]) is not dict or set(manifest["files"]) != names):
        raise ValueError("invalid manifest schema")
    percent = manifest["holdout_percent"]
    if type(percent) is not int or not 1 <= percent <= 49:
        raise ValueError("invalid split percent")
    h = manifest["input_sha256"]
    if type(h) is not str or len(h) != 64 or any(c not in "0123456789abcdef" for c in h):
        raise ValueError("invalid source digest")
    result = {}
    source_hashes, source_splits = {}, {}
    total = 0
    for r in ROLES:
        result[r] = {}
        for part in ("train", "holdout"):
            name = r.lower()+"_"+part+".jsonl"
            info, path = manifest["files"][name], root / name
            if (type(info) is not dict or set(info) != {"sha256", "rows", "sources"}
                    or path.is_symlink() or not path.is_file()):
                raise ValueError("invalid partition metadata")
            h = info["sha256"]
            if type(h) is not str or len(h) != 64 or any(c not in "0123456789abcdef" for c in h):
                raise ValueError("invalid partition digest")
            if (type(info["rows"]) is not int or type(info["sources"]) is not int
                    or not 1 <= info["rows"] <= MAX_ROWS
                    or not 1 <= info["sources"] <= info["rows"]):
                raise ValueError("invalid partition counts")
            digest, rows, sources = hashlib.sha256(), [], set()
            with path.open("rb") as stream:
                for line in stream:
                    digest.update(line)
                    if len(line) > MAX_LINE or not line.endswith(b"\n") or len(rows) >= max_rows:
                        raise ValueError("invalid partition row")
                    item = _validate(json.loads(line))
                    if item["role"] != r:
                        raise ValueError("cross-role partition")
                    sid, sh = item["source_id"], item["source_sha256"]
                    if source_hashes.setdefault(sid, sh) != sh:
                        raise ValueError("source ID changed hash")
                    if source_splits.setdefault((sid, sh), part) != part:
                        raise ValueError("train/holdout source leakage")
                    expected = "holdout" if int(sh[:16], 16) % 100 < percent else "train"
                    if expected != part:
                        raise ValueError("source split mismatch")
                    sources.add((sid, sh))
                    rows.append(item)
            if (len(rows) != info["rows"] or len(sources) != info["sources"]
                    or digest.hexdigest() != h):
                raise ValueError("partition hash/count mismatch")
            total += len(rows)
            result[r][part] = tuple(rows)
    if total != manifest["rows"]:
        raise ValueError("total row count mismatch")
    return result[role]["train"], result[role]["holdout"]
