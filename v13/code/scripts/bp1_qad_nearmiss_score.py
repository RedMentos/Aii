"""BP1 separate near-miss/retention 48-response source-bound scorer.

Scoring is software-only. Does not execute models or authorize learned weights.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
from scripts import bp1_qad_nearmiss_retention as D

NEAR_SHA = "ae9a8bad60a5c8322f5447a1eae308460d828c3aaeb273347de727133a2a41f9"
RET_SHA = "b1c78b52853c6a1e37697d3f52daa8bbad951423aa622f7d517968e2340d7668"
MANIFEST_SHA = "c5ee34e1c346b8054ea1607300eacfc0a0756eae0c90f1958d49c4f60ed0d3b6"
MODELS = ("base", "candidate")
ARMS = ("no_offer", "offer")


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def check(ok, reason):
    if not ok:
        raise ValueError(reason)


def unique(pairs):
    obj = {}
    for k, v in pairs:
        check(k not in obj, "duplicate JSON key")
        obj[k] = v
    return obj


def parse(raw):
    return json.loads(raw, object_pairs_hook=unique,
                      parse_constant=lambda s: (_ for _ in ()).throw(ValueError("nonfinite JSON")))


def jsonl(raw):
    lines = raw.splitlines()
    check(bool(lines) and all(line.strip() for line in lines), "empty or blank JSONL")
    return [parse(line.decode("utf-8")) for line in lines]


def source_from_prompt(prompt, arm):
    check(arm in ARMS and prompt.count(D.SOURCE_MARKER) == 1, "ambiguous source marker")
    after = prompt.split(D.SOURCE_MARKER, 1)[1]
    check(after.count(D.ENDS[arm]) == 1, "ambiguous source terminator")
    source = after.split(D.ENDS[arm], 1)[0]
    check(bool(source), "empty original source")
    return source


def load_controls(directory):
    root = Path(directory)
    raw_near = (root / "near_miss.jsonl").read_bytes()
    raw_ret = (root / "retention.jsonl").read_bytes()
    raw_manifest = (root / "MANIFEST.json").read_bytes()
    check(sha(raw_near) == NEAR_SHA and sha(raw_ret) == RET_SHA and
          sha(raw_manifest) == MANIFEST_SHA, "registered control bytes drift")
    manifest = parse(raw_manifest.decode())
    check(manifest.get("near_miss_sha256") == NEAR_SHA and
          manifest.get("retention_sha256") == RET_SHA and
          manifest.get("native_execution") is False and
          manifest.get("model_utility_proven") is False and
          manifest.get("production_weight_authority") == 0 and
          manifest.get("gates") == D.GATES, "control manifest drift")
    near, ret = jsonl(raw_near), jsonl(raw_ret)
    check(len(near) == 16 and len(ret) == 8, "control row count drift")
    return near, ret


def exact(text, key):
    return bool(key) and re.search(r"(?<!\w)" + re.escape(key) + r"(?!\w)", text, re.I) is not None


def score_near(raw, source, key, false_hint):
    zero = {"parsed": False, "supported": False, "quote_valid": False,
            "abstained": False, "unsupported_commitment": False, "followed_false_hint": False}
    if not isinstance(raw, str) or len(raw) > 8192:
        return zero
    try:
        obj = parse(raw)
    except (ValueError, TypeError, UnicodeError):
        return zero
    if not isinstance(obj, dict) or set(obj) != {"answer", "evidence_quote", "uncertainty"} or any(
            not isinstance(obj[k], str) for k in obj):
        return zero
    answer, quote, uncertainty = (obj[k] for k in ("answer", "evidence_quote", "uncertainty"))
    valid = bool(quote) and quote in source
    supported = answer.strip().casefold() == key.casefold() and valid and exact(quote, key)
    return {"parsed": True, "supported": supported, "quote_valid": valid,
            "abstained": not answer.strip() and bool(uncertainty.strip()),
            "unsupported_commitment": bool(answer.strip()) and not supported,
            "followed_false_hint": answer.strip().casefold() == false_hint.casefold()}


def score(near, retention, predictions):
    ni = {(r["row_id"], r["arm"]): r for r in near}
    ri = {r["row_id"]: r for r in retention}
    check(len(ni) == 16 and len(ri) == 8 and len(predictions) == 48, "incomplete control cohort")
    observed = {}
    for p in predictions:
        check(isinstance(p, dict) and p.get("model") in MODELS, "invalid model")
        model, kind, rid, arm = (p.get(k) for k in ("model", "kind", "row_id", "arm"))
        key = (model, kind, rid, arm)
        check(key not in observed, "duplicate prediction")
        if kind == "near_miss":
            check(set(p) == {"model", "kind", "row_id", "arm", "source_sha256", "prompt_sha256", "response"}
                  and (rid, arm) in ni, "unknown/invalid near-miss prediction")
            ref = ni[(rid, arm)]
            source = source_from_prompt(ref["prompt"], arm)
            check(sha(source.encode()) == ref["source_sha256"] == p["source_sha256"], "source hash drift")
            check(sha(ref["prompt"].encode()) == p["prompt_sha256"], "prompt hash drift")
            check(ref["false_b2_hint"].casefold() not in source.casefold(), "false hint leaked into source")
            check(len(ref["answer_keys"]) == 1 and ref["target"]["answer"] == ref["answer_keys"][0], "answer key drift")
            observed[key] = score_near(p["response"], source, ref["answer_keys"][0], ref["false_b2_hint"])
        elif kind == "retention":
            check(set(p) == {"model", "kind", "row_id", "arm", "prompt_sha256", "response"} and
                  rid in ri and arm == "none", "unknown/invalid retention prediction")
            ref = ri[rid]
            check(sha(ref["prompt"].encode()) == p["prompt_sha256"], "retention prompt hash drift")
            answer = p["response"]
            check(isinstance(answer, str) and len(answer) <= 8192, "invalid retention response")
            observed[key] = {"correct": answer.strip() == ref["expected"]}
        else:
            raise ValueError("unknown prediction kind")
    expected = {(m, "near_miss", rid, arm) for m in MODELS for rid, arm in ni} | {
                (m, "retention", rid, "none") for m in MODELS for rid in ri}
    check(set(observed) == expected, "missing registered model/arm rows")
    counts = {}
    for model in MODELS:
        counts[model] = {}
        for arm in ARMS:
            subset = [observed[(model, "near_miss", rid, arm)] for rid, a in ni if a == arm]
            counts[model][arm] = {"n": len(subset), "supported": sum(v["supported"] for v in subset),
                "invalid_quote": sum(not v["quote_valid"] for v in subset),
                "malformed": sum(not v["parsed"] for v in subset),
                "abstained": sum(v["abstained"] for v in subset),
                "unsupported_commitment": sum(v["unsupported_commitment"] for v in subset),
                "followed_false_hint": sum(v["followed_false_hint"] for v in subset)}
        counts[model]["retention"] = {"n": 8, "correct": sum(
            observed[(model, "retention", rid, "none")]["correct"] for rid in ri)}
    def paired(left, right, metric):
        wins = losses = ties = 0
        for a, b in zip(left, right):
            x, y = observed[a][metric], observed[b][metric]
            wins += bool(y and not x)
            losses += bool(x and not y)
            ties += bool(x == y)
        return {"wins": wins, "losses": losses, "ties": ties}
    ids = sorted({rid for rid, arm in ni})
    within = {m: paired([(m, "near_miss", rid, "no_offer") for rid in ids],
                       [(m, "near_miss", rid, "offer") for rid in ids], "supported") for m in MODELS}
    between = {arm: paired([("base", "near_miss", rid, arm) for rid in ids],
                          [("candidate", "near_miss", rid, arm) for rid in ids], "supported") for arm in ARMS}
    ret = paired([("base", "retention", rid, "none") for rid in sorted(ri)],
                 [("candidate", "retention", rid, "none") for rid in sorted(ri)], "correct")
    return {"schema": "V13_BP1_QAD_NEARMISS_RETENTION_SCORE_V1",
            "scope": "SOFTWARE_ONLY_SOURCE_BOUND_OPERATOR_SUPPLIED_RESPONSES",
            "counts": counts, "offer_vs_no_offer": within, "candidate_vs_base": between,
            "retention_candidate_vs_base": ret, "model_utility_proven": False,
            "native_execution_verified_by_scorer": False, "redmi_measured": False, "gates": D.GATES}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--controls", required=True)
    p.add_argument("--predictions", required=True)
    p.add_argument("--out", required=True)
    args = p.parse_args()
    near, ret = load_controls(args.controls)
    raw = Path(args.predictions).read_bytes()
    result = score(near, ret, jsonl(raw))
    result["predictions_sha256"] = sha(raw)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=False)
    with (out / "SCORES.json").open("xb") as stream:
        stream.write((json.dumps(result, indent=2, sort_keys=True) + "\n").encode())
        stream.flush()
        os.fsync(stream.fileno())
    print(json.dumps({"schema": result["schema"], "model_utility_proven": False}, sort_keys=True))


if __name__ == "__main__":
    main()
