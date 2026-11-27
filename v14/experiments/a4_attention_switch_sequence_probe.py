"""Source-bound, shadow-only evaluation of A4 score sequences before attention switches.

The A4 score vector is a control signal, NOT an attended-speaker posterior or AAD
probability. This probe asks only whether causal A4 score sequences rank a later
attention-state transition above stable windows. It never trains, persists, changes
A4 policy, or grants learning/action authority.
"""
from __future__ import annotations

from collections import defaultdict, deque
import argparse
import json
import math
from pathlib import Path
import random
import re
from typing import Any

SCHEMA = "v14.a4-attention-switch-sequence-probe/1"
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_GAIN_KEYS = frozenset({"perceptual", "callosum", "workspace", "focal", "action"})
_STATES = frozenset({"STATE_A", "STATE_B"})
_EVIDENCE_CLASSES = frozenset({"SYNTHETIC_FIXTURE", "OBSERVED_LOCAL"})
_LABEL_KINDS = frozenset({"TARGET_CUE", "EEG_DECODER_ESTIMATE", "OBSERVED_ATTENDED_STATE"})


def _finite(value: Any) -> bool:
    return type(value) in (int, float) and math.isfinite(float(value))


def _source_ref(value: Any, *, modalities: set[str]) -> dict:
    if type(value) is not dict:
        raise ValueError("source_ref must be an object")
    if (type(value.get("source_id")) is not str or not value["source_id"].strip()
            or type(value.get("sha256")) is not str or not _SHA256.fullmatch(value["sha256"])
            or type(value.get("char_start")) is not int or type(value.get("char_end")) is not int
            or value["char_start"] < 0 or value["char_end"] < value["char_start"]
            or value.get("modality") not in modalities):
        raise ValueError("source_ref identity, hash or modality is invalid")
    return value


def _score_vector(value: Any) -> dict:
    if type(value) is not dict or value.get("kind") != "A4_CONTROL_SCORE_NOT_AAD":
        raise ValueError("expected A4_CONTROL_SCORE_NOT_AAD score vector")
    if value.get("truth_authority") != 0:
        raise PermissionError("A4 scores cannot carry truth authority")
    if any(not _finite(value.get(k)) or not 0 <= float(value[k]) <= 1
           for k in ("salience", "caution")):
        raise ValueError("A4 salience/caution must be finite in [0,1]")
    gains = value.get("gains")
    if type(gains) is not dict or set(gains) != _GAIN_KEYS:
        raise ValueError("A4 gain vector is incomplete")
    if any(not _finite(gains[k]) or not 0 <= float(gains[k]) <= 1 for k in _GAIN_KEYS):
        raise ValueError("A4 gains must be finite in [0,1]")
    if type(value.get("interrupt")) is not bool:
        raise ValueError("A4 interrupt must be boolean")
    reason = value.get("interrupt_reason")
    if reason is not None and type(reason) is not str:
        raise ValueError("A4 interrupt_reason must be text or null")
    return {
        "salience": float(value["salience"]),
        "caution": float(value["caution"]),
        "interrupt": value["interrupt"],
        "focal_gain": float(gains["focal"]),
        "callosum_gain": float(gains["callosum"]),
        "action_gain": float(gains["action"]),
    }


def _contains_forbidden(value: Any) -> bool:
    forbidden = {"pcm", "raw_pcm", "waveform", "samples", "transcript", "asr_text"}
    if type(value) is dict:
        return any(key in forbidden or _contains_forbidden(child) for key, child in value.items())
    if type(value) in (list, tuple):
        return any(_contains_forbidden(child) for child in value)
    return False


