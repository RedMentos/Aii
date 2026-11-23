#!/usr/bin/env python3
"""Deterministic, synthetic A4 novelty-gate stress test.

This is deliberately NOT a FASTDIAR/VBx reproduction. It isolates three design
choices using 192-D synthetic embeddings: binary threshold vs three-way
assign/defer/create, and all-history vs sliding-window vs first-exemplar
prototype retention. No real audio, model weights, identity data, or persistent
vectors are used. The result is a mechanism sanity check, not a product gate.
"""
from __future__ import annotations

import argparse
import json
import math
import random
from collections import defaultdict, deque
from dataclasses import dataclass
from statistics import mean
from typing import Iterable

DIM = 192
SCHEDULE = (0, 1, 2, 0, 3, 1, 2, 3, 0)
TURN_LENGTH = 20


@dataclass(frozen=True)
class Segment:
    source_group: str
    index: int
    speaker: int | None
    vector: tuple[float, ...]
    quality: float
    overlap: bool
    transition: bool


def _unit(values: Iterable[float]) -> tuple[float, ...]:
    values = tuple(float(x) for x in values)
    norm = math.sqrt(sum(x * x for x in values))
    if not math.isfinite(norm) or norm <= 1e-12:
        raise ValueError("cannot normalize a zero or non-finite vector")
    return tuple(x / norm for x in values)


def _cosine(left: tuple[float, ...], right: tuple[float, ...]) -> float:
    if len(left) != len(right):
        raise ValueError("embedding dimensions differ")
    return max(-1.0, min(1.0, sum(a * b for a, b in zip(left, right))))


def make_sessions(*, count: int = 20, seed: int = 20261122) -> list[list[Segment]]:
    """Make independent source groups; each meeting has private speaker bases."""
    sessions: list[list[Segment]] = []
    for session_index in range(count):
        rng = random.Random(seed + session_index * 10007)
        centers = {
            speaker: _unit(rng.gauss(0.0, 1.0) for _ in range(DIM))
            for speaker in range(4)
        }
        segments: list[Segment] = []
        previous_speaker: int | None = None
        index = 0
        for turn_index, speaker in enumerate(SCHEDULE):
            for within_turn in range(TURN_LENGTH):
                boundary_overlap = turn_index > 0 and within_turn < 2
                previous_turn_speaker = SCHEDULE[turn_index - 1] if turn_index else speaker
                noisy = not boundary_overlap and (index % 31 == 17)
                quality = 0.28 if boundary_overlap else (0.52 if noisy else 0.94)
                if boundary_overlap:
                    raw = [
                        0.5 * centers[speaker][j]
                        + 0.5 * centers[previous_turn_speaker][j]
                        + rng.gauss(0.0, 0.035)
                        for j in range(DIM)
                    ]
                    label = None
                else:
                    noise = 0.17 if noisy else 0.075
                    raw = [centers[speaker][j] + rng.gauss(0.0, noise) for j in range(DIM)]
                    label = speaker
                transition = label is not None and previous_speaker is not None and label != previous_speaker
                if label is not None:
                    previous_speaker = label
                segments.append(Segment(
                    source_group=f"synthetic-meeting-{session_index:03d}",
                    index=index,
                    speaker=label,
                    vector=_unit(raw),
                    quality=quality,
                    overlap=boundary_overlap,
                    transition=transition,
                ))
                index += 1
        sessions.append(segments)
    return sessions


class PrototypeBank:
    def __init__(self, mode: str, window: int = 24):
        if mode not in {"full_history", "sliding_window", "first_exemplar"}:
            raise ValueError("unknown prototype retention mode")
        self.mode = mode
        self.window = window
        self.samples: dict[int, deque[tuple[float, ...]]] = {}
        self.sums: dict[int, list[float]] = {}
        self.prototypes: dict[int, tuple[float, ...]] = {}
        self.global_window: deque[tuple[int, tuple[float, ...]]] = deque(maxlen=window)

    def add(self, cluster_id: int, vector: tuple[float, ...]) -> None:
        if self.mode == "sliding_window":
            self.global_window.append((cluster_id, vector))
            sums: dict[int, list[float]] = {}
            for key, sample in self.global_window:
                bucket = sums.setdefault(key, [0.0] * DIM)
                for j, value in enumerate(sample):
                    bucket[j] += value
            self.prototypes = {key: _unit(total) for key, total in sums.items()}
            return
        if cluster_id not in self.samples:
            self.samples[cluster_id] = deque()
            self.sums[cluster_id] = [0.0] * DIM
        history = self.samples[cluster_id]
        if self.mode == "first_exemplar" and history:
            return
        history.append(vector)
        for j, value in enumerate(vector):
            self.sums[cluster_id][j] += value
        self.prototypes[cluster_id] = _unit(self.sums[cluster_id])

    def best(self, vector: tuple[float, ...]) -> tuple[int, float] | None:
        if not self.prototypes:
            return None
        similarity, cluster_id = max(
            (_cosine(vector, prototype), key)
            for key, prototype in self.prototypes.items()
        )
        return cluster_id, similarity


