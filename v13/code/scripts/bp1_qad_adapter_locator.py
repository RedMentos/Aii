"""Locate exact ephemeral BP1 QAD trained adapter without moving or publishing weights.

This is a same-job read-only bridge from frozen trainer output to V2 evaluator.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re

TRAIN_SHA = "9f356917911983e887f80aaadd8b58365fe43ecbf6632bb5e9e0a1aa8628ff86"
GATES = {"STEP2": "UTILITY_FAIL", "B3_L1": "FAIL", "Body_JEPA": "UNAVAILABLE",
         "jepa_weight": 0, "V13": "INCOMPLETE"}


def check(ok, message):
    if not ok:
        raise ValueError(message)


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def unique(pairs):
    out = {}
    for key, value in pairs:
        check(key not in out, "duplicate proof JSON key")
        out[key] = value
    return out


def locate(trainer_work, proof_path):
    root = Path(trainer_work)
    proof_file = Path(proof_path)
    check(root.is_dir() and not root.is_symlink(), "trainer work root missing or symlink")
    check(proof_file.is_file() and not proof_file.is_symlink(), "train proof missing or symlink")
    proof = json.loads(proof_file.read_text(), object_pairs_hook=unique)
    check(isinstance(proof, dict) and proof.get("mode") == "train" and
          proof.get("status") == "TRAINED_SHADOW_ADAPTER_NOT_DEPLOYED" and
          proof.get("train_rows") == 25 and proof.get("train_sha256") == TRAIN_SHA,
          "original train proof mismatch")
    check(proof.get("native_training_executed") is True and
          proof.get("heldout_files_opened") is False and
          proof.get("production_weight_authority") == 0 and
          proof.get("model_utility_proven") is False and
          proof.get("gates") == GATES, "train isolation/authority drift")
    adapter_info = proof.get("adapter")
    check(isinstance(adapter_info, dict), "adapter proof missing")
    candidates = list(root.glob("*/adapter.gguf"))
    check(len(candidates) == 1, "require exactly one trained adapter")
    adapter = candidates[0]
    parent = adapter.parent
    peft = parent / "adapter_model.safetensors"
    check(re.fullmatch(r"[0-9a-f]{24}", parent.name) is not None, "trainer digest directory drift")
    check(not parent.is_symlink() and not adapter.is_symlink() and not peft.is_symlink() and
          adapter.is_file() and peft.is_file(), "adapter/PEFT path invalid")
    check(adapter.resolve().parent.parent == root.resolve() and
          peft.resolve().parent == adapter.resolve().parent, "adapter escaped owned trainer work")
    check(adapter.stat().st_size == adapter_info.get("gguf_bytes"), "adapter size mismatch")
    check(sha(adapter) == adapter_info.get("gguf_sha256"), "GGUF adapter SHA mismatch")
    check(sha(peft) == adapter_info.get("peft_sha256"), "PEFT adapter SHA mismatch")
    check(adapter_info.get("lora_b_nonzero", 0) > 0 and
          adapter_info.get("gguf_tensors") == 44, "adapter update proof mismatch")
    return adapter.resolve(), adapter_info


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--trainer-work", required=True)
    parser.add_argument("--proof", required=True)
    parser.add_argument("--path-file", required=True)
    args = parser.parse_args()
    adapter, info = locate(args.trainer_work, args.proof)
    with Path(args.path_file).open("xb") as stream:
        stream.write((str(adapter) + "\n").encode())
        stream.flush()
        os.fsync(stream.fileno())
    print(json.dumps({"status": "VERIFIED_EPHEMERAL_ADAPTER_NOT_DEPLOYED",
                      "gguf_sha256": info["gguf_sha256"],
                      "peft_sha256": info["peft_sha256"],
                      "production_weight_authority": 0}, sort_keys=True))


if __name__ == "__main__":
    main()
