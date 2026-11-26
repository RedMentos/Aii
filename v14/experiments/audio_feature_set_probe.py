"""Source-bound, shadow-only feature-set probe for A4/A5 audio packets.

Consumes FINAL A5_AUDIO PerceptPackets enriched with RAW EAR voice cues and
separately sourced goal/action outcomes. Measures whether a set of current
acoustic features predicts a later action beyond any single feature, conditioned
on the active goal. It never admits attention, trains a model, persists packets,
or grants authority.
"""
from __future__ import annotations

from collections import Counter, defaultdict
import math
import random
import re
from typing import Any, Iterable

SCHEMA = "v14.audio-feature-set-predictive-probe/1"
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_ACTIVITY = frozenset({"SILENCE", "VOICED", "UNVOICED_NOISE", "IMPULSIVE", "UNCERTAIN"})
_ACTIONS = frozenset({"INTERRUPT", "CONTINUE"})
_PITCH_SPLIT_HZ = 220.0
_PROSODY_SPLIT = 0.5


def _finite_number(value: Any) -> bool:
    return type(value) in (int, float) and math.isfinite(float(value))


def mutual_information_bits(xs: Iterable[Any], ys: Iterable[Any]) -> float:
    """Empirical plug-in mutual information for discrete variables, in bits."""
    left, right = list(xs), list(ys)
    if not left or len(left) != len(right):
        raise ValueError("mutual-information inputs must be non-empty and equally sized")
    x_counts, y_counts = Counter(left), Counter(right)
    joint = Counter(zip(left, right))
    n = len(left)
    return sum(
        (count / n) * math.log2((count * n) / (x_counts[x] * y_counts[y]))
        for (x, y), count in joint.items()
    )


def conditional_mutual_information_bits(xs: Iterable[Any], ys: Iterable[Any],
                                         conditions: Iterable[Any]) -> float:
    """Empirical I(X;Y|Z), weighted by the observed condition frequencies."""
    left, right, cond = list(xs), list(ys), list(conditions)
    if not left or len(left) != len(right) or len(left) != len(cond):
        raise ValueError("conditional-MI inputs must be non-empty and equally sized")
    groups: dict[Any, tuple[list[Any], list[Any]]] = {}
    for x, y, z in zip(left, right, cond):
        if z not in groups:
            groups[z] = ([], [])
        groups[z][0].append(x)
        groups[z][1].append(y)
    n = len(left)
    return sum(
        len(group_x) / n * mutual_information_bits(group_x, group_y)
        for group_x, group_y in groups.values()
    )


def feature_values_from_packet(packet: dict) -> dict[str, str]:
    """Validate and read the bounded A5/A4 acoustic feature contract.

    Only hashes and cue summaries are accepted. Raw PCM, transcripts,
    provisional evidence and authority flags are deliberately excluded.
    """
    if not isinstance(packet, dict) or packet.get("schema_version") != "1.0":
        raise ValueError("expected schema-version 1.0 PerceptPacket")
    if packet.get("producer_component") != "A5_AUDIO" or packet.get("modality") != "audio":
        raise ValueError("expected A5_AUDIO audio PerceptPacket")
    if not all(
        isinstance(packet.get(key), str) and packet[key]
        for key in ("packet_id", "event_id", "brain_generation_id")
    ):
        raise ValueError("packet identity is incomplete")

    source = packet.get("source_ref")
    if not isinstance(source, dict):
        raise ValueError("packet source_ref is missing")
    if (
        not isinstance(source.get("source_id"), str) or not source["source_id"]
        or not isinstance(source.get("sha256"), str)
        or not _SHA256.fullmatch(source["sha256"])
        or source.get("modality") not in {"audio", "audio/pcm16le"}
    ):
        raise ValueError("audio source binding is invalid")
    provenance = packet.get("provenance")
    if not isinstance(provenance, list) or source not in provenance:
        raise ValueError("packet provenance does not bind its audio source")

    segments = packet.get("segments")
    if not isinstance(segments, list) or len(segments) != 1 or not isinstance(segments[0], dict):
        raise ValueError("expected exactly one bounded audio segment")
    segment = segments[0]
    start_ms, end_ms = segment.get("start_ms"), segment.get("end_ms")
    if (
        type(start_ms) is not int or type(end_ms) is not int
        or not 0 <= start_ms < end_ms or end_ms - start_ms > 1000
    ):
        raise ValueError("audio segment interval is invalid")
    if segment.get("finality") != "FINAL":
        raise ValueError("predictive probe requires FINAL audio evidence")
    if segment.get("learning_authority") is not False or segment.get("action_authority") is not False:
        raise PermissionError("audio percept cannot grant learning or action authority")
    if segment.get("asr_transcript") is not None:
        raise ValueError("transcript text is not an acoustic feature")
    receipt_ref = segment.get("consent_receipt_ref")
    if not isinstance(receipt_ref, str) or not receipt_ref.strip():
        raise ValueError("opaque consent receipt reference is missing")
    if any(key in packet or key in segment for key in ("pcm", "raw_pcm", "samples", "waveform")):
        raise ValueError("raw PCM must not enter the feature-set probe")

    acoustic = segment.get("acoustic")
    cues = acoustic.get("voice_cues") if isinstance(acoustic, dict) else None
    if not isinstance(cues, dict):
        raise ValueError("A4 voice_cues are missing from the A5 packet")
    activity = cues.get("activity_hint")
    if activity not in _ACTIVITY:
        raise ValueError("unknown RAW EAR activity cue")
    pitch = cues.get("f0_median_hz")
    if pitch is not None and (
        not _finite_number(pitch) or not 65.0 <= float(pitch) <= 400.0
    ):
        raise ValueError("RAW EAR median pitch is invalid")
    prosody = cues.get("prosody_change_score")
    if not _finite_number(prosody) or not 0.0 <= float(prosody) <= 1.0:
        raise ValueError("RAW EAR prosody score is invalid")
    if activity != "VOICED" and float(prosody) != 0.0:
        raise ValueError("non-voiced activity cannot carry a prosody-change score")
    return {
        "pitch_band": "NO_PITCH" if pitch is None else (
            "HIGH" if float(pitch) >= _PITCH_SPLIT_HZ else "LOW"
        ),
        "prosody_band": "HIGH" if float(prosody) >= _PROSODY_SPLIT else "LOW",
        "activity_hint": activity,
    }