def run_session(
    segments: list[Segment], *, policy: str, memory: str,
    single_threshold: float = 0.27, low_threshold: float = 0.14,
    high_threshold: float = 0.34, quality_floor: float = 0.65,
) -> dict:
    bank = PrototypeBank(memory)
    decisions = []
    next_cluster = 0
    for segment in segments:
        nearest = bank.best(segment.vector)
        if nearest is None:
            decision, cluster_id = "CREATE", next_cluster
            next_cluster += 1
        else:
            nearest_id, similarity = nearest
            novelty = (1.0 - similarity) * 0.5
            if policy == "no_gate":
                decision, cluster_id = "ASSIGN", nearest_id
            elif policy == "single_threshold":
                decision = "CREATE" if novelty >= single_threshold else "ASSIGN"
                cluster_id = next_cluster if decision == "CREATE" else nearest_id
                if decision == "CREATE":
                    next_cluster += 1
            elif policy == "triage":
                if segment.overlap or segment.quality < quality_floor:
                    decision, cluster_id = "DEFER", None
                elif novelty <= low_threshold:
                    decision, cluster_id = "ASSIGN", nearest_id
                elif novelty >= high_threshold:
                    decision, cluster_id = "CREATE", next_cluster
                    next_cluster += 1
                else:
                    decision, cluster_id = "DEFER", None
            else:
                raise ValueError("unknown novelty policy")
        if decision in {"CREATE", "ASSIGN"} and cluster_id is not None:
            bank.add(cluster_id, segment.vector)
        decisions.append({"decision": decision, "cluster_id": cluster_id})
    return evaluate(segments, decisions)


def evaluate(segments: list[Segment], decisions: list[dict]) -> dict:
    tp = fp = fn = 0
    overlap_deferred = overlap_total = 0
    deferred = assigned = single_total = 0
    cluster_members: dict[int, list[int]] = defaultdict(list)
    first_cluster_by_speaker: dict[int, int] = {}
    speaker_recall_hits = speaker_recall_total = 0
    for segment, result in zip(segments, decisions):
        decision, cluster_id = result["decision"], result["cluster_id"]
        if decision == "DEFER":
            deferred += 1
        if segment.overlap:
            overlap_total += 1
            overlap_deferred += int(decision == "DEFER")
            continue
        single_total += 1
        if decision != "DEFER":
            assigned += 1
        if segment.transition:
            tp += int(decision == "CREATE")
            fn += int(decision != "CREATE")
        elif decision == "CREATE" and segment.index != 0:
            fp += 1
        if cluster_id is not None:
            cluster_members[cluster_id].append(segment.speaker)
            if segment.speaker not in first_cluster_by_speaker:
                first_cluster_by_speaker[segment.speaker] = cluster_id
            speaker_recall_total += 1
            speaker_recall_hits += int(first_cluster_by_speaker[segment.speaker] == cluster_id)
    # Cluster purity is a post-hoc diagnostic; the online algorithm never sees labels.
    purity_hits = 0
    for labels in cluster_members.values():
        counts: dict[int, int] = defaultdict(int)
        for label in labels:
            counts[label] += 1
        purity_hits += max(counts.values())
    cluster_count = len(cluster_members)
    true_speakers = len({segment.speaker for segment in segments if segment.speaker is not None})
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "change_precision": precision,
        "change_recall": recall,
        "change_f1": f1,
        "false_novelty_rate": fp / max(1, single_total - sum(s.transition for s in segments) - 1),
        "overlap_defer_rate": overlap_deferred / max(1, overlap_total),
        "defer_rate": deferred / max(1, len(segments)),
        "coverage": assigned / max(1, single_total),
        "cluster_purity": purity_hits / max(1, assigned),
        "one_shot_recall": speaker_recall_hits / max(1, speaker_recall_total),
        "cluster_count": cluster_count,
        "cluster_count_error": abs(cluster_count - true_speakers),
        "segments": len(segments),
        "overlap_segments": overlap_total,
    }