def _validate_record(record: Any) -> dict:
    if type(record) is not dict:
        raise ValueError("record must be an object")
    evidence_class = record.get("evidence_class")
    if type(evidence_class) is not str or evidence_class not in _EVIDENCE_CLASSES:
        raise ValueError("evidence_class must be SYNTHETIC_FIXTURE or OBSERVED_LOCAL")
    receipt = record.get("a4_receipt")
    if type(receipt) is not dict or receipt.get("schema_version") != "1.0":
        raise ValueError("expected schema-version 1.0 A4AttentionReceipt")
    if receipt.get("producer_component") != "A4_AUDIO":
        raise ValueError("expected A4_AUDIO producer")
    for key in ("packet_id", "event_id", "brain_generation_id", "percept_packet_id"):
        if type(receipt.get(key)) is not str or not receipt[key].strip():
            raise ValueError("A4 receipt identity is incomplete: " + key)
    if receipt.get("finality") != "FINAL":
        raise ValueError("sequence evaluation requires FINAL A4 receipts")
    start_ms, end_ms = receipt.get("start_ms"), receipt.get("end_ms")
    if type(start_ms) is not int or type(end_ms) is not int or not 0 <= start_ms < end_ms:
        raise ValueError("A4 receipt interval is invalid")
    if receipt.get("learning_authority") is not False or receipt.get("action_authority") is not False:
        raise PermissionError("A4 receipt cannot grant learning or action authority")
    if receipt.get("truth_authority") != 0:
        raise PermissionError("A4 receipt cannot grant truth authority")
    audio_ref = _source_ref(receipt.get("source_ref"), modalities={"audio", "audio/pcm16le"})
    provenance = receipt.get("provenance")
    if type(provenance) is not list or audio_ref not in provenance:
        raise ValueError("A4 receipt provenance does not bind the audio source")
    scores = _score_vector(receipt.get("score_vector"))

    outcome = record.get("outcome")
    if type(outcome) is not dict:
        raise ValueError("separate attention outcome is required")
    label_kind = outcome.get("label_kind")
    if type(label_kind) is not str or label_kind not in _LABEL_KINDS:
        raise ValueError("label_kind must distinguish target cue from observed attention")
    expected_label_modality = {
        "TARGET_CUE": "attention/target-cue",
        "EEG_DECODER_ESTIMATE": "attention/eeg-decoder-estimate",
        "OBSERVED_ATTENDED_STATE": "attention/attended-state",
    }[label_kind]
    outcome_ref = _source_ref(outcome.get("source_ref"), modalities={expected_label_modality})
    timebase_ref = _source_ref(outcome.get("timebase_source_ref"), modalities={"audio", "audio/pcm16le"})
    if timebase_ref != audio_ref:
        raise ValueError("attention outcome timebase must bind the exact A4 audio source")
    if outcome.get("brain_generation_id") != receipt["brain_generation_id"]:
        raise ValueError("attention outcome generation does not match A4 receipt")
    if (outcome_ref["source_id"] == audio_ref["source_id"]
            or outcome_ref["sha256"] == audio_ref["sha256"]):
        raise ValueError("attention outcome must have an independent source binding")
    if outcome.get("learning_authority") is not False or outcome.get("action_authority") is not False:
        raise PermissionError("attention outcome cannot grant learning or action authority")
    session_id, trial_id, goal_id = (outcome.get(k) for k in ("session_id", "trial_id", "goal_id"))
    if not all(type(v) is str and v.strip() for v in (session_id, trial_id, goal_id)):
        raise ValueError("session/trial/goal identity is incomplete")
    previous_state, next_state = outcome.get("state_before"), outcome.get("state_after")
    if (type(previous_state) is not str or previous_state not in _STATES
            or type(next_state) is not str or next_state not in _STATES):
        raise ValueError("attention states must be STATE_A or STATE_B")
    observed_at = outcome.get("observed_at_ms")
    if type(observed_at) is not int or observed_at < end_ms:
        raise ValueError("attention outcome must be observed after the A4 window")
    switch_at = outcome.get("next_switch_at_ms")
    if previous_state == next_state:
        if switch_at is not None:
            raise ValueError("stable state cannot carry next_switch_at_ms")
        label = 0
    else:
        if type(switch_at) is not int or switch_at < end_ms or switch_at > observed_at:
            raise ValueError("state transition requires a bounded future switch timestamp")
        label = 1
    if _contains_forbidden(receipt) or _contains_forbidden(outcome):
        raise ValueError("raw audio/transcript content is not accepted")
    return {
        "evidence_class": evidence_class,
        "label_kind": label_kind,
        "session_id": session_id,
        "trial_id": trial_id,
        "goal_id": goal_id,
        "brain_generation_id": receipt["brain_generation_id"],
        "packet_id": receipt["packet_id"],
        "event_id": receipt["event_id"],
        "percept_packet_id": receipt["percept_packet_id"],
        "start_ms": start_ms,
        "end_ms": end_ms,
        "observed_at_ms": observed_at,
        "label": label,
        "switch_at_ms": switch_at,
        "scores": scores,
    }


