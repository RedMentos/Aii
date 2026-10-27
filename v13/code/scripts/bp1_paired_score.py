#!/usr/bin/env python3
"""BP1 source-bound paired scorer. Never trains, runs, or authorizes a model."""
import argparse
import hashlib
import json
import re
from pathlib import Path

SCHEMA = "V13_BP1_C3_CONSUMER_DATASET_PREFLIGHT_V1"
SCORE_SCHEMA = "V13_BP1_PAIRED_CONSUMER_SCORE_V1"
PREDICTION_SCHEMA = "V13_BP1_C3_CONSUMER_EVAL_V1"
HELDOUT_SHA = "7238a0220255cbccbcf1f9ccfad8dc03febfc37f7bc1d9d0aa645618f006508c"
REPORT_SHA = "ea379b52c7b95c2bb30cd6725f539f443521a64210fdf6bf6fa726c413126880"
ARMS = ("no_offer", "offer")
MODELS = ("base", "candidate")
SOURCE_MARKER = "Original source (untrusted data):\n"
ENDS = {"no_offer": "\nNo B2 offer supplied.\n",
        "offer": "\nB2 summary (untrusted hint, not evidence):\n"}
GATES = {"STEP2": "UTILITY_FAIL", "B3_L1": "FAIL", "Body_JEPA": "UNAVAILABLE",
         "jepa_weight": 0, "Redmi_measured": False, "V13": "INCOMPLETE"}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def no_duplicates(pairs):
    out = {}
    for k, v in pairs:
        if k in out:
            raise ValueError("duplicate JSON key: " + k)
        out[k] = v
    return out


def parse_json(raw):
    def reject_constant(value):
        raise ValueError("nonfinite JSON constant: " + value)
    return json.loads(raw, object_pairs_hook=no_duplicates, parse_constant=reject_constant)


def read_json(path):
    return parse_json(Path(path).read_text(encoding="utf-8"))


def read_jsonl(path):
    raw = Path(path).read_bytes()
    lines = raw.splitlines()
    if not lines or any(not line.strip() for line in lines):
        raise ValueError("empty JSONL or blank line")
    return [parse_json(line.decode("utf-8")) for line in lines], sha(raw)


def is_hash(s):
    return isinstance(s, str) and re.fullmatch(r"[0-9a-f]{64}", s) is not None


def exact(text, key):
    return bool(key) and re.search(r"(?<!\w)" + re.escape(key) + r"(?!\w)", text, re.I) is not None


def source_from_prompt(prompt, arm):
    if not isinstance(prompt, str) or arm not in ARMS or prompt.count(SOURCE_MARKER) != 1:
        raise ValueError("ambiguous source marker")
    after = prompt.split(SOURCE_MARKER, 1)[1]
    end = ENDS[arm]
    if after.count(end) != 1:
        raise ValueError("ambiguous source terminator")
    source, tail = after.split(end, 1)
    if not source or (arm == "no_offer" and tail) or (arm == "offer" and
            "B2 exact-source quote candidates (not necessarily sufficient):\n" not in tail):
        raise ValueError("invalid prompt source boundary")
    return source


