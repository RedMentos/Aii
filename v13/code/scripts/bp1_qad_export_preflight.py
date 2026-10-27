#!/usr/bin/env python3
"""Pinned b10964 GGUF LFM2 LoRA export preflight; synthetic tensors, no weights."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import struct
import subprocess

SOURCE_COMMIT = "b29c606e28a01b1bc8c1351026a0fa6e616bf6c4"
SCHEMA = "V13_BP1_QAD_LFM2_GGUF_EXPORT_PREFLIGHT_V1"
HF_MODULES = ("model.layers.0.self_attn.v_proj", "model.layers.0.self_attn.out_proj")
GATES = {"STEP2": "UTILITY_FAIL", "B3_L1": "FAIL", "Body_JEPA": "UNAVAILABLE",
         "jepa_weight": 0, "Redmi_measured": False, "V13": "INCOMPLETE"}


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def verify_checkout(checkout):
    checkout = Path(checkout).resolve()
    try:
        commit = subprocess.check_output(
            ["git", "-C", str(checkout), "rev-parse", "HEAD"],
            text=True, timeout=15, stderr=subprocess.DEVNULL).strip()
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        raise ValueError("unregistered gguf-py source checkout") from None
    if commit != SOURCE_COMMIT:
        raise ValueError("unregistered gguf-py source revision")
    if not (checkout / "gguf-py" / "gguf" / "constants.py").is_file():
        raise ValueError("pinned gguf-py source missing")
    return checkout


def resolve_arch(gguf):
    choices = [arch for arch, name in gguf.MODEL_ARCH_NAMES.items() if name == "lfm2"]
    if len(choices) != 1:
        raise ValueError("pinned gguf-py LFM2 architecture absent/ambiguous")
    return choices[0]


def map_modules(gguf):
    tm = gguf.get_tensor_name_map(resolve_arch(gguf), 16)
    names = [tm.get_name(name) for name in HF_MODULES]
    if any(not isinstance(name, str) or not name.startswith("blk.0.") for name in names):
        raise ValueError("LFM2 official HF attention LoRA tensor mapping missing")
    if len(set(names)) != len(names):
        raise ValueError("LFM2 LoRA tensor names collide")
    return names


def run(checkout, out):
    root = verify_checkout(checkout)
    import gguf
    import numpy as np
    installed = Path(gguf.__file__).resolve()
    try:
        installed.relative_to(root / "gguf-py")
    except ValueError:
        raise ValueError("gguf imported from unregistered installation") from None
    names = map_modules(gguf)
    output = Path(out)
    output.mkdir(parents=True, exist_ok=False)
    dest = output / "SYNTHETIC_LFM2_LORA.gguf"
    w = gguf.GGUFWriter(str(dest), "lfm2")
    w.add_string(gguf.Keys.General.TYPE, gguf.GGUFType.ADAPTER)
    w.add_string(gguf.Keys.Adapter.TYPE, "lora")
    w.add_float32(gguf.Keys.Adapter.LORA_ALPHA, 4.0)
    for name in names:
        w.add_tensor(name + ".weight.lora_a", np.ones((2, 8), dtype=np.float32))
        w.add_tensor(name + ".weight.lora_b", np.ones((8, 2), dtype=np.float32))
    w.write_header_to_file()
    w.write_kv_data_to_file()
    w.write_tensors_to_file()
    w.close()
    with dest.open("rb") as f:
        header = f.read(24)
    if len(header) != 24 or header[:4] != b"GGUF":
        raise ValueError("GGUF header missing")
    version, count, _ = struct.unpack("<IQQ", header[4:])
    if version != 3 or count != 4:
        raise ValueError("GGUF v3 tensor count mismatch")
    reader = gguf.GGUFReader(str(dest))
    observed = sorted(t.name for t in reader.tensors)
    expected = sorted(n + ".weight.lora_" + suffix for n in names for suffix in ("a", "b"))
    if observed != expected:
        raise ValueError("GGUF readback tensor names mismatch")
    if not all(key in reader.fields for key in ("general.architecture", "general.type",
                                                "adapter.type", "adapter.lora.alpha")):
        raise ValueError("GGUF adapter metadata missing")
    proof = {"schema": SCHEMA, "source_commit": SOURCE_COMMIT,
             "gguf_py_source": str(installed.relative_to(root)),
             "numpy_version": np.__version__, "module_names": list(HF_MODULES),
             "gguf_tensor_names": observed, "synthetic_gguf_sha256": sha(dest),
             "synthetic_gguf_bytes": dest.stat().st_size,
             "synthetic_tensors": count, "training_executed": False,
             "model_utility_proven": False, "redmi_measured": False, "gates": GATES}
    with (output / "PREFLIGHT.json").open("xb") as f:
        f.write((json.dumps(proof, indent=2, sort_keys=True) + "\n").encode())
        f.flush()
        os.fsync(f.fileno())
    return proof


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--source-checkout", required=True)
    p.add_argument("--out", required=True)
    args = p.parse_args()
    proof = run(args.source_checkout, args.out)
    print(json.dumps({"source_commit": proof["source_commit"],
                      "synthetic_tensors": proof["synthetic_tensors"],
                      "training_executed": False}, sort_keys=True))


if __name__ == "__main__":
    main()
