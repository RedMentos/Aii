#!/usr/bin/env python3
"""Run12D independent read-only audit of original Run12C native Actions ZIP.

Never executes a model, changes a preregistered scorer, imports the trainer,
promotes gates, or treats GitHub Actions success as measured utility.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import statistics
import zipfile

SCHEMA = "v13.bodyjepa.350m_contrastive_disjoint_nll.v1"
LAUNCH_HEAD = "35c163f19f3ccdc1e8ebed1df5821c679d96a13a"
SEEDS = ("227", "229", "233")
ARMS = ("CE", "COS_EMA", "CONTRAST_EMA", "CONTRAST_SHUFFLED")
CATEGORIES = ("train", "paraphrase", "near_miss_leak_proxy", "retention")
PINS = {
    "CANON_BLOB.txt": "218464b12a2d27d92524c751922fa8e1c3fb0ea7",
    "BJEPA_BLOB.txt": "b560d4e88fe457f381e89dfc5d6188a8ec3b306b",
    "LORA_BLOB.txt": "49a752879ae5d19391963742a0f042e740edb2cc",
    "LOSS_BLOB.txt": "acd40aeac9e286e93b40bda72c655c17725a522e",
    "TRAINER_BLOB.txt": "a31a18d9be0b1137a10304f24d3a241d720bd247",
    "ORIGINAL_RUN11P_BLOB.txt": "af685a22ddd4ff6412643a8849a1f00bf2112487",
    "PROBE_BLOB.txt": "15597550100de6ca546b1b024fbc6597fc600839",
}
STAGES = ("SOURCE", "VENV", "TORCH", "DEPS", "PIP_CHECK", "SOFTWARE",
          "COMPILE", "DOWNLOAD", "NATIVE", "PRIVACY", "DIFF")
MASTER_SHA256 = "1c9c77a4471a7f590f85240f74ed1fc26df7fbde88c3006724e2f93ca993ea4e"
REVISION = "120bf032c36dd1273de754669da040dba7ad4982"
FIXTURE_SHA256 = "848021441551627c47107c7b1298d338ab674d8983ff10af4848cf33adf77748"
LICENSE_SHA256 = "4d28ca14dedc0b3d0fcc2b3339f0e79931faa33874f3d24f522183a8fc70068c"
MAX_ZIP_BYTES = 64 * 1024 * 1024
MAX_MEMBERS = 100


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def finite_nll(v):
    return type(v) in (float, int) and math.isfinite(v) and v >= 0


def unique_pairs(pairs):
    out = {}
    for key, value in pairs:
        require(key not in out, "DUPLICATE_JSON_KEY")
        out[key] = value
    return out


def strict_json(raw):
    return json.loads(raw, object_pairs_hook=unique_pairs,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError("NONFINITE_JSON")))


def read_original_zip(path, expected_sha256):
    """Verify original ZIP bytes, names, CRC and all inner SHA256 before parsing."""
    path = Path(path)
    require(path.is_file() and not path.is_symlink(), "ORIGINAL_ZIP_MISSING_OR_SYMLINK")
    require(path.stat().st_size <= MAX_ZIP_BYTES, "ORIGINAL_ZIP_OVERSIZE")
    data = path.read_bytes()
    observed = hashlib.sha256(data).hexdigest()
    require(observed == expected_sha256, "ORIGINAL_ZIP_SHA256_MISMATCH")
    with zipfile.ZipFile(path) as z:
        infos = z.infolist()
        names = [i.filename for i in infos]
        require(1 <= len(names) <= MAX_MEMBERS and len(names) == len(set(names)),
                "ZIP_DUPLICATE_OR_MEMBER_COUNT")
        require(all(n and not n.startswith("/") and not n.startswith("../")
                    and ".." not in Path(n).parts and "\\" not in n
                    and n == Path(n).name for n in names), "ZIP_PATH_UNSAFE")
        require(all(not (i.flag_bits & 1) and not ((i.external_attr >> 16) & 0o170000) == 0o120000
                    for i in infos), "ZIP_ENCRYPTED_OR_SYMLINK")
        require(sum(i.file_size for i in infos) <= MAX_ZIP_BYTES, "ZIP_UNCOMPRESSED_OVERSIZE")
        require(z.testzip() is None, "ZIP_CRC_RED")
        require("SHA256SUMS" in names, "INNER_HASH_MANIFEST_MISSING")
        raw = {n: z.read(n) for n in names}
    lines = raw["SHA256SUMS"].decode("utf-8").splitlines()
    listed = {}
    for line in lines:
        fields = line.split(maxsplit=1)
        require(len(fields) == 2 and len(fields[0]) == 64, "INNER_HASH_ROW_INVALID")
        name = fields[1].removeprefix("*").removeprefix("./")
        require(name not in listed and name in raw and name != "SHA256SUMS",
                "INNER_HASH_UNLISTED_OR_DUPLICATE")
        listed[name] = fields[0]
    require(set(listed) == set(raw) - {"SHA256SUMS"}, "INNER_HASH_COVERAGE_RED")
    for name, sha in listed.items():
        require(hashlib.sha256(raw[name]).hexdigest() == sha, "INNER_SHA256_MISMATCH:" + name)
    return observed, raw


def mean_rows(arm, kind):
    rows = arm["rows"] if kind == "after" else arm["baseline_rows"]
    summary = arm["summary"] if kind == "after" else arm["baseline"]
    require(set(rows) == set(CATEGORIES) and set(summary) == set(CATEGORIES),
            "NLL_CATEGORY_SET_RED")
    for category in CATEGORIES:
        group = rows[category]
        require(type(group) is list and len(group) == 4, "NLL_ROW_COUNT_RED")
        seen = set()
        for row in group:
            require(type(row) is dict and set(row) == {"q", "answer", "nll"},
                    "NLL_ROW_SCHEMA_RED")
            require(type(row["q"]) is str and bool(row["q"].strip())
                    and type(row["answer"]) is str and bool(row["answer"].strip())
                    and row["q"] not in seen and finite_nll(row["nll"]),
                    "NLL_ROW_VALUE_RED")
            seen.add(row["q"])
        expected = statistics.mean(row["nll"] for row in group)
        require(finite_nll(summary[category])
                and math.isclose(summary[category], expected, rel_tol=1e-10, abs_tol=1e-10),
                "NLL_MEAN_MISMATCH:" + category)


def independent_verdict(results):
    """Independent replay of the fixed preregistered threshold, no native utility gate."""
    require(type(results) is dict and set(results) == set(SEEDS), "INCOMPLETE_SEEDS")
    deltas = []
    for seed in SEEDS:
        arms = results[seed]
        require(type(arms) is dict and set(arms) == set(ARMS), "INCOMPLETE_ARMS")
        ce, cosine, contrast, wrong = (arms[k]["summary"] for k in ARMS)
        deltas.append({
            "seed": int(seed),
            "paraphrase_contrast_minus_ce": contrast["paraphrase"] - ce["paraphrase"],
            "paraphrase_contrast_minus_cosine": contrast["paraphrase"] - cosine["paraphrase"],
            "paraphrase_contrast_minus_shuffled": contrast["paraphrase"] - wrong["paraphrase"],
            "near_miss_contrast_minus_ce": contrast["near_miss_leak_proxy"] - ce["near_miss_leak_proxy"],
            "retention_contrast_minus_ce": contrast["retention"] - ce["retention"],
        })
    means = {k: statistics.mean(d[k] for d in deltas)
             for k in deltas[0] if k != "seed"}
    wins = sum(d["paraphrase_contrast_minus_ce"] <= -0.05
               and d["paraphrase_contrast_minus_cosine"] <= -0.05 for d in deltas)
    signal = (wins >= 2 and means["paraphrase_contrast_minus_ce"] <= -0.05
              and means["paraphrase_contrast_minus_cosine"] <= -0.05
              and means["near_miss_contrast_minus_ce"] >= -0.05
              and means["retention_contrast_minus_ce"] <= 0.05)
    hurt = (means["paraphrase_contrast_minus_ce"] >= 0.05
            or means["retention_contrast_minus_ce"] > 0.05)
    status = ("BOUNDED_CONTRASTIVE_NLL_SIGNAL_NOT_UTILITY_GATE" if signal
              else "DIAGNOSTIC_HURT" if hurt else "DIAGNOSTIC_NO_ATTRIBUTABLE_GAIN")
    return {"status": status, "seed_wins": wins, "per_seed_deltas": deltas,
            "mean_deltas": means, "utility_gate_pass": False}


def compare_deltas(a, b):
    require(type(a) is dict and set(a) == set(b), "DELTA_KEYS_RED")
    for k, v in b.items():
        require(finite_nll(abs(a[k])) and math.isclose(a[k], v, rel_tol=1e-10, abs_tol=1e-10),
                "DELTA_MISMATCH:" + k)


def verify_report(d):
    require(type(d) is dict and d.get("schema") == SCHEMA, "REPORT_SCHEMA_RED")
    for key, want in (("model_revision", REVISION), ("master_sha256", MASTER_SHA256),
                      ("fixture_sha256", FIXTURE_SHA256), ("license_sha256", LICENSE_SHA256),
                      ("body_jepa_source_git_blob", PINS["BJEPA_BLOB.txt"]),
                      ("contrastive_trainer_source_git_blob", PINS["TRAINER_BLOB.txt"])):
        require(d.get(key) == want, "REPORT_PIN_RED:" + key)
    require(d.get("model_id") == "LiquidAI/LFM2.5-350M", "MODEL_ID_RED")
    require(d.get("seeds") == [227, 229, 233] and d.get("arms") == list(ARMS),
            "COHORT_REGISTRATION_RED")
    cfg = d.get("config", {})
    require(cfg.get("rank") == 2 and cfg.get("alpha") == 4
            and cfg.get("lr") == 0.0005 and cfg.get("max_steps") == cfg.get("min_steps") == 8
            and cfg.get("targets") == ["w1", "w2", "w3"]
            and cfg.get("jepa_ema_decay") == 0.9
            and cfg.get("jepa_target_eval") is True
            and cfg.get("contrastive_temperature") == 0.1
            and cfg.get("checkpoint_resume") is False, "CONFIG_PIN_RED")
    require(d.get("completed_arms") == 12 and d.get("failures") == [],
            "INCOMPLETE_OR_FAILED_NATIVE_ARMS")
    for k, expected in (("runtime_jepa_weight", 0), ("age_authority", 0),
                        ("redmi_measured", False), ("step2_utility_pass", False),
                        ("body_jepa_available", False), ("production_activation", False),
                        ("whole_system_complete", False), ("b1_b2_utility_proven", False)):
        require(d.get(k) is expected or (type(expected) is int and d.get(k) == expected),
                "PROMOTION_OR_MISSING_GATE:" + k)
    results = d.get("results")
    require(type(results) is dict and set(results) == set(SEEDS), "INCOMPLETE_SEEDS")
    for seed in SEEDS:
        arms = results[seed]
        require(type(arms) is dict and set(arms) == set(ARMS), "INCOMPLETE_ARMS")
        for arm in ARMS:
            entry = arms[arm]
            require(type(entry) is dict and entry.get("exported_adapter") is False,
                    "ADAPTER_EXPORT_RED")
            metrics = entry.get("metrics", {})
            require(metrics.get("steps") == 8
                    and metrics.get("jepa_weight") == (0.0 if arm == "CE" else 0.25)
                    and metrics.get("jepa_target") == ("shuffled" if arm == "CONTRAST_SHUFFLED" else "ema"),
                    "ARM_TRAINING_CONFIG_RED")
            hist = metrics.get("loss_history")
            require(type(hist) is list and len(hist) == 8
                    and [h.get("step") for h in hist] == list(range(1, 9)),
                    "TRAINING_HISTORY_RED")
            require(all((h.get("jepa") is None) == (arm == "CE") for h in hist),
                    "JEPA_LOSS_ARM_RED")
            require(type(entry.get("elapsed_s")) in (float, int)
                    and math.isfinite(entry["elapsed_s"]) and entry["elapsed_s"] >= 0,
                    "ELAPSED_RED")
            mean_rows(entry, "after")
            mean_rows(entry, "baseline")
    expected = independent_verdict(results)
    require(d.get("status") == expected["status"]
            and d.get("seed_wins") == expected["seed_wins"]
            and d.get("utility_gate_pass") is False, "VERDICT_REPLAY_RED")
    compare_deltas(d.get("mean_deltas"), expected["mean_deltas"])
    actual = d.get("per_seed_deltas")
    require(type(actual) is list and len(actual) == 3, "SEED_DELTAS_RED")
    for row, want in zip(actual, expected["per_seed_deltas"]):
        require(row.get("seed") == want["seed"], "SEED_DELTA_ORDER_RED")
        compare_deltas({k: v for k, v in row.items() if k != "seed"},
                       {k: v for k, v in want.items() if k != "seed"})
    return expected


def audit(path, expected_zip_sha256, expected_head=LAUNCH_HEAD):
    observed, raw = read_original_zip(path, expected_zip_sha256)
    require(raw.get("HEAD.txt", b"").decode("utf-8").strip() == expected_head,
            "LAUNCH_HEAD_RED")
    stages = {stage: raw.get(stage + "_EXIT.txt", b"MISSING").decode("utf-8").strip()
              for stage in STAGES}
    bad = [stage for stage, value in stages.items() if value != "0"]
    pins_bad = [name for name, want in PINS.items()
                if raw.get(name, b"").decode("utf-8").strip() != want]
    outcome = {
        "schema": "V13_RUN12D_ORIGINAL_RAW_INDEPENDENT_AUDIT_V1",
        "original_zip_sha256": observed, "original_head": expected_head,
        "inner_sha256_verified": len(raw) - 1, "crc": "PASS",
        "stage_exits": stages, "bad_stages": bad, "bad_pins": pins_bad,
        "raw_preserved": True, "native_report_consistent": False,
        "utility_gate_pass": False, "production_activation": False,
        "redmi_measured": False, "whole_system_complete": False,
    }
    if bad or pins_bad or "REPORT.json" not in raw:
        outcome["status"] = "ORIGINAL_RED_OR_PARTIAL_PRESERVED"
        return outcome
    report = strict_json(raw["REPORT.json"])
    replay = verify_report(report)
    outcome.update({"status": "RAW_REPORT_CONSISTENT_NOT_UTILITY_GATE",
                    "native_report_consistent": True, "diagnostic": replay})
    return outcome


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--zip", required=True, type=Path)
    parser.add_argument("--expected-zip-sha256", required=True)
    parser.add_argument("--expected-head", default=LAUNCH_HEAD)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)
    require(len(args.expected_zip_sha256) == 64, "EXPECTED_SHA256_REQUIRED")
    result = audit(args.zip, args.expected_zip_sha256, args.expected_head)
    data = json.dumps(result, sort_keys=True, indent=2) + "\n"
    if args.out is not None:
        require(not args.out.exists() and not args.out.is_symlink(), "REFUSE_AUDIT_OVERWRITE")
        args.out.write_text(data)
    print(data, end="")
    return 0 if result["native_report_consistent"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
