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

    Also returns a session-local, coarse-history rIMI proxy. Outcomes are
    permuted within each goal, preserving goal/action marginals while breaking
    feature-to-outcome pairing. All results are diagnostic only.
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
        "relative_incremental_information": evaluate_relative_incremental_information(
            rows, seed=seed, permutations=permutations,
        ),
    }


def _conditional_entropy_bits(values: Iterable[Any], conditions: Iterable[Any]) -> float:
    """Empirical H(Y|Z) for discrete values, in bits."""
    targets, cond = list(values), list(conditions)
    if not targets or len(targets) != len(cond):
        raise ValueError("conditional-entropy inputs must be non-empty and equally sized")
    groups: dict[Any, list[Any]] = defaultdict(list)
    for target, condition in zip(targets, cond):
        groups[condition].append(target)
    total = 0.0
    n = len(targets)
    for group in groups.values():
        counts = Counter(group)
        size = len(group)
        entropy = -sum((count / size) * math.log2(count / size) for count in counts.values())
        total += size / n * entropy
    return total


def evaluate_relative_incremental_information(
    records: Iterable[dict], *, history_window_ms: int = 5000, seed: int = 17,
    permutations: int = 64, min_records: int = 32, min_per_session: int = 8,
) -> dict:
    """Return a discrete, session-local rIMI *proxy*, not the paper's estimator.

    Current FINAL A4/A5 feature tuples are tested for incremental information
    about a later, separately sourced action outcome, conditioned on the goal
    and a coarse summary of prior feature windows from the same session. The
    history summary contains the last feature tuple plus a capped prior-window
    count; only prior windows that ended before the current window are used.

    This intentionally differs from Heintz et al.'s full rIMI method: it uses
    discrete plug-in MI and a coarse feature-history state, not Gaussian-copula
    estimates over the previous five seconds of prediction scores. It is a
    synthetic diagnostic, not human auditory-attention decoding, a runtime
    attention signal, JEPA learning, or decision authority.
    """
    rows = list(records)
    if type(history_window_ms) is not int or isinstance(history_window_ms, bool) or not 1 <= history_window_ms <= 60000:
        raise ValueError("history window must be an integer in [1, 60000] ms")
    if type(seed) is not int or isinstance(seed, bool):
        raise ValueError("seed must be an integer")
    if type(permutations) is not int or isinstance(permutations, bool) or not 1 <= permutations <= 10000:
        raise ValueError("permutations must be an integer in [1, 10000]")
    if type(min_records) is not int or isinstance(min_records, bool) or min_records < 2:
        raise ValueError("minimum record count is invalid")
    if type(min_per_session) is not int or isinstance(min_per_session, bool) or min_per_session < 2:
        raise ValueError("minimum session count is invalid")
    if len(rows) < min_records:
        raise ValueError("insufficient source-bound records")

    session_ids = []
    for record in rows:
        session_id = record.get("session_id") if isinstance(record, dict) else None
        if not isinstance(session_id, str) or not session_id.strip():
            raise ValueError("session identity is missing")
        session_ids.append(session_id)

    parsed = [_validate_record(record) for record in rows]
    generations = {record["packet"]["brain_generation_id"] for record in rows}
    if len(generations) != 1:
        raise ValueError("audio packets cross brain generations")
    feature_sets = [
        tuple(item[key] for key in ("pitch_band", "prosody_band", "activity_hint"))
        for item, _goal, _action, _start in parsed
    ]
    goals = [item[1] for item in parsed]
    actions = [item[2] for item in parsed]
    starts = [item[3] for item in parsed]
    ends = [record["packet"]["segments"][0]["end_ms"] for record in rows]

    source_hashes = [record["packet"]["source_ref"]["sha256"] for record in rows]
    event_ids = [record["packet"]["event_id"] for record in rows]
    action_ids = [record["outcome"]["action_id"] for record in rows]
    outcome_hashes = [record["outcome"]["source_ref"]["sha256"] for record in rows]
    if (
        len(set(source_hashes)) != len(rows)
        or len(set(event_ids)) != len(rows)
        or len(set(action_ids)) != len(rows)
        or len(set(outcome_hashes)) != len(rows)
    ):
        raise ValueError("duplicate source/event/action binding in cohort")

    session_rows: dict[str, list[int]] = defaultdict(list)
    for index, session_id in enumerate(session_ids):
        session_rows[session_id].append(index)
    if len(session_rows) < 2:
        raise ValueError("at least two sessions are required")

    for indices in session_rows.values():
        if len(indices) < min_per_session:
            raise ValueError("session cohort is too small")
        session_starts = [starts[index] for index in indices]
        if any(right <= left for left, right in zip(session_starts, session_starts[1:])):
            raise ValueError("session audio windows must advance monotonically")
        goal_counts = Counter(goals[index] for index in indices)
        if len(goal_counts) < 2 or min(goal_counts.values()) < 2:
            raise ValueError("each session must include multiple goals with repeated outcomes")

    histories: list[tuple] = [("EMPTY",)] * len(rows)
    nonempty_history = 0
    max_history_depth = 0
    for indices in session_rows.values():
        prior_indices: list[int] = []
        for index in indices:
            eligible = [
                previous for previous in prior_indices
                if 0 <= starts[index] - ends[previous] <= history_window_ms
            ]
            if eligible:
                depth = min(len(eligible), 5)
                histories[index] = ("HISTORY", depth, feature_sets[eligible[-1]])
                nonempty_history += 1
                max_history_depth = max(max_history_depth, depth)
            prior_indices.append(index)

    conditions = [
        (session_ids[index], goals[index], histories[index])
        for index in range(len(rows))
    ]
    incremental_mi = conditional_mutual_information_bits(feature_sets, actions, conditions)
    remaining_entropy = _conditional_entropy_bits(actions, conditions)
    rimi_proxy = (
        None if remaining_entropy <= 1e-12
        else min(1.0, max(0.0, incremental_mi / remaining_entropy))
    )
    conditional_self_dependence = conditional_mutual_information_bits(
        feature_sets, histories,
        [
            (session_ids[index], goals[index], actions[index])
            for index in range(len(rows))
        ],
    )
    no_history_cmi = conditional_mutual_information_bits(
        feature_sets, actions,
        [
            (session_ids[index], goals[index])
            for index in range(len(rows))
        ],
    )

    per_session = []
    for ordinal, indices in enumerate(session_rows.values()):
        session_features = [feature_sets[index] for index in indices]
        session_actions = [actions[index] for index in indices]
        session_conditions = [
            (goals[index], histories[index]) for index in indices
        ]
        session_incremental = conditional_mutual_information_bits(
            session_features, session_actions, session_conditions
        )
        session_entropy = _conditional_entropy_bits(session_actions, session_conditions)
        per_session.append({
            "session_index": ordinal,
            "record_count": len(indices),
            "incremental_mi_bits": session_incremental,
            "remaining_entropy_bits": session_entropy,
            "rimi_proxy": (
                None if session_entropy <= 1e-12
                else min(1.0, max(0.0, session_incremental / session_entropy))
            ),
        })

    permutation_groups: dict[tuple[str, str], list[int]] = defaultdict(list)
    for index, key in enumerate(zip(session_ids, goals)):
        permutation_groups[key].append(index)
    rng = random.Random(seed)
    null_scores = []
    for _ in range(permutations):
        shuffled_actions = list(actions)
        for indices in permutation_groups.values():
            labels = [actions[index] for index in indices]
            rng.shuffle(labels)
            for index, label in zip(indices, labels):
                shuffled_actions[index] = label
        permuted_mi = conditional_mutual_information_bits(
            feature_sets, shuffled_actions, conditions
        )
        permuted_entropy = _conditional_entropy_bits(shuffled_actions, conditions)
        if permuted_entropy > 1e-12:
            null_scores.append(min(1.0, max(0.0, permuted_mi / permuted_entropy)))

    ordered_null = sorted(null_scores)
    permutation_p = (
        None if rimi_proxy is None or not null_scores
        else (1 + sum(score >= rimi_proxy for score in null_scores)) / (len(null_scores) + 1)
    )
    p95_index = min(len(ordered_null) - 1, math.ceil(0.95 * len(ordered_null)) - 1)
    return {
        "schema": "v14.audio-relative-incremental-information-proxy/1",
        "estimator": "DISCRETE_PLUGIN_COARSE_HISTORY_PROXY",
        "paper_exact_rimi": False,
        "evidence_class": "SYNTHETIC_FIXTURE_ONLY",
        "record_count": len(rows),
        "session_count": len(session_rows),
        "minimum_records_per_session": min(len(indices) for indices in session_rows.values()),
        "history_window_ms": history_window_ms,
        "history_state": "LAST_FEATURE_SET_PLUS_CAPPED_PRIOR_WINDOW_COUNT",
        "history_crosses_sessions": False,
        "session_history_reset_verified": all(
            histories[indices[0]] == ("EMPTY",) for indices in session_rows.values()
        ),
        "history_nonempty_fraction": nonempty_history / len(rows),
        "history_depth_max": max_history_depth,
        "relative_incremental_information_bits": incremental_mi,
        "remaining_action_entropy_bits": remaining_entropy,
        "rimi_proxy": rimi_proxy,
        "conditional_self_dependence_bits": conditional_self_dependence,
        "no_history_goal_conditioned_cmi_bits": no_history_cmi,
        "per_session": per_session,
        "permutation_strata": "SESSION_X_GOAL",
        "permutation_p_value": permutation_p,
        "permutation_p95_rimi_proxy": (
            ordered_null[p95_index] if ordered_null else None
        ),
        "runtime_integrated": False,
        "attention_policy_changed": False,
        "learning_authority": 0,
        "action_authority": 0,
        "persisted": False,
    }
