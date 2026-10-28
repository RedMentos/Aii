"""Independent source-pinned Linux-native C5 no-B proactive-selection probe.

Only a temporary manifest loses B1/B2. This is not STEP2 or Redmi acceptance.
"""
import argparse
import json
import platform
import shutil
import tempfile
import threading
import time
from pathlib import Path

from v13.common import APP, atomic_write, dumps, file_hash
from v13.config import initialize, save_config
from v13.models import ModelManager
from v13.runtime import Runtime

FIXTURES = (
    ("auto", "Say one short sentence about trees."),
    ("detail", "What is half of 120?"),
    ("gist", "Describe a blue sky briefly."),
    ("both", "Give one short greeting."),
    ("gist", "Describe a green leaf briefly."),
)
ROLES = ("needle", "language", "body", "gist")


def run(installed_home, out):
    parent = Path(installed_home).resolve()
    output = Path(out)
    output.parent.mkdir(parents=True, exist_ok=True)
    report = {
        "status": "C5_NO_B_NATIVE_RUNNING",
        "claim_limit": "Source-pinned Linux C5 proactive no-B selection only; no semantic quality, STEP2 or Redmi promotion.",
        "seed": 13,
        "platform": platform.platform(),
        "phone_measured": False,
        "fixtures": [{"route": route, "query": query} for route, query in FIXTURES],
        "turns": [],
        "checks": {},
        "source_sha256": {str(p.relative_to(APP)): file_hash(p) for p in
            (APP / "v13/runtime.py", APP / "v13/focal.py", APP / "v13/bodies.py",
             APP / "specs/models.json", APP / "scripts/c5_no_b_native_probe.py")},
    }
    def save():
        atomic_write(output, dumps(report))

    save()
    r = None
    try:
        before = ModelManager(parent).verify(deep=True)
        report["models_before"] = before
        if not all(k in before and before[k]["ok"] and before[k]["hash_checked"] for k in ROLES):
            raise RuntimeError("PINNED_MODELS_NOT_DEEP_VERIFIED")
        with tempfile.TemporaryDirectory(prefix="v13-c5-no-b-native-") as tmp:
            home = Path(tmp)
            cfg = initialize(home)
            cfg.update(learning_mode="RECORD_ONLY", system_stage=0, latents_enabled=False,
                       jepa_weight=0, observer_mode="off", route_override="auto",
                       teacher_enabled=False, history_turns=0, seed=13, answer_tokens=96)
            save_config(home, cfg)
            for name in ("models", "bin"):
                shutil.rmtree(home / name)
                (home / name).symlink_to(parent / name, target_is_directory=True)
            shutil.copyfile(parent / "config/models.json", home / "config/models.json")
            r = Runtime(home)
            for key in ("body", "gist"):
                r.models.installed.pop(key, None)
            r.models.save()
            report["temporary_installed_roles"] = sorted(r.models.installed)
            report["no_b_manifest"] = not ({"body", "gist"} & set(r.models.installed))
            save()

            session = r.session
            generation = r.store.generation_id
            for i, (route, query) in enumerate(FIXTURES):
                if i == 4:
                    r.close()
                    r = Runtime(home)
                    report["restart"] = {
                        "same_session": r.session == session,
                        "same_generation": r.store.generation_id == generation,
                        "no_b_manifest": not ({"body", "gist"} & set(r.models.installed)),
                        "manager_attached": getattr(r.store, "_model_manager", None) is r.models,
                    }
                r.cfg["route_override"] = route
                eid = r.submit(query)
                deadline = time.monotonic() + 90
                while not r.idle():
                    if time.monotonic() > deadline:
                        r.cancel()
                        raise TimeoutError("NATIVE_TURN_DEADLINE")
                    time.sleep(.05)
                msg = r.store.one(
                    "SELECT status,text,metadata FROM messages WHERE event_id=? AND role='assistant' ORDER BY rowid LIMIT 1",
                    (eid,))
                selected = r.store.one(
                    "SELECT payload FROM packets WHERE kind='ActionSelection' AND event_id=? ORDER BY rowid DESC LIMIT 1",
                    (eid,))
                packet = json.loads(selected["payload"]) if selected else {}
                meta = json.loads(msg["metadata"]) if msg else {}
                suppress = {x["action_id"]: x["reason"] for x in packet.get("suppressed", [])}
                row = {
                    "route": route, "query": query, "event_id": eid,
                    "status": msg["status"] if msg else "MISSING",
                    "output": msg["text"] if msg else "",
                    "c5_selected": packet.get("selected", {}).get("action_id"),
                    "suppressed": suppress,
                    "native_c2_observed": "native_control" in meta.get("route", {}),
                    "native_c3_observed": meta.get("runner", {}).get("role") == "C3_LANGUAGE"
                        and meta.get("model_generated") is True,
                    "late_fallback": meta.get("fallback"),
                    "runner": meta.get("runner", {}),
                }
                report["turns"].append(row)
                save()
            report["store_integrity_errors"] = r.store.integrity(True)
            r.close()
            r = None
        after = ModelManager(parent).verify(deep=True)
        report["models_after"] = after
        report["model_hash_unchanged"] = before == after
        report["checks"] = {
            "five_native_final": len(report["turns"]) == 5
                and all(x["status"] == "FINAL" and x["output"].strip() for x in report["turns"]),
            "c5_proactive_c3": len(report["turns"]) == 5
                and all(x["c5_selected"] == "C3_LANGUAGE" for x in report["turns"]),
            "b1_b2_suppressed": len(report["turns"]) == 5 and all(
                x["suppressed"].get("B1_DETAIL") == "MODEL_MANIFEST_UNAVAILABLE"
                and x["suppressed"].get("B2_GIST") == "MODEL_MANIFEST_UNAVAILABLE"
                for x in report["turns"]),
            "no_late_fallback": all(x["late_fallback"] is None for x in report["turns"]),
            "actual_c3": all(x["native_c3_observed"] for x in report["turns"]),
            "actual_c2_auto": report["turns"][0]["native_c2_observed"],
            "temporary_no_b": report["no_b_manifest"],
            "restart": all(report.get("restart", {}).values()),
            "store_integrity": not report["store_integrity_errors"],
            "parent_models_unchanged": report["model_hash_unchanged"],
        }
        report["status"] = ("C5_NO_B_NATIVE_SCOPED_PASS" if all(report["checks"].values())
                            else "C5_NO_B_NATIVE_SCOPED_FAIL")
    except Exception as exc:
        report["status"] = "C5_NO_B_NATIVE_INTERRUPTED"
        report["error_type"] = type(exc).__name__
        report["error"] = str(exc)[:500]
    finally:
        if r is not None:
            r.close()
        save()
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--installed-home", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    result = run(args.installed_home, args.out)
    print(json.dumps({"status": result["status"], "checks": result["checks"],
                      "turn_count": len(result["turns"])}, sort_keys=True))
    return 0 if result["status"] == "C5_NO_B_NATIVE_SCOPED_PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