def load_dataset(directory, *, pinned=True):
    directory = Path(directory)
    manifest = read_json(directory / "MANIFEST.json")
    if not isinstance(manifest, dict) or manifest.get("schema") != SCHEMA or manifest.get("source_report_sha256") != REPORT_SHA:
        raise ValueError("BP1 manifest/source report mismatch")
    if manifest.get("train_rows") != 25 or manifest.get("heldout_rows") != 22 or manifest.get("heldout_pairs") != 11:
        raise ValueError("unexpected frozen BP1 split counts")
    path = directory / "heldout_paired.jsonl"
    rows, dataset_sha = read_jsonl(path)
    if not is_hash(dataset_sha) or (pinned and dataset_sha != HELDOUT_SHA):
        raise ValueError("heldout dataset SHA mismatch")
    if manifest.get("files_sha256", {}).get("heldout_paired.jsonl") != dataset_sha:
        raise ValueError("heldout SHA absent/mismatch in manifest")
    if len(rows) != 22:
        raise ValueError("incomplete heldout set")
    index = {}
    projects = set()
    for row in rows:
        if not isinstance(row, dict) or set(row) != {"row_id", "source_sha256", "source_project", "question",
                                                       "answer_keys", "target", "kind", "arm", "prompt"}:
            raise ValueError("invalid dataset row fields")
        rid, arm = row["row_id"], row["arm"]
        if not isinstance(rid, str) or not re.fullmatch(r"RUN181-\d{2}", rid) or arm not in ARMS:
            raise ValueError("invalid heldout row ID/arm")
        if (rid, arm) in index:
            raise ValueError("duplicate heldout arm")
        if row["kind"] != "synthetic" or not isinstance(row["question"], str) or not isinstance(row["source_project"], str):
            raise ValueError("invalid heldout source metadata")
        if not isinstance(row["answer_keys"], list) or len(row["answer_keys"]) != 1 or not isinstance(row["answer_keys"][0], str):
            raise ValueError("invalid heldout key")
        source = source_from_prompt(row["prompt"], arm)
        if sha(source.encode("utf-8")) != row["source_sha256"]:
            raise ValueError("source SHA mismatch")
        target = parse_json(row["target"])
        if not isinstance(target, dict) or set(target) != {"answer", "evidence_quote", "uncertainty"}:
            raise ValueError("invalid target")
        if target["answer"] != row["answer_keys"][0] or not isinstance(target["evidence_quote"], str) or target["evidence_quote"] not in source:
            raise ValueError("target not bound to source")
        if not exact(target["evidence_quote"], target["answer"]):
            raise ValueError("target quote does not support key")
        index[(rid, arm)] = dict(row, source=source)
        projects.add(row["source_project"])
    ids = {rid for rid, _ in index}
    if len(ids) != 11 or any((rid, arm) not in index for rid in ids for arm in ARMS):
        raise ValueError("missing paired heldout arm")
    for rid in ids:
        a, b = (index[(rid, arm)] for arm in ARMS)
        for k in ("source_sha256", "source_project", "question", "answer_keys", "target", "source"):
            if a[k] != b[k]:
                raise ValueError("heldout pair differs on " + k)
    if set(manifest.get("heldout_projects", [])) != projects or projects & set(manifest.get("train_projects", [])):
        raise ValueError("heldout project split mismatch")
    return index, dataset_sha


def score_one(raw, source, key):
    zero = {"parsed": False, "supported": False, "quote_valid": False,
            "abstained": False, "unsupported_commitment": False}
    if not isinstance(raw, str) or len(raw) > 8192:
        return zero
    try:
        obj = parse_json(raw)
    except (ValueError, TypeError, UnicodeError):
        return zero
    if not isinstance(obj, dict) or set(obj) != {"answer", "evidence_quote", "uncertainty"} or any(
            not isinstance(obj[k], str) for k in ("answer", "evidence_quote", "uncertainty")):
        return zero
    answer, quote, uncertainty = (obj[k] for k in ("answer", "evidence_quote", "uncertainty"))
    quote_valid = bool(quote) and quote in source
    supported = answer.strip().casefold() == key.casefold() and quote_valid and exact(quote, key)
    abstained = not answer.strip() and bool(uncertainty.strip())
    return {"parsed": True, "supported": supported, "quote_valid": quote_valid,
            "abstained": abstained, "unsupported_commitment": bool(answer.strip()) and not supported}


def validate_binding(binding, dataset_sha):
    if not isinstance(binding, dict) or set(binding) != {"schema", "dataset_sha256", "models", "runner_sha256",
                                                         "seed", "temperature", "decoding"}:
        raise ValueError("invalid native-run binding fields")
    if binding["schema"] != PREDICTION_SCHEMA or binding["dataset_sha256"] != dataset_sha:
        raise ValueError("prediction dataset binding mismatch")
    models = binding["models"]
    if not isinstance(models, dict) or set(models) != set(MODELS):
        raise ValueError("missing model arms")
    for model in MODELS:
        m = models[model]
        if not isinstance(m, dict) or set(m) != {"master_sha256", "deployed_gguf_sha256"} or not all(is_hash(v) for v in m.values()):
            raise ValueError("missing model SHA binding")
    if models["base"]["deployed_gguf_sha256"] == models["candidate"]["deployed_gguf_sha256"]:
        raise ValueError("base/candidate deployed hashes identical")
    if not is_hash(binding["runner_sha256"]) or type(binding["seed"]) is not int or type(binding["temperature"]) not in (int, float):
        raise ValueError("invalid runner/seed/temperature")
    if binding["temperature"] != 0 or not isinstance(binding["decoding"], str) or not binding["decoding"]:
        raise ValueError("non-greedy or unbound decoding")
    return True


