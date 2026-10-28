"""Preregistered Run11 stage11 native C3 memory-consumer ablation.

No learned retriever, no model weights updated, no acceptance gate promotion.
All sources are real SourceRefs of synthetic operator feedback in an isolated
V13 store. The native runner is unloaded between arms to avoid prompt-cache
cross-contamination. Requires installed exact pinned model files.
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
from v13.memory import Memory
from v13.prompts import text as prompt
from v13.resources import device
from v13.runtime import Runtime

SEED = 2801028
NATIVE_SEED = 13
NAMES = ("Elyra", "Dovan", "Virel", "Miora", "Seldan", "Orven", "Talira", "Fenro")
ARMS = ("json_baseline", "source_first", "no_source", "wrong_topic")
CLAIM = ("Synthetic native C3 source-consumer prompt rendering only; not learned "
         "retrieval, STEP2, Body-JEPA, Redmi, or original Stage11 promotion.")


def fixtures(seed=SEED):
    rng = random.Random(seed)
    amounts = rng.sample(range(180, 930), len(NAMES))
    return [{"project": name, "topic": f"Project {name} budget",
             "value": f"{amount} Euro",
             "query": (f"What is the budget for Project {name}?"
                       if i < 4 else f"Projekt {name}: Wie hoch ist das Budget?"),
             "language": "en" if i < 4 else "de",
             "amount": amount} for i, (name, amount) in enumerate(zip(NAMES, amounts))]


def exact_amount(answer, amount):
    """Reject numeric substrings inside other numbers; do not score prompt echoes."""
    import re
    return bool(re.search(r"(?<![0-9])" + re.escape(str(amount)) + r"(?![0-9])", answer))


def score(rows):
    by = {arm: [r for r in rows if r["arm"] == arm] for arm in ARMS}
    if any(len(by[a]) != len(NAMES) for a in ARMS):
        return {"complete": False, "status": "INCOMPLETE", "counts": {a: len(by[a]) for a in ARMS}}
    rates = {}
    for arm in ("json_baseline", "source_first"):
        rates[arm] = sum(bool(x["expected_amount_present"]) for x in by[arm]) / len(NAMES)
    no_source_inventions = sum(bool(x["expected_amount_present"]) for x in by["no_source"])
    wrong_topic_leaks = sum(bool(x["wrong_topic_amount_present"]) for x in by["wrong_topic"])
    native_complete = all(x["native_status"] == "FINAL" and x["actual_model"] for x in rows)
    supported = (native_complete and rates["source_first"] - rates["json_baseline"] >= .20
                 and no_source_inventions == 0 and wrong_topic_leaks == 0)
    return {"complete": True, "native_complete": native_complete,
            "status": "CONSUMER_PROMPT_GAIN_SUPPORTED" if supported else "CONSUMER_PROMPT_GAIN_NOT_SUPPORTED",
            "rates": rates, "gain": round(rates["source_first"] - rates["json_baseline"], 4),
            "no_source_inventions": no_source_inventions, "wrong_topic_leaks": wrong_topic_leaks,
            "n": len(NAMES), "per_language": {
                lang: {arm: {"n": len([x for x in by[arm] if x["language"] == lang]),
                              "correct": sum(bool(x["expected_amount_present"]) for x in by[arm]
                                             if x["language"] == lang)}
                       for arm in ("json_baseline", "source_first")}
                for lang in ("en", "de")}}


def messages_for(cfg, arm, fixture, source, other=None):
    base = " ".join(prompt(cfg, k) for k in ("system", "conduct", "answer_rules"))
    if arm == "json_baseline":
        # Same nested-correction framing as the original stage11 C3 consumer.
        entry = {"topic": fixture["topic"], "correction": source}
        context = "\n" + prompt(cfg, "memories") + dumps([entry])
    elif arm == "source_first":
        context = (f"\nVerified user correction for this topic: {fixture['topic']} = {source}. "
                   "Use that correction to answer this question if it refers to the same project. "
                   "Do not substitute an unrelated project or invent a value.")
    elif arm == "no_source":
        context = ("\nNo verified user correction or budget amount is available for this project. "
                   "State uncertainty rather than inventing a number.")
    elif arm == "wrong_topic":
        if not other:
            raise ValueError("wrong-topic control requires a source-backed other project")
        context = (f"\nThe only verified correction belongs to a DIFFERENT project: "
                   f"{other['topic']} = {other['value']}. It does not answer the current project. "
                   "State uncertainty rather than copying the unrelated number.")
    else:
        raise ValueError("Unknown preregistered arm")
    return [{"role": "system", "content": base + context},
            {"role": "user", "content": fixture["query"]}]


def run(installed, out):
    report = {"status": "INCOMPLETE", "scope": CLAIM, "seed": SEED,
              "native_seed": NATIVE_SEED, "arms": ARMS, "fixtures": fixtures(),
              "rows": [], "device": device(), "phone_measured": device()["android"],
              "source_hashes": {str(p.relative_to(APP)): file_hash(p)
                                for p in (Path(__file__).resolve(), APP / "v13/runtime.py",
                                          APP / "v13/runners.py", APP / "v13/memory.py",
                                          APP / "v13/prompts.py")}}
    out.parent.mkdir(parents=True, exist_ok=True)
    def save():
        atomic_write(out, json.dumps(report, ensure_ascii=False, indent=2))
    save()
    with tempfile.TemporaryDirectory(prefix="v13-stage11-consumer-") as tmp:
        home = Path(tmp)
        initialize(home)
        for folder in ("models", "bin"):
            shutil.rmtree(home / folder)
            (home / folder).symlink_to(installed / folder, target_is_directory=True)
        shutil.copyfile(installed / "config/models.json", home / "config/models.json")
        r = Runtime(home)
        try:
            r.cfg.update(observer_mode="off", history_turns=0, answer_tokens=64)
            report["c3_model_sha256"] = file_hash(r.models.path_for("C3_LANGUAGE"))
            report["c3_revision"] = r.models.revision("C3_LANGUAGE")
            records = []
            for fixture in report["fixtures"]:
                event = r.store.event(r.session, fixture["topic"])
                mid = r.memory.feedback(event["event_id"], "fact", fixture["value"],
                                        key=fixture["topic"], permission="record")
                memory = r.memory.candidate(mid, r.session)
                value = r.store.read_source(memory["source_ref"])
                if value != fixture["value"]:
                    raise RuntimeError("SourceRef value mismatch")
                records.append({"memory_id": mid, "source_ref": memory["source_ref"],
                                "topic": fixture["topic"], "value": value})
            report["memory_records"] = records
            save()
            for i, fixture in enumerate(report["fixtures"]):
                source = records[i]["value"]
                other = records[(i + 1) % len(records)]
                for arm in ARMS:
                    messages = messages_for(r.cfg, arm, fixture, source, other)
                    runner = r.pool.get("C3_LANGUAGE")
                    start = time.monotonic()
                    try:
                        chunks = runner.generate(messages, threading.Event(),
                                                 time.monotonic() + 120,
                                                 max_tokens=64, seed=NATIVE_SEED)
                        answer = "".join(chunks)
                        metrics = dict(runner.last_metrics)
                    finally:
                        release = r.pool.unload("C3_LANGUAGE")
                    row = {"project": fixture["project"], "language": fixture["language"],
                           "arm": arm, "query": fixture["query"],
                           "source_ref": records[i]["source_ref"],
                           "other_source_ref": other["source_ref"] if arm == "wrong_topic" else None,
                           "messages": messages,
                           "messages_sha256": hashlib.sha256(dumps(messages).encode()).hexdigest(),
                           "output": answer, "duration_s": time.monotonic() - start,
                           "native_status": metrics.get("status"), "actual_model": metrics.get("actual_model"),
                           "native_metrics": metrics, "release": release,
                           "expected_amount_present": exact_amount(answer, fixture["amount"]),
                           "wrong_topic_amount_present": exact_amount(answer, int(other["value"].split()[0]))
                           if arm == "wrong_topic" else False}
                    report["rows"].append(row)
                    save()
            report["score"] = score(report["rows"])
            report["status"] = report["score"]["status"]
            report["integrity_errors"] = r.store.integrity(True)
            if report["integrity_errors"]:
                report["status"] = "INTEGRITY_FAIL"
            report["model_hash_unchanged"] = file_hash(r.models.path_for("C3_LANGUAGE")) == report["c3_model_sha256"]
            if not report["model_hash_unchanged"]:
                report["status"] = "MODEL_HASH_CHANGED"
        except Exception as exc:
            report["status"] = "INTERRUPTED"
            report["error"] = type(exc).__name__ + ": " + str(exc)[:300]
        finally:
            r.close()
            save()
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--installed-home", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.installed_home.resolve(), args.out.resolve())
    print(dumps({"status": result["status"], "score": result.get("score"),
                 "rows": len(result["rows"])}))
    return 0 if result["status"] == "CONSUMER_PROMPT_GAIN_SUPPORTED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
