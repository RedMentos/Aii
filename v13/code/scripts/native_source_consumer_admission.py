"""Native source-bound C3 consumer holdout; preregistered, isolated, no weight updates.

Only admitted human-correction sources reach the actual pinned model. Missing,
wrong-entity and conflicting-source cases must stop *before* generation.
"""
import argparse
import hashlib
import json
import random
import shutil
import tempfile
import threading
import time
from pathlib import Path

from v13.common import APP, atomic_write, dumps, file_hash
from v13.config import initialize
from v13.resources import device
from v13.runtime import Runtime
from v13.source_consumer import admit, render_messages, strict_exact_amount, unsupported_amount

SEED = 2801029
NATIVE_SEED = 13
NAMES = ("Gryna", "Uldar", "Hovena", "Rivon", "Karell", "Peldra", "Norven", "Ysola")
CLAIM = "Scoped synthetic project-budget source consumer only; no general utility or AGI gate."


def fixtures():
    rng = random.Random(SEED)
    amounts = rng.sample(range(181, 929), len(NAMES))
    return [{"project": name, "topic": f"Project {name} budget",
             "value": f"{amount} Euro", "amount": amount,
             "query": (f"What is the budget for Project {name}?" if i < 4
                       else f"Projekt {name}: Wie hoch ist das Budget?"),
             "language": "en" if i < 4 else "de"}
            for i, (name, amount) in enumerate(zip(NAMES, amounts))]


def score(report):
    pos = report["positive"]
    neg = report["negative"]
    if len(pos) != 8 or len(neg) != 24:
        return {"status": "INCOMPLETE", "positive_n": len(pos), "negative_n": len(neg)}
    correct = sum(bool(x["exact_amount"]) for x in pos)
    no_model = all(x["native_calls"] == 0 and x["status"] == "CLARIFY" for x in neg)
    no_numbers = all(not x["unsupported_amount"] and not x["unrelated_source_leak"] for x in neg)
    native = all(x["native_status"] == "FINAL" and x["actual_model"] for x in pos)
    source = all(x["source_verified"] for x in pos)
    passed = correct >= 7 and no_model and no_numbers and native and source
    return {"status": "SOURCE_CONSUMER_SCOPED_NATIVE_PASS" if passed else "SOURCE_CONSUMER_SCOPED_NATIVE_FAIL",
            "positive_correct": correct, "positive_n": 8, "negative_n": 24,
            "no_negative_model_calls": no_model, "no_negative_amounts": no_numbers,
            "native_complete": native, "source_verified": source,
            "per_language": {lang: {"correct": sum(x["exact_amount"] for x in pos if x["language"] == lang),
                                     "n": sum(x["language"] == lang for x in pos)}
                             for lang in ("en", "de")}}