def _validate_record(record: dict) -> tuple[dict[str, str], str, str, int]:
    if not isinstance(record, dict) or record.get("evidence_class") != "SYNTHETIC_FIXTURE":
        raise ValueError("this probe version accepts synthetic fixtures only")
    packet = record.get("packet")
    outcome = record.get("outcome")
    features = feature_values_from_packet(packet)
    if not isinstance(outcome, dict):
        raise ValueError("separate goal/action outcome is missing")
    goal_id = outcome.get("goal_id")
    action_id = outcome.get("action_id")
    action_type = outcome.get("action_type")
    if not all(isinstance(value, str) and value for value in (goal_id, action_id)):
        raise ValueError("goal/action identity is incomplete")
    if action_type not in _ACTIONS:
        raise ValueError("unsupported action outcome")
    observed_at_ms = outcome.get("observed_at_ms")
    end_ms = packet["segments"][0]["end_ms"]
    if type(observed_at_ms) is not int or observed_at_ms < end_ms:
        raise ValueError("goal/action outcome must occur after its audio source")
    outcome_source = outcome.get("source_ref")
    audio_source = packet["source_ref"]
    if (
        not isinstance(outcome_source, dict)
        or outcome_source.get("modality") != "world/action-outcome"
        or not isinstance(outcome_source.get("source_id"), str)
        or not outcome_source["source_id"]
        or not isinstance(outcome_source.get("sha256"), str)
        or not _SHA256.fullmatch(outcome_source["sha256"])
        or outcome_source.get("source_id") == audio_source["source_id"]
        or outcome_source.get("sha256") == audio_source["sha256"]
    ):
        raise ValueError("goal/action outcome must have a separate source binding")
    if outcome.get("learning_authority") is not False or outcome.get("action_authority") is not False:
        raise PermissionError("outcome fixture cannot grant learning or action authority")
    return features, goal_id, action_type, packet["segments"][0]["start_ms"]


