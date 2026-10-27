#!/usr/bin/env python3
"""BP1 QAD Q4 base-only 22-row source-disjoint native heldout baseline."""
import argparse
from contextlib import contextmanager
import json
import os
from pathlib import Path

from scripts import bp1_native_collect as C
from scripts import bp1_paired_score as S
from scripts import bp1_qad_native_smoke as N
from scripts import bp1_qad_lora_eval as V2

SCHEMA = "V13_BP1_QAD_BASE_HELDOUT_BINDING_V1"
COLLECT_SCHEMA = "V13_BP1_QAD_BASE_HELDOUT_COLLECTION_V1"
SCORE_SCHEMA = "V13_BP1_QAD_BASE_HELDOUT_SCORE_V1"
GATES = S.GATES


def validate_binding(binding, dataset_sha):
    if not isinstance(binding, dict) or set(binding) != {
        "schema", "dataset_sha256", "model_sha256", "runner_sha256",
        "seed", "temperature", "decoding", "production_weight_authority", "gates",
    }:
        raise ValueError("invalid QAD base-only binding fields")
    if binding["schema"] != SCHEMA or dataset_sha != S.HELDOUT_SHA or binding["dataset_sha256"] != dataset_sha:
        raise ValueError("QAD heldout source SHA mismatch")
    if binding["model_sha256"] != N.GGUF_SHA or binding["runner_sha256"] != V2.RUNNER_SHA:
        raise ValueError("QAD base model/runner hash mismatch")
    if (type(binding["seed"]) is not int or binding["seed"] != N.SEED or
            type(binding["temperature"]) not in (int, float) or binding["temperature"] != 0 or
            binding["decoding"] != C.DECODING or
            type(binding["production_weight_authority"]) is not int or
            binding["production_weight_authority"] != 0 or
            json.dumps(binding["gates"], sort_keys=True) != json.dumps(GATES, sort_keys=True)):
        raise ValueError("QAD base-only decoding/authority/gates drift")
    return True


def validate_files(binding, server, model):
    if not Path(server).is_file() or not os.access(server, os.X_OK):
        raise ValueError("QAD base-only native server not executable")
    observed = {"runner_sha256": C.file_sha(server), "model_sha256": C.file_sha(model)}
    if observed["runner_sha256"] != binding["runner_sha256"] or observed["model_sha256"] != binding["model_sha256"]:
        raise ValueError("QAD base-only native file hash mismatch")
    return observed


@contextmanager
def serve(server, model, port, log_path):
    N.assert_loopback_port_available(port)
    with C.serve(server, model, port, log_path):
        yield


