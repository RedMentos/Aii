"""Independent BP1 V2 source-quote rescoring of original 44 native responses.

Must first pass bp1_qad_v2_raw_audit. This verifies score bookkeeping,
not learned utility or counterfactual causal effect.
"""
import argparse
import json
import re
import zipfile
from scripts import bp1_qad_v2_raw_audit as A

MARKER = "Original source (untrusted data):\n"
END = {"no_offer": "\nNo B2 offer supplied.\n",
       "offer": "\nB2 summary (untrusted hint, not evidence):\n"}


def pairs_unique(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise ValueError("duplicate response JSON key")
        out[key] = value
    return out


def parse(raw):
    return json.loads(raw, object_pairs_hook=pairs_unique,
                      parse_constant=lambda v: (_ for _ in ()).throw(ValueError("nonfinite JSON")))


def extract_source(prompt, arm):
    A.check(arm in END and prompt.count(MARKER) == 1, "ambiguous source marker")
    after = prompt.split(MARKER, 1)[1]
    A.check(after.count(END[arm]) == 1, "ambiguous source terminator")
    source = after.split(END[arm], 1)[0]
    A.check(bool(source), "empty source")
    return source


def exact(text, key):
    return bool(key) and re.search(r"(?<!\w)" + re.escape(key) + r"(?!\w)", text, re.I) is not None


def score_one(raw, source, key):
    zero = {"parsed": False, "supported": False, "quote_valid": False,
            "abstained": False, "unsupported_commitment": False}
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
            "unsupported_commitment": bool(answer.strip()) and not supported}


def rescore(refs, predictions):
    index = {(r["row_id"], r["arm"]): r for r in refs}
    A.check(len(index) == len(refs) == 22, "duplicate/missing source rows")
    scored = {}
    for p in predictions:
        k = (p["model"], p["row_id"], p["arm"])
        A.check(k not in scored and (p["row_id"], p["arm"]) in index, "duplicate/unknown prediction")
        ref = index[(p["row_id"], p["arm"])]
        A.check(len(ref["answer_keys"]) == 1 and isinstance(ref["answer_keys"][0], str), "invalid answer key")
        source = extract_source(ref["prompt"], ref["arm"])
        A.check(A.sha(source.encode()) == ref["source_sha256"], "source text hash mismatch")
        scored[k] = score_one(p["response"], source, ref["answer_keys"][0])
    A.check(len(scored) == 44, "incomplete score cohort")
    counts = {}
    for model in ("base", "candidate"):
        counts[model] = {}
        for arm in ("no_offer", "offer"):
            subset = [v for (m, rid, a), v in scored.items() if m == model and a == arm]
            counts[model][arm] = {"n": len(subset),
                "supported": sum(v["supported"] for v in subset),
                "invalid_quote": sum(not v["quote_valid"] for v in subset),
                "abstained": sum(v["abstained"] for v in subset),
                "unsupported_commitment": sum(v["unsupported_commitment"] for v in subset),
                "malformed": sum(not v["parsed"] for v in subset)}
            A.check(len(subset) == 11, "incomplete model/arm scores")
    def pair(left, right):
        win = loss = tie = 0
        for x, y in zip(left, right):
            a, b = scored[x]["supported"], scored[y]["supported"]
            win += bool(b and not a)
            loss += bool(a and not b)
            tie += bool(a == b)
        return {"wins": win, "losses": loss, "ties": tie}
    ids = sorted({rid for rid, arm in index})
    within = {m: pair([(m, rid, "no_offer") for rid in ids],
                      [(m, rid, "offer") for rid in ids]) for m in ("base", "candidate")}
    between = {arm: pair([("base", rid, arm) for rid in ids],
                         [("candidate", rid, arm) for rid in ids]) for arm in ("no_offer", "offer")}
    return {"counts": counts, "offer_vs_no_offer": within, "candidate_vs_base": between}


def audit_and_rescore(native_zip, dataset_zip, expected_head, expected_zip_sha):
    bound = A.audit(native_zip, dataset_zip, expected_head, expected_zip_sha)
    with zipfile.ZipFile(native_zip) as z, zipfile.ZipFile(dataset_zip) as d:
        refs = A.jsonl(d.read("bp1-output/heldout_paired.jsonl"))
        predictions = A.jsonl(z.read("predictions.jsonl"))
        result = rescore(refs, predictions)
        reported = json.loads(z.read("V2_SCORES.json"))
        for key in ("counts", "offer_vs_no_offer", "candidate_vs_base"):
            A.check(result[key] == reported.get(key), "independent scorer mismatch: " + key)
    return {"status": "RAW_AND_RESCORE_PASS_NOT_UTILITY",
            "native_zip_sha256": bound["native_zip_sha256"],
            "counts": result["counts"], "offer_vs_no_offer": result["offer_vs_no_offer"],
            "candidate_vs_base": result["candidate_vs_base"],
            "candidate_utility_proven": False, "redmi_measured": False, "gates": A.GATES}


def main():
    p = argparse.ArgumentParser()
    for arg in ("native-zip", "dataset-zip", "expected-head", "expected-zip-sha"):
        p.add_argument("--" + arg, required=True)
    args = p.parse_args()
    print(json.dumps(audit_and_rescore(args.native_zip, args.dataset_zip,
          args.expected_head, args.expected_zip_sha), sort_keys=True))


if __name__ == "__main__":
    main()
