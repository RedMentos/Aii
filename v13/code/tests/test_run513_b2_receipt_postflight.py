"""Run513 independent receipt auditor: synthetic source-only fixtures, no models."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import run509_b2_rule_quote_prereg as frozen
import run511_b2_offer_collector as collector
import run513_b2_receipt_postflight as audit


def write(path, value):
    Path(path).write_text(json.dumps(value, sort_keys=True, allow_nan=False) + "\n")


def write_lines(path, values):
    Path(path).write_text("".join(json.dumps(v, sort_keys=True, allow_nan=False)
                                  + "\n" for v in values))


def make_stage(work):
    plan = collector.plan(0)
    write(work / "RUN511_STAGE_PLAN.json", plan)
    reg = frozen.registration()
    preflight = {
        "model_sha256": reg["model_sha256_expected_not_retrieved"],
        "runner_sha256": reg["runner_sha256_expected_not_retrieved"],
        "runtime_library_sha256": {"lib": "a" * 64},
        "native_executed": False,
    }
    write(work / "RUN511_INSTALLED_PREFLIGHT.json", preflight)
    fixtures = {f["id"]: f for f in reg["fixtures"]}
    rows = []
    progress = []
    for fixture_name in plan["fixture_ids"]:
        fixture = fixtures[fixture_name]
        originals = fixture["history"] + [fixture["current"]]
        for seed in frozen.SEEDS:
            prior = []
            for i, value in enumerate(originals[:3]):
                prior.append({
                    "source_id": f"prior-{fixture_name}-{seed}-{i}",
                    "sha256": hashlib.sha256(value.encode()).hexdigest(),
                    "char_start": 0, "char_end": len(value),
                    "modality": "text",
                })
            prep = {
                "status": "CLOSED_PREPARATION_SOURCE_ONLY",
                "fixture": fixture_name, "seed": seed,
                "model_sha256": preflight["model_sha256"],
                "runner_sha256": preflight["runner_sha256"],
                "runtime_library_sha256": preflight["runtime_library_sha256"],
                "checkpoint_hashes": {"db": "b" * 64},
                "sealed_sha256": "c" * 64,
                "prior_event_source_refs": prior,
            }
            write(work / f"RUN511_PREP_{fixture_name}_s{seed}.json", prep)
            progress.extend([
                {"state": "PREP_STARTED", "fixture": fixture_name,
                 "seed": seed, "time_ns": 123},
                {"state": "PREP_SEALED", "fixture": fixture_name,
                 "seed": seed, "sealed_sha256": "c" * 64,
                 "time_ns": 124},
            ])
            for arm in frozen.ARMS:
                current = {
                    "source_id": f"current-{fixture_name}-{seed}-{arm}",
                    "sha256": hashlib.sha256(originals[3].encode()).hexdigest(),
                    "char_start": 0, "char_end": len(originals[3]),
                    "modality": "text",
                }
                refs = prior + [current]
                slots = []
                for slot, value, ref in zip(audit.SLOTS, originals, refs):
                    slots.append({
                        "source_slot": slot, "source_id": ref["source_id"],
                        "source_sha256": ref["sha256"],
                        "char_start": 0, "char_end": len(value),
                        "source_text": value,
                    })
                excerpt = originals[0][:12]
                quote_ref = dict(prior[0])
                quote_ref["char_end"] = len(excerpt)
                rows.append({
                    "fixture": fixture_name, "arm": arm, "seed": seed,
                    "status": "RECORDED", "source_slots": slots,
                    "source_history0_sha256": prior[0]["sha256"],
                    "quotes": [{
                        "source_slot": "history0",
                        "source_sha256": prior[0]["sha256"],
                        "text": excerpt,
                    }],
                    "evidence_refs": [quote_ref],
                    "native_metrics": {"status": "FINAL"},
                    "model_revision": "SYNTHETIC_TEST_ONLY",
                    "raw_offer_quotes": [excerpt], "rejected_quotes": 0,
                    "process_releases": [{"process_reaped": True}],
                    "oracle_visible_to_native": False,
                    "native_executed": True,
                })
                progress.append({
                    "state": "OFFER_RECORDED", "fixture": fixture_name,
                    "seed": seed, "arm": arm, "time_ns": 125,
                })
    write_lines(work / "RUN511_PROGRESS.jsonl", progress)
    update_rows(work, rows)
    return rows, progress


def update_rows(work, rows, repair_result=True):
    raw = work / "RUN511_OBSERVATIONS_RAW.jsonl"
    write_lines(raw, rows)
    if repair_result:
        keys = [[r["fixture"], r["arm"], r["seed"]] for r in rows]
        result = {
            "status": "RUN511_12_B2_NATIVE_OFFERS_STRUCTURALLY_VERIFIED_ONLY",
            "stage_id": "p00", "row_keys_sha256": audit.digest(audit.canonical(keys)),
            "raw_observations_sha256": audit.digest(raw.read_bytes()),
            "rows_verified": 12, "native_execution_performed": True,
            **audit.GATES,
        }
        write(work / "RUN511_STAGE_RESULT.json", result)


class Run513ReceiptPostflight(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.work = Path(self.tmp.name)
        self.rows, self.progress = make_stage(self.work)

    def test_exact_twelve_synthetic_rows_source_only(self):
        report, metric = audit.audit(self.work, 0)
        self.assertEqual(report["source_bound_rows"], 12)
        self.assertEqual(len(metric), 12)
        self.assertFalse(report["native_execution_independently_confirmed"])
        self.assertFalse(report["canonical_gate_pass"])
        self.assertEqual(report["step2_exit"], "UTILITY_FAIL")
        self.assertEqual({tuple((r["fixture"], r["arm"], r["seed"]))
                          for r in metric}, {tuple(x) for x in collector.plan(0)["row_keys"]})

    def test_quote_offset_tamper_fails_with_repaired_result_hash(self):
        self.rows[0]["evidence_refs"][0]["char_start"] = 1
        update_rows(self.work, self.rows)
        with self.assertRaisesRegex(ValueError, "QUOTE_EVIDENCE_OFFSET_OR_TEXT_DRIFT"):
            audit.audit(self.work, 0)

    def test_quote_source_id_tamper_fails(self):
        self.rows[0]["evidence_refs"][0]["source_id"] = "unknown"
        update_rows(self.work, self.rows)
        with self.assertRaisesRegex(ValueError, "QUOTE_UNKNOWN_SOURCE_ID"):
            audit.audit(self.work, 0)

    def test_quote_text_tamper_fails(self):
        self.rows[0]["quotes"][0]["text"] = "Budget 999 euros."
        update_rows(self.work, self.rows)
        with self.assertRaisesRegex(ValueError, "QUOTE_EVIDENCE_OFFSET_OR_TEXT_DRIFT"):
            audit.audit(self.work, 0)

    def test_slot_text_tamper_fails(self):
        self.rows[0]["source_slots"][1]["source_text"] = "swapped"
        update_rows(self.work, self.rows)
        with self.assertRaisesRegex(ValueError, "SOURCE_SLOT_RECORD_DRIFT"):
            audit.audit(self.work, 0)

    def test_missing_and_duplicate_rows_fail(self):
        for replacement in (self.rows[:-1], self.rows[:-1] + [copy.deepcopy(self.rows[0])]):
            update_rows(self.work, replacement)
            with self.assertRaises(ValueError):
                audit.audit(self.work, 0)

    def test_unreaped_process_fails(self):
        self.rows[0]["process_releases"][0]["process_reaped"] = False
        update_rows(self.work, self.rows)
        with self.assertRaisesRegex(ValueError, "NATIVE_ROW_LIFECYCLE_DRIFT"):
            audit.audit(self.work, 0)

    def test_progress_truncation_fails(self):
        write_lines(self.work / "RUN511_PROGRESS.jsonl", self.progress[:-1])
        with self.assertRaisesRegex(ValueError, "PROGRESS_EVENT_COUNT_DRIFT"):
            audit.audit(self.work, 0)

    def test_raw_sha_tamper_fails(self):
        result = audit.load_json(self.work / "RUN511_STAGE_RESULT.json")
        result["raw_observations_sha256"] = "0" * 64
        write(self.work / "RUN511_STAGE_RESULT.json", result)
        with self.assertRaisesRegex(ValueError, "STAGE_RESULT_OR_RAW_HASH_DRIFT"):
            audit.audit(self.work, 0)

    def test_preparation_source_ref_tamper_fails(self):
        prep_path = self.work / f"RUN511_PREP_{self.rows[0]['fixture']}_s{self.rows[0]['seed']}.json"
        prep = audit.load_json(prep_path)
        prep["prior_event_source_refs"][0]["source_id"] = "wrong"
        write(prep_path, prep)
        with self.assertRaisesRegex(ValueError, "PREPARATION_SOURCE_REF_DRIFT"):
            audit.audit(self.work, 0)

    def test_exclusive_output_refuses_overwrite(self):
        report, metric = audit.audit(self.work, 0)
        out = self.work / "RUN513_POSTFLIGHT.json"
        audit.write_exclusive(out, report)
        with self.assertRaises(FileExistsError):
            audit.write_exclusive(out, report)


if __name__ == "__main__":
    unittest.main()
