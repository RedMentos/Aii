#!/usr/bin/env python3
"""Read-only independent audit of the *original* Run13R GitHub Actions ZIP.

No native model invocation, scorer import, adapter writes, or gate promotion.
This script is independent of the frozen Run13R verdict implementation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import statistics
import sys
import zipfile

ORIGINAL_SHA256 = "d3d4ba03e2740e1dbe44a6b1c0b756c947a57cbfbc30a91293da6f0f3d76ee49"
ORIGINAL_HEAD = "aab856a28b8e864eddba37c03f945e9454804363"
ORIGINAL_FIXTURE = "a93322a5a30f9a9da5c391d172f8f6048cc6b9e2d617ab0349f4d148d278b77e"
MASTER_SHA256 = "1c9c77a4471a7f590f85240f74ed1fc26df7fbde88c3006724e2f93ca993ea4e"
REVISION = "120bf032c36dd1273de754669da040dba7ad4982"
EXPECTED_BLOBS = {
    "CANON": "218464b12a2d27d92524c751922fa8e1c3fb0ea7",
    "BJEPA": "b560d4e88fe457f381e89dfc5d6188a8ec3b306b",
    "LORA": "49a752879ae5d19391963742a0f042e740edb2cc",
    "LOSS": "acd40aeac9e286e93b40bda72c655c17725a522e",
    "TRAINER": "a31a18d9be0b1137a10304f24d3a241d720bd247",
    "ORIGINAL_RUN12C": "15597550100de6ca546b1b024fbc6597fc600839",
    "PROBE": "5d665c09909ae77eeb12bf038a053232371abcb8",
    "TEST": "ac3a38192de0c5dd6cde632746da4e191d196adf",
    "PREREG": "c979514672c01d74999868c307a46d3be8ba455d",
}
STAGES = ("SOURCE", "VENV", "TORCH", "DEPS", "PIP_CHECK", "SOFTWARE", "COMPILE", "DOWNLOAD", "NATIVE", "PRIVACY", "DIFF")
SEEDS = (271, 277)
ARMS = ("CE_0", "CONTRAST_2_5", "CONTRAST_12", "SHUFFLED_12")
CATEGORIES = ("train", "paraphrase", "near_miss_leak_proxy", "retention")
FACTS = (("Argen271", "amber", "Topaz"), ("Belora271", "teal", "Birch"),
         ("Corvyn271", "violet", "Falcon"), ("Deltis271", "silver", "Sable"))
RETENTION = (("What is the capital of Japan?", "Tokyo"),
             ("What is 7 times 3?", "21"),
             ("What is the opposite of wet?", "dry"),
             ("Which gas do humans inhale to survive?", "oxygen"))


def require(ok, why):
    if not ok:
        raise ValueError(why)


def close(a, b, where):
    require(isinstance(a, (int, float)) and not isinstance(a, bool)
            and isinstance(b, (int, float)) and not isinstance(b, bool)
            and math.isfinite(a) and math.isfinite(b)
            and math.isclose(a, b, abs_tol=1e-8, rel_tol=1e-9),
            "MISMATCH:" + where)


def expected_rows():
    rows = {k: [] for k in CATEGORIES}
    rows["retention"] = list(RETENTION)
    for i, (archive, color, answer) in enumerate(FACTS):
        rows["train"].append((f"In the invented {archive} archive, what is the {color} vault key?", answer))
        rows["paraphrase"].append((f"Which key opens the {color} vault of the {archive} archive?", answer))
        other = FACTS[(i + 1) % 4][0]
        rows["near_miss_leak_proxy"].append((f"In the invented {other} archive, what is the {color} vault key?", answer))
    return rows


def inspect_zip(path, expected_sha=ORIGINAL_SHA256):
    data = Path(path).read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    require(digest == expected_sha, "ORIGINAL_ZIP_SHA256_MISMATCH")
    with zipfile.ZipFile(path) as z:
        require(z.testzip() is None, "ZIP_CRC_RED")
        infos = z.infolist()
        names = [i.filename for i in infos]
        require(len(names) == len(set(names)) == 34, "ZIP_FILE_SET_RED")
        require(all(not i.is_dir() and i.file_size <= 2_000_000
                    and '/' not in i.filename and '\\' not in i.filename
                    and i.filename not in ('.', '..') for i in infos), "ZIP_PATH_OR_SIZE_RED")
        files = {name: z.read(name) for name in names}
    manifest = files["SHA256SUMS"].decode("utf-8").splitlines()
    listed = {}
    for line in manifest:
        m = re.fullmatch(r"([0-9a-f]{64})  \./([A-Za-z0-9_.-]+)", line)
        require(m is not None, "SHA256SUMS_FORMAT_RED")
        hash_, name = m.groups()
        require(name not in listed, "DUPLICATE_HASH_ENTRY")
        listed[name] = hash_
    require(set(listed) == set(files) - {"SHA256SUMS"} and len(listed) == 33,
            "SHA256SUMS_FILE_SET_RED")
    for name, hash_ in listed.items():
        require(hashlib.sha256(files[name]).hexdigest() == hash_, "INNER_SHA256_RED:" + name)
    require(files["HEAD.txt"].decode().strip() == ORIGINAL_HEAD, "SOURCE_HEAD_RED")
    for name, expected in EXPECTED_BLOBS.items():
        require(files[name + "_BLOB.txt"].decode().strip() == expected, "SOURCE_BLOB_RED:" + name)
    for stage in STAGES:
        require(files[stage + "_EXIT.txt"].decode().strip() == "0", "STAGE_RED:" + stage)
    require("Ran 18 tests" in files["SOFTWARE_RAW.log"].decode(), "TEST_COUNT_RED")
    require("\nOK\n" in files["SOFTWARE_RAW.log"].decode(), "TEST_RESULT_RED")
    require("PRIVACY_SCAN_CLEAN" in files["PRIVACY_RAW.log"].decode()
            or "CLEAN" in files["PRIVACY_RAW.log"].decode(), "PRIVACY_RED")
    r = json.loads(files["REPORT.json"])
    require(r["schema"] == "v13.bodyjepa.350m_scale_heldout_run13r.v1", "SCHEMA_RED")
    require(r["master_sha256"] == MASTER_SHA256 and r["model_revision"] == REVISION,
            "MODEL_PIN_RED")
    require(r["model_id"] == "LiquidAI/LFM2.5-350M", "MODEL_ID_RED")
    require(r["license_sha256"] == "4d28ca14dedc0b3d0fcc2b3339f0e79931faa33874f3d24f522183a8fc70068c", "LICENSE_PIN_RED")
    require(r["canon_blob"] == EXPECTED_BLOBS["CANON"] and
            r["body_jepa_blob"] == EXPECTED_BLOBS["BJEPA"] and
            r["contrastive_loss_blob"] == EXPECTED_BLOBS["LOSS"] and
            r["contrastive_trainer_blob"] == EXPECTED_BLOBS["TRAINER"] and
            r["original_run12c_runner_blob"] == EXPECTED_BLOBS["ORIGINAL_RUN12C"],
            "REPORT_SOURCE_BINDING_RED")
    require(r["fixture_sha256"] == ORIGINAL_FIXTURE, "FIXTURE_PIN_RED")
    require(r["seeds"] == list(SEEDS) and r["arms"] == list(ARMS), "COHORT_RED")
    require(r["completed_arms"] == 8 and r["failures"] == [], "INCOMPLETE_RED")
    require(r["weights"] == {"CE_0": 0, "CONTRAST_2_5": 2.5,
                             "CONTRAST_12": 12, "SHUFFLED_12": 12}, "DOSE_RED")
    require(r["config"]["max_steps"] == r["config"]["min_steps"] == 8,
            "STEPS_CONFIG_RED")
    require(r["config"]["checkpoint_resume"] is False, "RESUME_RED")
    require(r["evidence_class"] == "LINUX_FP32_TORCH_SYNTHETIC_HELDOUT", "EVIDENCE_CLASS_RED")
    for key, value in {"runtime_jepa_weight": 0, "age_authority": 0,
                       "b3_authority": 0, "utility_gate_pass": False,
                       "step2_utility_pass": False, "body_jepa_available": False,
                       "redmi_measured": False, "production_activation": False,
                       "whole_system_complete": False}.items():
        require(type(r[key]) is type(value) and r[key] == value, "NEGATIVE_GATE_RED:" + key)
    rows_expected = expected_rows()
    fixture_hash = hashlib.sha256(json.dumps(rows_expected, sort_keys=True,
                               separators=(",", ":")).encode()).hexdigest()
    require(fixture_hash == ORIGINAL_FIXTURE, "INDEPENDENT_FIXTURE_HASH_RED")
    require(set(r["results"]) == {str(s) for s in SEEDS}, "RESULT_SEED_RED")
    deltas = []
    exact_hits = {}
    baseline_first = None
    for seed in SEEDS:
        arms = r["results"][str(seed)]
        require(set(arms) == set(ARMS), "RESULT_ARM_RED")
        summaries = {}
        for arm in ARMS:
            obj = arms[arm]
            require(obj["exported_adapter"] is False, "ADAPTER_EXPORT_RED")
            metrics = obj["metrics"]
            require(metrics["steps"] == metrics["ema_updates"] == 8, "STEPS_RED")
            require(len(metrics["loss_history"]) == 8, "HISTORY_RED")
            require([x["step"] for x in metrics["loss_history"]] == list(range(1, 9)), "STEP_ORDER_RED")
            close(metrics["jepa_weight"], r["weights"][arm], "weight")
            require(metrics["jepa_target"] == ("shuffled" if arm == "SHUFFLED_12" else "ema"),
                    "TARGET_ARM_RED")
            require(set(obj["rows"]) == set(obj["baseline_rows"]) == set(CATEGORIES),
                    "CATEGORY_SET_RED")
            for kind in CATEGORIES:
                for base, key in ((False, "rows"), (True, "baseline_rows")):
                    vals = obj[key][kind]
                    require(len(vals) == 4, "ROW_COUNT_RED")
                    for actual, (q, answer) in zip(vals, rows_expected[kind]):
                        require(actual["q"] == q and actual["answer"] == answer,
                                "FIXTURE_ROW_RED")
                        require(type(actual["nll"]) in (float, int)
                                and math.isfinite(actual["nll"]) and actual["nll"] >= 0,
                                "NLL_NONFINITE_RED")
                    close(statistics.mean(v["nll"] for v in vals),
                          obj["baseline" if base else "summary"][kind], "NLL_MEAN")
            if baseline_first is None:
                baseline_first = obj["baseline_rows"]
            else:
                require(obj["baseline_rows"] == baseline_first, "BASELINE_DRIFT_RED")
            generated = obj["paraphrase_generated"]
            require(len(generated) == 4, "GREEDY_COUNT_RED")
            hit_count = 0
            for item, (q, answer) in zip(generated, rows_expected["paraphrase"]):
                require(item["q"] == q and item["expected"] == answer,
                        "GREEDY_FIXTURE_RED")
                require(type(item["text"]) is str and len(item["text"]) <= 256,
                        "GREEDY_OUTPUT_RED")
                # The observed original cohort uses exact one-token answers for hits.
                exact = item["text"].strip().casefold() == answer.casefold()
                require(item["answer_hit"] is exact, "GREEDY_HIT_REPLAY_RED")
                hit_count += exact
            require(obj["paraphrase_greedy_hits"] == hit_count, "GREEDY_TOTAL_RED")
            exact_hits[f"{seed}/{arm}"] = hit_count
            summaries[arm] = obj["summary"]
        ce, moderate, high, shuffled = (summaries[a] for a in ARMS)
        deltas.append({
            "seed": seed,
            "high_minus_ce_paraphrase": high["paraphrase"] - ce["paraphrase"],
            "high_minus_shuffled_paraphrase": high["paraphrase"] - shuffled["paraphrase"],
            "moderate_minus_ce_paraphrase": moderate["paraphrase"] - ce["paraphrase"],
            "high_minus_ce_near_miss": high["near_miss_leak_proxy"] - ce["near_miss_leak_proxy"],
            "high_minus_ce_retention": high["retention"] - ce["retention"],
        })
    for calc, reported in zip(deltas, r["per_seed_deltas"]):
        require(set(calc) == set(reported), "DELTA_KEYS_RED")
        for key in calc:
            if key == "seed":
                require(calc[key] == reported[key], "DELTA_SEED_RED")
            else:
                close(calc[key], reported[key], "DELTA:" + key)
    means = {k: statistics.mean(x[k] for x in deltas) for k in deltas[0] if k != "seed"}
    for key, val in means.items():
        close(val, r["mean_deltas"][key], "MEAN:" + key)
    wins = sum(x["high_minus_ce_paraphrase"] <= -.05 and
               x["high_minus_shuffled_paraphrase"] <= -.05 for x in deltas)
    signal = wins == 2 and means["high_minus_ce_near_miss"] >= -.05 and means["high_minus_ce_retention"] <= .05
    hurt = means["high_minus_ce_paraphrase"] >= .05 or means["high_minus_ce_retention"] > .05
    status = "BOUNDED_SYNTHETIC_SCALE_SIGNAL_NOT_UTILITY_GATE" if signal else (
        "DIAGNOSTIC_HURT" if hurt else "DIAGNOSTIC_NO_ATTRIBUTABLE_GAIN")
    require(r["seed_wins"] == wins and r["status"] == status, "VERDICT_REPLAY_RED")
    return {"schema": "v13.run13s.independent_raw_review.v1",
            "source_zip_sha256": digest, "original_artifact_id": 12996160234,
            "source_head": ORIGINAL_HEAD, "manifest_hashes_verified": len(listed),
            "stage_exits_zero": len(STAGES), "cohort_arms_verified": 8,
            "row_nll_values_verified": 8 * 4 * 4 * 2,
            "reported_status_replayed": status, "seed_wins": wins,
            "mean_deltas": means, "per_seed_deltas": deltas,
            "greedy_exact_hits": exact_hits,
            "evidence_class": "INDEPENDENT_REPLAY_OF_ORIGINAL_LINUX_NATIVE_SYNTHETIC_RAW",
            "native_executed_by_this_audit": False, "utility_gate_pass": False,
            "body_jepa_available": False, "redmi_measured": False,
            "whole_system_complete": False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("zip", type=Path)
    parser.add_argument("--expected-sha", default=ORIGINAL_SHA256)
    args = parser.parse_args(argv)
    try:
        report = inspect_zip(args.zip, args.expected_sha)
    except (OSError, ValueError, KeyError, TypeError, zipfile.BadZipFile, json.JSONDecodeError) as e:
        print(f"RUN13S_RAW_REVIEW_RED: {type(e).__name__}: {e}", file=sys.stderr)
        return 1
    print(json.dumps(report, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())