def _objective(metrics: dict) -> float:
    # Fixed before holdout: reward change detection and overlap abstention;
    # penalize false novelty and excessive deferral. Synthetic-only objective.
    return (
        metrics["change_f1"]
        + 0.25 * metrics["overlap_defer_rate"]
        + 0.20 * metrics["cluster_purity"]
        - 0.75 * metrics["false_novelty_rate"]
        - 0.20 * metrics["defer_rate"]
        - 0.10 * metrics["cluster_count_error"]
    )


def tune(sessions: list[list[Segment]], *, policy: str, memory: str) -> dict:
    if policy == "no_gate":
        return {"parameters": {}, "train_score": mean(
            _objective(run_session(s, policy=policy, memory=memory)) for s in sessions
        )}
    candidates = []
    if policy == "single_threshold":
        for threshold in (0.16, 0.22, 0.28, 0.34, 0.40):
            params = {"single_threshold": threshold}
            scores = [run_session(s, policy=policy, memory=memory, **params) for s in sessions]
            candidates.append((_objective({k: mean(m[k] for m in scores) for k in scores[0]}), params))
    else:
        for low in (0.10, 0.16, 0.22):
            for high in (0.30, 0.38, 0.46):
                if high <= low:
                    continue
                for quality in (0.50, 0.70):
                    params = {"low_threshold": low, "high_threshold": high, "quality_floor": quality}
                    scores = [run_session(s, policy=policy, memory=memory, **params) for s in sessions]
                    candidates.append((_objective({k: mean(m[k] for m in scores) for k in scores[0]}), params))
    score, parameters = max(candidates, key=lambda item: item[0])
    return {"parameters": parameters, "train_score": score}


def run_ablation(*, seed: int = 20261122, session_count: int = 20) -> dict:
    if session_count < 8 or session_count % 2:
        raise ValueError("session_count must be even and at least 8 for source-disjoint holdout")
    sessions = make_sessions(count=session_count, seed=seed)
    train_sessions, test_sessions = sessions[:session_count // 2], sessions[session_count // 2:]
    train_groups = {s[0].source_group for s in train_sessions}
    test_groups = {s[0].source_group for s in test_sessions}
    if train_groups & test_groups:
        raise AssertionError("source-group leakage between calibration and holdout")
    results = []
    for memory in ("full_history", "sliding_window", "first_exemplar"):
        for policy in ("no_gate", "single_threshold", "triage"):
            fitted = tune(train_sessions, policy=policy, memory=memory)
            holdout = [run_session(s, policy=policy, memory=memory, **fitted["parameters"])
                       for s in test_sessions]
            aggregate = {key: mean(item[key] for item in holdout) for key in holdout[0]}
            results.append({
                "policy": policy,
                "memory": memory,
                "parameters": fitted["parameters"],
                "train_objective": fitted["train_score"],
                "holdout": aggregate,
            })
    return {
        "schema": "v14.a4.novelty-gate-ablation/1",
        "evidence": "SYNTHETIC_ONLY",
        "seed": seed,
        "dimension": DIM,
        "train_source_groups": sorted(train_groups),
        "holdout_source_groups": sorted(test_groups),
        "source_disjoint": True,
        "synthetic_audio_claim": False,
        "runtime_consumer_claim": False,
        "method_boundary": (
            "Cosine-prototype toy stress test only; sliding_window is a global 24-event "
            "retention proxy, not VBx sleep. Not PLDA, FASTDIAR inference, speaker identity, "
            "real audio, or a reproduction of arXiv:2611.20819v1."
        ),
        "results": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=20261122)
    parser.add_argument("--sessions", type=int, default=20)
    parser.add_argument("--output", default="")
    args = parser.parse_args()
    report = run_ablation(seed=args.seed, session_count=args.sessions)
    rendered = json.dumps(report, sort_keys=True, indent=2) + "\n"
    if args.output:
        with open(args.output, "w", encoding="utf-8") as handle:
            handle.write(rendered)
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