def _auc(scores: list[float], labels: list[int]) -> float:
    positives = sum(labels)
    negatives = len(labels) - positives
    if positives == 0 or negatives == 0:
        raise ValueError("each session/goal stratum needs both switch and stable examples")
    ordered = sorted(zip(scores, labels), key=lambda item: item[0])
    rank_sum = 0.0
    index = 0
    while index < len(ordered):
        end = index + 1
        while end < len(ordered) and ordered[end][0] == ordered[index][0]:
            end += 1
        average_rank = ((index + 1) + end) / 2.0
        rank_sum += average_rank * sum(label for _, label in ordered[index:end])
        index = end
    return (rank_sum - positives * (positives + 1) / 2) / (positives * negatives)


def _features_by_sequence(rows: list[dict], *, history_ms: int) -> list[dict]:
    grouped: dict[tuple[str, str, str, str], list[dict]] = defaultdict(list)
    for row in rows:
        grouped[(row["session_id"], row["trial_id"], row["goal_id"], row["brain_generation_id"])].append(row)
    output = []
    for group in grouped.values():
        group.sort(key=lambda r: (r["start_ms"], r["end_ms"], r["packet_id"]))
        history: deque[dict] = deque()
        previous_start = -1
        for row in group:
            if row["start_ms"] <= previous_start:
                raise ValueError("A4 sequence windows must have strictly increasing starts")
            previous_start = row["start_ms"]
            while history and history[0]["end_ms"] < row["end_ms"] - history_ms:
                history.popleft()
            current = row["scores"]
            prior = list(history)
            sequence = prior + [row]
            saliences = [r["scores"]["salience"] for r in sequence]
            cautions = [r["scores"]["caution"] for r in sequence]
            focal = [r["scores"]["focal_gain"] for r in sequence]
            callosum = [r["scores"]["callosum_gain"] for r in sequence]
            interrupts = [r["scores"]["interrupt"] for r in sequence]
            output.append({
                **row,
                "features": {
                    "salience_now": current["salience"],
                    "caution_now": current["caution"],
                    "interrupt_now": float(current["interrupt"]),
                    "salience_max_history": max(saliences),
                    "caution_mean_history": sum(cautions) / len(cautions),
                    "interrupt_count_history": float(sum(interrupts)),
                    "focal_gain_delta": current["focal_gain"] - (focal[-2] if len(focal) > 1 else current["focal_gain"]),
                    "callosum_gain_delta": current["callosum_gain"] - (callosum[-2] if len(callosum) > 1 else current["callosum_gain"]),
                    "action_gain_delta": current["action_gain"] - (sequence[-2]["scores"]["action_gain"] if len(sequence) > 1 else current["action_gain"]),
                },
            })
            history.append(row)
    return output


