"""Fail-closed independent audit of a BP1 QAD V2 original native Actions ZIP.

Pass proves byte/source-bound evidence, NOT learned utility or phone readiness.
Only stdlib; no model weights or heldout answer text in the output.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path, PurePosixPath
import zipfile

DATASET_SHA = "7238a0220255cbccbcf1f9ccfad8dc03febfc37f7bc1d9d0aa645618f006508c"
TRAIN_SHA = "9f356917911983e887f80aaadd8b58365fe43ecbf6632bb5e9e0a1aa8628ff86"
MASTER_SHA = "1d90518482c4ec204bebb4820bbaee4f8a38c5a6df72256f86bcd21fe52ad079"
BASE_SHA = "3d10b6ab8fc91a919534b9558e266255aca0bbc7f6d015963599aa9e74e05b1d"
RUNNER_SHA = "79e312188dc1d75c28201771f106e91de470b5cebdd838d31bb4db25eecf5d39"
GATES = {"STEP2": "UTILITY_FAIL", "B3_L1": "FAIL", "Body_JEPA": "UNAVAILABLE", "jepa_weight": 0, "V13": "INCOMPLETE"}
EXITS = ("BUDGET", "DATASET_FETCH", "DEPS", "GGUF_SOURCE", "MASTER_FETCH", "TRAIN", "V2_MODEL", "V2_HELDOUT", "V2")


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def check(ok, message):
    if not ok:
        raise ValueError(message)


def safe_zip(path):
    z = zipfile.ZipFile(path)
    names = z.namelist()
    check(z.testzip() is None, "ZIP CRC failure")
    check(len(names) == len(set(names)), "duplicate ZIP members")
    for info in z.infolist():
        p = PurePosixPath(info.filename)
        check(not p.is_absolute() and ".." not in p.parts and "\\" not in info.filename, "unsafe ZIP path")
        check(info.file_size <= 20_000_000, "oversized raw ZIP member")
        check(not info.filename.lower().endswith((".gguf", ".safetensors", ".pt", ".pth")), "private weights in raw ZIP")
    return z


def jsonl(raw):
    return [json.loads(line) for line in raw.decode("utf-8").splitlines() if line.strip()]


def audit(native_zip, dataset_zip, expected_head, expected_zip_sha):
    original = Path(native_zip).read_bytes()
    check(sha(original) == expected_zip_sha, "original ZIP SHA mismatch")
    with safe_zip(native_zip) as z, safe_zip(dataset_zip) as d:
        ds = d.read("bp1-output/heldout_paired.jsonl")
        check(sha(ds) == DATASET_SHA, "heldout source bytes drift")
        ref_rows = jsonl(ds)
        refs = {(r["row_id"], r["arm"]): r for r in ref_rows}
        check(len(ref_rows) == len(refs) == 22, "heldout duplicates or missing rows")
        check(len({r for r, a in refs}) == 11 and {a for r, a in refs} == {"no_offer", "offer"}, "heldout cohort drift")
        check(z.read("HEAD.txt").decode().strip() == expected_head, "native source HEAD drift")
        for key in EXITS:
            check(z.read(key + "_EXIT.txt").decode().strip() == "0", key + " exit nonzero")
        proof_raw = z.read("BP1_QAD_TRAIN_PROOF.json")
        proof = json.loads(proof_raw)
        check(proof.get("train_sha256") == TRAIN_SHA and proof.get("train_rows") == 25, "train cohort drift")
        check(proof.get("native_training_executed") is True and proof.get("heldout_files_opened") is False, "train isolation drift")
        check(proof.get("production_weight_authority") == 0 and proof.get("model_utility_proven") is False, "train authority drift")
        check(proof.get("config", {}).get("jepa_weight") == 0 and proof.get("config", {}).get("max_steps") == 2, "train config drift")
        check(proof.get("master", {}).get("master_sha256") == MASTER_SHA, "FP32 master drift")
        check(proof.get("adapter", {}).get("lora_b_nonzero", 0) > 0, "no adapter delta")
        hist = proof.get("metrics", {}).get("loss_history")
        check(isinstance(hist, list) and len(hist) == 2 and all(math.isfinite(x["ce"]) for x in hist), "invalid optimizer history")
        binding_raw = z.read("V2_BINDING.json")
        check(binding_raw == z.read("RUN_BINDING.json"), "binding bytes differ")
        binding = json.loads(binding_raw)
        check(binding.get("dataset_sha256") == DATASET_SHA and binding.get("train_sha256") == TRAIN_SHA, "V2 cohort drift")
        check(binding.get("base_master_sha256") == MASTER_SHA and binding.get("base_gguf_sha256") == BASE_SHA and binding.get("runner_sha256") == RUNNER_SHA, "native model/runner drift")
        check(binding.get("train_proof_sha256") == sha(proof_raw), "train proof bytes unbound")
        check(binding.get("adapter_gguf_sha256") == proof.get("adapter", {}).get("gguf_sha256"), "adapter SHA mismatch")
        check(binding.get("scales") == {"base": 0.0, "candidate": 1.0}, "LoRA scales drift")
        check(binding.get("seed") == 13 and binding.get("temperature") == 0 and binding.get("production_weight_authority") == 0, "decoding/authority drift")
        check(all(binding.get("gates", {}).get(k) == v for k, v in GATES.items()), "negative gate drift")
        predictions_raw = z.read("predictions.jsonl")
        check(predictions_raw == z.read("V2_PARTIAL_OR_FINAL_PREDICTIONS.jsonl"), "raw prediction copy mismatch")
        manifest = json.loads(z.read("FINAL_MANIFEST.json"))
        scores = json.loads(z.read("V2_SCORES.json"))
        check(manifest.get("predictions_sha256") == sha(predictions_raw) == scores.get("predictions_sha256"), "prediction digest drift")
        check(manifest.get("binding_sha256") == sha(binding_raw) == scores.get("binding_sha256"), "binding digest drift")
        check(manifest.get("rows") == 44 and manifest.get("source_pairs") == 11, "collection size drift")
        check(manifest.get("heldout_targets_sent_to_model") is False and manifest.get("model_utility_proven") is False, "collection claim drift")
        check(scores.get("model_utility_proven") is False, "score claims utility")
        check(all(manifest.get("gates", {}).get(k) == v and scores.get("gates", {}).get(k) == v for k, v in GATES.items()), "negative gates promoted")
        predictions = jsonl(predictions_raw)
        check(len(predictions) == 44, "prediction count drift")
        seen = set()
        for p in predictions:
            key = (p["row_id"], p["arm"])
            check(p["model"] in ("base", "candidate") and key in refs, "unregistered prediction")
            check((p["model"], *key) not in seen, "duplicate prediction")
            seen.add((p["model"], *key))
            check(p["source_sha256"] == refs[key]["source_sha256"], "source identity drift")
            check(p["prompt_sha256"] == sha(refs[key]["prompt"].encode()), "prompt identity drift")
            check(isinstance(p["response"], str) and len(p["response"]) <= 8192, "invalid response")
        check(seen == {(m, rid, arm) for m in ("base", "candidate") for rid, arm in refs}, "incomplete paired cohort")
        check(len(z.read("V2_SERVER_RAW.log")) > 0, "missing native server log")
        return {"status": "RAW_BINDING_PASS_NOT_UTILITY", "native_zip_sha256": sha(original),
                "source_head": expected_head, "dataset_sha256": DATASET_SHA,
                "train_proof_sha256": sha(proof_raw), "binding_sha256": sha(binding_raw),
                "predictions_sha256": sha(predictions_raw), "responses": 44,
                "source_pairs": 11, "candidate_utility_proven": False,
                "redmi_measured": False, "gates": GATES}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--native-zip", required=True)
    parser.add_argument("--dataset-zip", required=True)
    parser.add_argument("--expected-head", required=True)
    parser.add_argument("--expected-zip-sha", required=True)
    args = parser.parse_args()
    print(json.dumps(audit(args.native_zip, args.dataset_zip, args.expected_head, args.expected_zip_sha), sort_keys=True))


if __name__ == "__main__":
    main()