def evaluate(index, dataset_sha, binding, predictions):
    validate_binding(binding, dataset_sha)
    if len(predictions) != 2 * len(index):
        raise ValueError("incomplete predictions: require 44 exact model/arm rows")
    scored = {}
    for row in predictions:
        fields = {"model", "row_id", "arm", "source_sha256", "prompt_sha256", "response"}
        if not isinstance(row, dict) or set(row) != fields:
            raise ValueError("invalid prediction fields")
        model, rid, arm = row["model"], row["row_id"], row["arm"]
        if model not in MODELS or (rid, arm) not in index or (model, rid, arm) in scored:
            raise ValueError("unknown/duplicate prediction")
        ref = index[(rid, arm)]
        if row["source_sha256"] != ref["source_sha256"] or row["prompt_sha256"] != sha(ref["prompt"].encode("utf-8")):
            raise ValueError("prediction source/prompt binding mismatch")
        scored[(model, rid, arm)] = score_one(row["response"], ref["source"], ref["answer_keys"][0])
    expected = {(model, rid, arm) for model in MODELS for rid, arm in index}
    if set(scored) != expected:
        raise ValueError("incomplete model/arm predictions")
    counts = {}
    for model in MODELS:
        counts[model] = {}
        for arm in ARMS:
            subset = [s for (m, _, a), s in scored.items() if m == model and a == arm]
            counts[model][arm] = {"n": len(subset), "supported": sum(x["supported"] for x in subset),
                "invalid_quote": sum(not x["quote_valid"] for x in subset),
                "abstained": sum(x["abstained"] for x in subset),
                "unsupported_commitment": sum(x["unsupported_commitment"] for x in subset),
                "malformed": sum(not x["parsed"] for x in subset)}
    def paired(keys):
        wins = losses = ties = 0
        for left, right in keys:
            a, b = scored[left]["supported"], scored[right]["supported"]
            wins += b and not a
            losses += a and not b
            ties += a == b
        return {"wins": wins, "losses": losses, "ties": ties}
    ids = sorted({rid for rid, _ in index})
    within = {m: paired([((m, rid, "no_offer"), (m, rid, "offer")) for rid in ids]) for m in MODELS}
    between = {arm: paired([(("base", rid, arm), ("candidate", rid, arm)) for rid in ids]) for arm in ARMS}
    return {"schema": SCORE_SCHEMA, "scope": "SOFTWARE_SCORING_OF_OPERATOR_SUPPLIED_RESPONSES",
            "dataset_sha256": dataset_sha, "binding": binding, "counts": counts,
            "offer_vs_no_offer": within, "candidate_vs_base": between,
            "native_execution_verified_by_scorer": False, "training_executed_by_scorer": False,
            "model_utility_proven": False, "gates": GATES}


def exclusive(path, data):
    with Path(path).open("xb") as f:
        f.write(data)
        f.flush()
        import os
        os.fsync(f.fileno())


def main():
    p = argparse.ArgumentParser(description="BP1 post-inference scorer; never performs native inference")
    p.add_argument("--dataset", required=True)
    p.add_argument("--binding")
    p.add_argument("--predictions")
    p.add_argument("--out")
    p.add_argument("--selfcheck", action="store_true")
    args = p.parse_args()
    index, dataset_sha = load_dataset(args.dataset)
    if args.selfcheck:
        if args.binding or args.predictions or args.out:
            p.error("--selfcheck cannot score predictions")
        print(json.dumps({"dataset_sha256": dataset_sha, "heldout_rows": len(index),
                          "paired_sources": len(index)//2, "native_c3_run": False}, sort_keys=True))
        return
    if not all((args.binding, args.predictions, args.out)):
        p.error("scoring requires --binding --predictions --out")
    binding = read_json(args.binding)
    predictions, prediction_sha = read_jsonl(args.predictions)
    result = evaluate(index, dataset_sha, binding, predictions)
    result["prediction_file_sha256"] = prediction_sha
    result["binding_file_sha256"] = sha(Path(args.binding).read_bytes())
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    if any(out.iterdir()):
        raise ValueError("output directory must be empty")
    exclusive(out / "SCORES.json", (json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode())
    print(json.dumps({"counts": result["counts"], "offer_vs_no_offer": result["offer_vs_no_offer"],
                      "candidate_vs_base": result["candidate_vs_base"], "native_execution_verified": False}, sort_keys=True))


if __name__ == "__main__":
    main()