def run(installed, out):
    report = {"status": "INCOMPLETE", "claim_limit": CLAIM, "seed": SEED,
              "native_seed": NATIVE_SEED, "fixtures": fixtures(), "positive": [],
              "negative": [], "native_call_count": 0, "device": device(),
              "phone_measured": device()["android"],
              "source_hashes": {str(p.relative_to(APP)): file_hash(p)
                                for p in (Path(__file__).resolve(), APP / "v13/source_consumer.py",
                                          APP / "v13/memory.py", APP / "v13/runtime.py",
                                          APP / "v13/runners.py")}}
    out.parent.mkdir(parents=True, exist_ok=True)
    def save():
        atomic_write(out, json.dumps(report, ensure_ascii=False, indent=2))
    save()
    with tempfile.TemporaryDirectory(prefix="v13-consumer-guarded-") as tmp:
        home = Path(tmp)
        initialize(home)
        for folder in ("models", "bin"):
            shutil.rmtree(home / folder)
            (home / folder).symlink_to(installed / folder, target_is_directory=True)
        shutil.copyfile(installed / "config/models.json", home / "config/models.json")
        r = Runtime(home)
        try:
            r.cfg.update(observer_mode="off", history_turns=0, answer_tokens=64)
            report["model_sha256"] = file_hash(r.models.path_for("C3_LANGUAGE"))
            report["model_revision"] = r.models.revision("C3_LANGUAGE")
            records = []
            for f in report["fixtures"]:
                e = r.store.event(r.session, f["topic"])
                mid = r.memory.feedback(e["event_id"], "fact", f["value"], key=f["topic"], permission="record")
                m = r.memory.candidate(mid, r.session)
                if r.store.read_source(m["source_ref"]) != f["value"]:
                    raise RuntimeError("SourceRef mismatch")
                records.append(m)
            report["source_refs"] = [m["source_ref"] for m in records]
            save()
            for i, f in enumerate(report["fixtures"]):
                decision = admit(f["query"], r.session, [records[i]], r.memory)
                if decision["status"] != "ADMITTED" or not decision["model_allowed"]:
                    raise RuntimeError("Correct human source rejected by admission")
                messages = render_messages(r.cfg, f["query"], decision)
                runner = r.pool.get("C3_LANGUAGE")
                report["native_call_count"] += 1
                start = time.monotonic()
                try:
                    answer = "".join(runner.generate(messages, threading.Event(),
                                                     time.monotonic() + 120,
                                                     max_tokens=64, seed=NATIVE_SEED))
                    metrics = dict(runner.last_metrics)
                finally:
                    release = r.pool.unload("C3_LANGUAGE")
                report["positive"].append({
                    "project": f["project"], "language": f["language"], "query": f["query"],
                    "expected": f["value"], "output": answer,
                    "source_verified": r.store.read_source(decision["source"]["source_ref"]) == f["value"],
                    "source_ref": decision["source"]["source_ref"],
                    "messages": messages, "messages_sha256": hashlib.sha256(dumps(messages).encode()).hexdigest(),
                    "exact_amount": strict_exact_amount(answer, f["amount"]),
                    "native_status": metrics.get("status"), "actual_model": metrics.get("actual_model"),
                    "native_metrics": metrics, "release": release,
                    "duration_s": time.monotonic() - start})
                save()
            for i, f in enumerate(report["fixtures"]):
                other = records[(i + 1) % len(records)]
                e = r.store.event(r.session, f["topic"] + " conflicting correction")
                mid = r.memory.feedback(e["event_id"], "fact", f"{f['amount'] + 71} Euro",
                                        key=f["topic"] + "s", permission="record")
                conflicting = r.memory.candidate(mid, r.session)
                cases = [("no_source", []), ("wrong_topic", [other]),
                         ("conflict", [records[i], conflicting])]
                for label, candidates in cases:
                    before = report["native_call_count"]
                    decision = admit(f["query"], r.session, candidates, r.memory)
                    if decision["status"] == "ADMITTED":
                        raise RuntimeError("Negative source unexpectedly admitted: " + label)
                    output = decision.get("answer", "")
                    report["negative"].append({
                        "project": f["project"], "language": f["language"], "case": label,
                        "status": decision["status"], "reason": decision["reason"],
                        "output": output, "native_calls": report["native_call_count"] - before,
                        "unsupported_amount": unsupported_amount(output),
                        "unrelated_source_leak": other["value"] in output or conflicting["value"] in output})
                    save()
            report["score"] = score(report)
            report["status"] = report["score"]["status"]
            report["integrity_errors"] = r.store.integrity(True)
            report["model_hash_unchanged"] = file_hash(r.models.path_for("C3_LANGUAGE")) == report["model_sha256"]
            if report["integrity_errors"] or not report["model_hash_unchanged"]:
                report["status"] = "INTEGRITY_OR_MODEL_HASH_FAIL"
        except Exception as exc:
            report["status"] = "INTERRUPTED"
            report["error"] = type(exc).__name__ + ": " + str(exc)[:300]
        finally:
            r.close()
            save()
    return report


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--installed-home", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    result = run(a.installed_home.resolve(), a.out.resolve())
    print(dumps({"status": result["status"], "score": result.get("score"),
                 "native_calls": result["native_call_count"]}))
    return 0 if result["status"] == "SOURCE_CONSUMER_SCOPED_NATIVE_PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