def evaluate_feature_set(records: Iterable[dict], *, seed: int = 17,
                         permutations: int = 64, min_records: int = 32,
                         min_per_goal: int = 8) -> dict:
    """Measure feature-set/action information with within-goal time shuffles.

    Outcomes are permuted within each goal, preserving goal/action marginals
    while breaking the feature-to-outcome pairing. The result is diagnostic
    only; no attention admission, training, persistence, or action follows.
    """
    if type(seed) is not int or isinstance(seed, bool):
        raise ValueError("seed must be an integer")
    if type(permutations) is not int or isinstance(permutations, bool) or not 1 <= permutations <= 10000:
        raise ValueError("permutations must be an integer in [1, 10000]")
    if type(min_records) is not int or min_records < 2 or type(min_per_goal) is not int or min_per_goal < 1:
        raise ValueError("invalid minimum cohort")
    rows = list(records)
    if len(rows) < min_records:
        raise ValueError("insufficient source-bound records")
    parsed = [_validate_record(row) for row in rows]
    generations = {row["packet"]["brain_generation_id"] for row in rows}
    if len(generations) != 1:
        raise ValueError("audio packets cross brain generations")
    source_hashes = [row["packet"]["source_ref"]["sha256"] for row in rows]
    event_ids = [row["packet"]["event_id"] for row in rows]
    action_ids = [row["outcome"]["action_id"] for row in rows]
    outcome_hashes = [row["outcome"]["source_ref"]["sha256"] for row in rows]
    if (
        len(set(source_hashes)) != len(source_hashes)
        or len(set(event_ids)) != len(event_ids)
        or len(set(action_ids)) != len(action_ids)
        or len(set(outcome_hashes)) != len(outcome_hashes)
    ):
        raise ValueError("duplicate source/event/action binding in cohort")
    starts = [row[3] for row in parsed]
    if any(right <= left for left, right in zip(starts, starts[1:])):
        raise ValueError("audio windows must be supplied in increasing time order")

    features = [row[0] for row in parsed]
    goals = [row[1] for row in parsed]
    actions = [row[2] for row in parsed]
    goal_counts = Counter(goals)
    if len(goal_counts) < 2 or min(goal_counts.values()) < min_per_goal:
        raise ValueError("goal-conditioned cohort is too small")

    pitch = [item["pitch_band"] for item in features]
    prosody = [item["prosody_band"] for item in features]
    activity = [item["activity_hint"] for item in features]
    feature_set = list(zip(pitch, prosody, activity))
    single_feature_cmi = {
        "pitch_band": conditional_mutual_information_bits(pitch, actions, goals),
        "prosody_band": conditional_mutual_information_bits(prosody, actions, goals),
        "activity_hint": conditional_mutual_information_bits(activity, actions, goals),
    }
    joint_cmi = conditional_mutual_information_bits(feature_set, actions, goals)
    joint_gain = joint_cmi - max(single_feature_cmi.values())

    by_goal: dict[str, list[int]] = defaultdict(list)
    for index, goal in enumerate(goals):
        by_goal[goal].append(index)
    rng = random.Random(seed)
    null_scores = []
    for _ in range(permutations):
        shuffled_actions = list(actions)
        for indices in by_goal.values():
            labels = [actions[index] for index in indices]
            rng.shuffle(labels)
            for index, label in zip(indices, labels):
                shuffled_actions[index] = label
        null_scores.append(conditional_mutual_information_bits(feature_set, shuffled_actions, goals))
    ordered_null = sorted(null_scores)
    p95_index = min(len(ordered_null) - 1, math.ceil(0.95 * len(ordered_null)) - 1)
    permutation_p = (1 + sum(score >= joint_cmi for score in null_scores)) / (permutations + 1)

    self_mi = {
        "pitch_band": mutual_information_bits(pitch[:-1], pitch[1:]),
        "prosody_band": mutual_information_bits(prosody[:-1], prosody[1:]),
        "activity_hint": mutual_information_bits(activity[:-1], activity[1:]),
        "feature_set": mutual_information_bits(feature_set[:-1], feature_set[1:]),
    }
    return {
        "schema": SCHEMA,
        "evidence_class": "SYNTHETIC_FIXTURE_ONLY",
        "record_count": len(rows),
        "goal_count": len(goal_counts),
        "source_binding_validated": True,
        "feature_names": ["pitch_band", "prosody_band", "activity_hint"],
        "feature_set_goal_action_cmi_bits": joint_cmi,
        "single_feature_goal_action_cmi_bits": single_feature_cmi,
        "joint_gain_over_best_single_bits": joint_gain,
        "shuffled_time_cmi_median_bits": ordered_null[len(ordered_null) // 2],
        "shuffled_time_cmi_p95_bits": ordered_null[p95_index],
        "permutation_p_value": permutation_p,
        "goal_only_action_mi_bits": mutual_information_bits(goals, actions),
        "feature_self_predictive_mi_bits": self_mi,
        "trained_jepa": False,
        "runtime_integrated": False,
        "attention_policy_changed": False,
        "learning_authority": 0,
        "action_authority": 0,
        "persisted": False,
    }