def evaluate(records: list[dict], *, horizon_ms: int = 5000, history_ms: int = 5000,
             permutations: int = 200, seed: int = 17) -> dict:
    """Evaluate causal A4 score sequences against separate later state labels.

    Samples are grouped by session × trial × goal. Each stratum must contain both
    a transition and a stable example. Metrics are macro-averaged over strata;
    labels are permuted only within a stratum. This is an evaluation probe, not a
    calibrated classifier or a production attention policy.
    """
    if type(records) is not list or not records:
        raise ValueError("records must be a non-empty list")
    for name, value, lower, upper in (("horizon_ms", horizon_ms, 100, 60000),
                                      ("history_ms", history_ms, 100, 60000),
                                      ("permutations", permutations, 1, 10000)):
        if type(value) is not int or not lower <= value <= upper:
            raise ValueError(name + " is out of range")
    rows = [_validate_record(record) for record in records]
    classes = {row["evidence_class"] for row in rows}
    label_kinds = {row["label_kind"] for row in rows}
    if len(classes) != 1 or len(label_kinds) != 1:
        raise ValueError("do not mix evidence classes or label kinds")
    for row in rows:
        if row["observed_at_ms"] > row["end_ms"] + horizon_ms:
            raise ValueError("attention outcome lies outside the configured horizon")
        if row["switch_at_ms"] is not None and row["switch_at_ms"] > row["end_ms"] + horizon_ms:
            raise ValueError("attention switch lies outside the configured horizon")
        if row["label"] == 0 and row["observed_at_ms"] < row["end_ms"] + horizon_ms:
            raise ValueError("stable label must observe the complete future horizon; otherwise it is censored")
    for key in ("packet_id", "event_id", "percept_packet_id"):
        values = [row[key] for row in rows]
        if len(set(values)) != len(values):
            raise ValueError("duplicate A4 receipt identity: " + key)

    enriched = _features_by_sequence(rows, history_ms=history_ms)
    strata: dict[tuple[str, str], list[dict]] = defaultdict(list)
    trial_groups: dict[tuple[str, str, str, str], list[dict]] = defaultdict(list)
    sessions = set()
    goals = set()
    for row in enriched:
        strata[(row["session_id"], row["goal_id"])].append(row)
        trial_groups[(row["session_id"], row["trial_id"], row["goal_id"], row["brain_generation_id"])].append(row)
        sessions.add(row["session_id"])
        goals.add(row["goal_id"])
    if len(sessions) < 2:
        raise ValueError("at least two disjoint sessions are required")
    if len(goals) < 2:
        raise ValueError("at least two goal strata are required")
    for key, group in strata.items():
        if len({row["label"] for row in group}) != 2:
            raise ValueError("every session × goal stratum needs switch and stable labels: " + repr(key))
    for key, group in trial_groups.items():
        if len({row["label"] for row in group}) != 2:
            raise ValueError("every session × trial × goal sequence needs switch and stable labels: " + repr(key))

    feature_names = tuple(enriched[0]["features"].keys())
    by_feature: dict[str, list[float]] = {name: [] for name in feature_names}
    stratum_rows = []
    for key, group in sorted(strata.items()):
        labels = [row["label"] for row in group]
        metrics = {}
        for name in feature_names:
            score_values = [float(row["features"][name]) for row in group]
            auc = _auc(score_values, labels)
            by_feature[name].append(auc)
            metrics[name] = round(auc, 6)
        stratum_rows.append({"session_id": key[0], "goal_id": key[1], "count": len(group),
                             "switches": sum(labels), "stable": len(labels)-sum(labels),
                             "auc": metrics})

    observed = {name: sum(values) / len(values) for name, values in by_feature.items()}
    rng = random.Random(seed)
    shuffled: dict[str, list[float]] = {name: [] for name in feature_names}
    for _ in range(permutations):
        trial_auc = {name: [] for name in feature_names}
        shuffled_by_packet = {}
        for group in trial_groups.values():
            labels = [row["label"] for row in group]
            shuffled_labels = list(labels)
            rng.shuffle(shuffled_labels)
            for row, label in zip(group, shuffled_labels):
                shuffled_by_packet[row["packet_id"]] = label
        for group in strata.values():
            labels = [shuffled_by_packet[row["packet_id"]] for row in group]
            for name in feature_names:
                scores = [float(row["features"][name]) for row in group]
                trial_auc[name].append(_auc(scores, labels))
        for name in feature_names:
            shuffled[name].append(sum(trial_auc[name]) / len(trial_auc[name]))

    controls = {}
    for name in feature_names:
        null = shuffled[name]
        controls[name] = {
            "zero_score_auc": 0.5,
            "shuffled_mean_auc": round(sum(null) / len(null), 6),
            "shuffled_p95_auc": round(sorted(null)[min(len(null)-1, math.ceil(0.95*len(null))-1)], 6),
            "permutation_p": round((1 + sum(value >= observed[name] for value in null)) / (permutations + 1), 6),
        }

    switch_leads = [row["switch_at_ms"] - row["end_ms"] for row in rows
                    if row["switch_at_ms"] is not None]
    interrupt_tp = sum(1 for row in rows if row["label"] == 1 and row["scores"]["interrupt"])
    interrupt_fn = sum(1 for row in rows if row["label"] == 1 and not row["scores"]["interrupt"])
    interrupt_fp = sum(1 for row in rows if row["label"] == 0 and row["scores"]["interrupt"])
    interrupt_tn = sum(1 for row in rows if row["label"] == 0 and not row["scores"]["interrupt"])
    return {
        "schema": SCHEMA,
        "evidence_class": next(iter(classes)),
        "label_kind": next(iter(label_kinds)),
        "label_scope": {
            "TARGET_CUE": "INSTRUCTION_TARGET_ONLY_NOT_OBSERVED_ATTENTION",
            "EEG_DECODER_ESTIMATE": "MODEL_ESTIMATED_ATTENDED_STATE_NOT_GROUND_TRUTH",
            "OBSERVED_ATTENDED_STATE": "SEPARATELY_OBSERVED_ATTENDED_STATE",
        }[next(iter(label_kinds))],
        "metric_scope": "NEXT_ATTENTION_STATE_SWITCH_WITHIN_HORIZON_NOT_TARGET_IDENTITY",
        "horizon_ms": horizon_ms,
        "history_ms": history_ms,
        "sample_count": len(enriched),
        "switch_rate": round(sum(row["label"] for row in rows) / len(rows), 6),
        "censored_samples": 0,
        "session_count": len(sessions),
        "goal_count": len(goals),
        "stratum_count": len(strata),
        "sequence_count": len(trial_groups),
        "session_stratified": True,
        "source_binding_validated": True,
        "timebase_binding_validated": True,
        "permutation_unit": "WITHIN_SESSION_TRIAL_GOAL_GENERATION",
        "mean_auc_by_feature": {name: round(observed[name], 6) for name in feature_names},
        "negative_controls": controls,
        "interrupt_operating_point": {
            "precision": round(interrupt_tp / max(1, interrupt_tp + interrupt_fp), 6),
            "recall": round(interrupt_tp / max(1, interrupt_tp + interrupt_fn), 6),
            "false_positive_rate": round(interrupt_fp / max(1, interrupt_fp + interrupt_tn), 6),
        },
        "switch_lead_ms": {
            "mean": round(sum(switch_leads) / len(switch_leads), 3) if switch_leads else None,
            "median": sorted(switch_leads)[len(switch_leads)//2] if switch_leads else None,
        },
        "strata": stratum_rows,
        "training_performed": False,
        "policy_changed": False,
        "learning_authority": False,
        "action_authority": False,
        "truth_authority": 0,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="JSONL of A4 receipts plus independent outcome labels")
    parser.add_argument("--horizon-ms", type=int, default=5000)
    parser.add_argument("--history-ms", type=int, default=5000)
    parser.add_argument("--permutations", type=int, default=200)
    parser.add_argument("--seed", type=int, default=17)
    parser.add_argument("--allow-synthetic", action="store_true",
                        help="explicitly allow SYNTHETIC_FIXTURE data; never use for acceptance")
    args = parser.parse_args(argv)
    records = []
    for line_number, line in enumerate(Path(args.input).read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise SystemExit(f"invalid JSONL at line {line_number}: {exc.msg}") from exc
    if not args.allow_synthetic and any(
        type(record) is not dict or record.get("evidence_class") != "OBSERVED_LOCAL"
        for record in records
    ):
        raise SystemExit("OBSERVED_LOCAL is required; pass --allow-synthetic only for non-acceptance fixtures")
    result = evaluate(records, horizon_ms=args.horizon_ms, history_ms=args.history_ms,
                      permutations=args.permutations, seed=args.seed)
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