def collect(dataset, binding_path, server, model, out, *, resume=False,
            owner_confirmed=False, ask=C.request, server_context=serve, port=8832):
    if not owner_confirmed:
        raise PermissionError("serial native owner confirmation required")
    index, dataset_sha = S.load_dataset(dataset)
    binding_raw = Path(binding_path).read_bytes()
    binding = S.parse_json(binding_raw.decode("utf-8"))
    validate_binding(binding, dataset_sha)
    observed = validate_files(binding, server, model)
    out = Path(out)
    if resume:
        if not out.is_dir() or (out / "FINAL_MANIFEST.json").exists():
            raise ValueError("QAD base-only resume directory missing/already final")
        if (out / "RUN_BINDING.json").read_bytes() != binding_raw:
            raise ValueError("QAD base-only resume binding bytes changed")
    else:
        out.mkdir(parents=True, exist_ok=False)
        S.exclusive(out / "RUN_BINDING.json", binding_raw)
        S.exclusive(out / "predictions.jsonl", b"")
    target = out / "predictions.jsonl"
    seen, _ = C.existing_records(target, index)
    if any(model_name != "base" for model_name, _, _ in seen):
        raise ValueError("candidate predictions prohibited in base-only collection")
    with server_context(server, model, port, out / "base-server.log"):
        for rid, arm in sorted(index):
            if ("base", rid, arm) in seen:
                continue
            ref = index[(rid, arm)]
            # Only source-bound prompt; never target or answer key.
            response = ask(port, ref["prompt"], binding["seed"])
            if not isinstance(response, str) or len(response) > 8192:
                raise ValueError("QAD base-only native response invalid")
            record = {"model": "base", "row_id": rid, "arm": arm,
                      "source_sha256": ref["source_sha256"],
                      "prompt_sha256": S.sha(ref["prompt"].encode("utf-8")),
                      "response": response}
            with target.open("ab") as stream:
                stream.write((json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n").encode())
                stream.flush()
                os.fsync(stream.fileno())
            seen.add(("base", rid, arm))
    seen, records = C.existing_records(target, index)
    if len(seen) != 22 or len(records) != 22 or any(m != "base" for m, _, _ in seen):
        raise ValueError("QAD base-only collection incomplete/contaminated")
    result = {"schema": COLLECT_SCHEMA, "evidence": "NATIVE_ONLY_AFTER_RAW_INDEPENDENT_AUDIT",
              "dataset_sha256": dataset_sha, "binding_sha256": S.sha(binding_raw),
              "predictions_sha256": C.file_sha(target), "verified_files": observed,
              "rows": 22, "source_pairs": 11, "base_only": True,
              "heldout_targets_sent_to_model": False, "training_executed": False,
              "candidate_evaluated": False, "model_utility_proven": False,
              "redmi_measured": False, "gates": GATES}
    S.exclusive(out / "FINAL_MANIFEST.json",
                (json.dumps(result, indent=2, sort_keys=True) + "\n").encode())
    return result


def score(dataset, binding_path, predictions_path, out):
    index, dataset_sha = S.load_dataset(dataset)
    binding_raw = Path(binding_path).read_bytes()
    binding = S.parse_json(binding_raw.decode("utf-8"))
    validate_binding(binding, dataset_sha)
    predictions, prediction_sha = S.read_jsonl(predictions_path)
    if len(predictions) != 22:
        raise ValueError("QAD base-only incomplete predictions")
    scored = {}
    for row in predictions:
        if not isinstance(row, dict) or set(row) != {
            "model", "row_id", "arm", "source_sha256", "prompt_sha256", "response",
        }:
            raise ValueError("QAD base-only invalid prediction fields")
        rid, arm = row["row_id"], row["arm"]
        if row["model"] != "base" or (rid, arm) not in index or (rid, arm) in scored:
            raise ValueError("QAD base-only duplicate/unknown/candidate prediction")
        ref = index[(rid, arm)]
        if (row["source_sha256"] != ref["source_sha256"] or
                row["prompt_sha256"] != S.sha(ref["prompt"].encode("utf-8"))):
            raise ValueError("QAD base-only source/prompt binding mismatch")
        scored[(rid, arm)] = S.score_one(row["response"], ref["source"], ref["answer_keys"][0])
    if set(scored) != set(index):
        raise ValueError("QAD base-only missing source/arm predictions")
    counts = {}
    for arm in S.ARMS:
        subset = [s for (rid, a), s in scored.items() if a == arm]
        counts[arm] = {"n": len(subset), "supported": sum(x["supported"] for x in subset),
                       "invalid_quote": sum(not x["quote_valid"] for x in subset),
                       "abstained": sum(x["abstained"] for x in subset),
                       "unsupported_commitment": sum(x["unsupported_commitment"] for x in subset),
                       "malformed": sum(not x["parsed"] for x in subset)}
    wins = losses = ties = 0
    for rid in sorted({rid for rid, _ in index}):
        no = scored[(rid, "no_offer")]["supported"]
        yes = scored[(rid, "offer")]["supported"]
        wins += yes and not no
        losses += no and not yes
        ties += yes == no
    result = {"schema": SCORE_SCHEMA, "scope": "SOURCE_BOUND_BASE_ONLY_RESPONSES",
              "dataset_sha256": dataset_sha, "binding_sha256": S.sha(binding_raw),
              "predictions_sha256": prediction_sha, "counts": counts,
              "offer_vs_no_offer": {"wins": wins, "losses": losses, "ties": ties},
              "native_execution_verified_by_scorer": False, "candidate_evaluated": False,
              "training_executed": False, "model_utility_proven": False,
              "redmi_measured": False, "gates": GATES}
    out = Path(out)
    out.mkdir(parents=True, exist_ok=False)
    S.exclusive(out / "SCORES.json", (json.dumps(result, indent=2, sort_keys=True) + "\n").encode())
    return result


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--mode", choices=("collect", "score"), required=True)
    p.add_argument("--dataset", required=True)
    p.add_argument("--binding", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--server")
    p.add_argument("--model")
    p.add_argument("--predictions")
    p.add_argument("--resume", action="store_true")
    p.add_argument("--serial-owner-confirmed", action="store_true")
    a = p.parse_args()
    if a.mode == "collect":
        if not a.server or not a.model:
            p.error("collect requires --server and --model")
        result = collect(a.dataset, a.binding, a.server, a.model, a.out,
                         resume=a.resume, owner_confirmed=a.serial_owner_confirmed)
    else:
        if not a.predictions:
            p.error("score requires --predictions")
        result = score(a.dataset, a.binding, a.predictions, a.out)
    print(json.dumps({"schema": result["schema"], "model_utility_proven": False}, sort_keys=True))


if __name__ == "__main__":
    main()
