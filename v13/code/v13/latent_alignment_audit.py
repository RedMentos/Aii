"""Read-only audit of paired, source-bound V13 LatentTapPacket artifacts.

The current tap path records per-token final RMSNorm output embeddings. This
module measures cross-space neighbourhood overlap without requiring equal
embedding dimensions. It never reads source text, loads a model, writes state,
changes weights, or grants B3/learning authority. It is an alignment screen,
not a semantic-communication or causal-transfer proof.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import sqlite3
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any

PACKET_KIND = "LatentTapPacket"
SENDER_ROLES = frozenset({"B1_DETAIL", "B2_GIST"})
MAX_RECORDS = 8192
MAX_SAMPLES = 32
MAX_COHORTS = 4
MAX_ROWS = 64
MAX_DIM = 4096
MAX_PERMUTATIONS = 1000
EXPECTED_NORMALIZATION = "native_final_RMSNorm_only"


class AuditError(ValueError):
    """Invalid or unsafe tap evidence."""


def _finite_number(value: Any) -> bool:
    return type(value) in (int, float) and math.isfinite(float(value))


def _digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _source_key(source_ref: Any) -> tuple[str, str, int, int, str]:
    if not isinstance(source_ref, dict):
        raise AuditError("source_ref is not an object")
    source_id = source_ref.get("source_id")
    digest = source_ref.get("sha256")
    start = source_ref.get("char_start")
    end = source_ref.get("char_end")
    modality = source_ref.get("modality")
    if not isinstance(source_id, str) or not source_id:
        raise AuditError("source_ref source_id is invalid")
    if (not isinstance(digest, str) or len(digest) != 64
            or any(ch not in "0123456789abcdef" for ch in digest.lower())):
        raise AuditError("source_ref sha256 is invalid")
    if type(start) is not int or type(end) is not int or start < 0 or end < start:
        raise AuditError("source_ref character range is invalid")
    if not isinstance(modality, str) or not modality:
        raise AuditError("source_ref modality is invalid")
    return source_id, digest.lower(), start, end, modality


def _packet_order(value: Any) -> tuple[int, str]:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return (1, f"{float(value):030.6f}")
    return (0, str(value or ""))


def _read_tap_blob(home: Path, packet: dict[str, Any]) -> tuple[list[list[float]], list[int]]:
    relative = packet.get("feature_path")
    expected = packet.get("feature_sha256")
    if not isinstance(relative, str) or not relative or Path(relative).is_absolute():
        raise AuditError("feature_path must be a relative path")
    if ".." in Path(relative).parts:
        raise AuditError("feature_path traversal is refused")
    if (not isinstance(expected, str) or len(expected) != 64
            or any(ch not in "0123456789abcdef" for ch in expected.lower())):
        raise AuditError("feature_sha256 is invalid")

    data_dir = home / "data"
    blobs_candidate = data_dir / "blobs"
    if data_dir.is_symlink() or blobs_candidate.is_symlink():
        raise AuditError("runtime data/blob directory symlinks are refused")
    blobs = blobs_candidate.resolve(strict=True)
    candidate = home / relative
    if candidate.is_symlink():
        raise AuditError("tap blob symlinks are refused")
    path = candidate.resolve(strict=True)
    if not path.is_relative_to(blobs) or not path.is_file():
        raise AuditError("tap blob is outside data/blobs")
    if _digest(path) != expected.lower():
        raise AuditError("tap blob hash mismatch")

    data = json.loads(path.read_text(encoding="utf-8"))
    token_ids = data.get("token_ids") if isinstance(data, dict) else None
    vectors = data.get("vectors") if isinstance(data, dict) else None
    if not isinstance(token_ids, list) or not isinstance(vectors, list):
        raise AuditError("tap blob is missing token_ids/vectors")
    rows = len(vectors)
    if not 2 <= rows <= MAX_ROWS or len(token_ids) != rows:
        raise AuditError("tap row count is invalid")
    if any(type(token) is not int or token < 0 for token in token_ids):
        raise AuditError("tap token IDs are invalid")
    if not isinstance(vectors[0], list):
        raise AuditError("tap vector row is invalid")
    dim = len(vectors[0])
    if not 1 <= dim <= MAX_DIM:
        raise AuditError("tap dimension is invalid")
    clean: list[list[float]] = []
    for row in vectors:
        if not isinstance(row, list) or len(row) != dim:
            raise AuditError("tap vectors are ragged")
        if any(not _finite_number(value) for value in row):
            raise AuditError("tap vector contains a non-finite value")
        clean.append([float(value) for value in row])
    shape = packet.get("shape")
    if shape != [rows, dim]:
        raise AuditError("packet shape does not match tap blob")
    if token_ids != packet.get("token_ids"):
        raise AuditError("tap blob token IDs differ from the stored packet")
    metrics = packet.get("metrics")
    if not isinstance(metrics, dict) or metrics.get("embedding_dim") != dim:
        raise AuditError("tap embedding dimension differs from its metric receipt")
    if metrics.get("tap_id") != packet.get("tap_id"):
        raise AuditError("tap identity differs from its metric receipt")
    return clean, token_ids


def _validate_packet(packet: Any) -> tuple[tuple[str, str, int, int, str], str, str, str, str]:
    if not isinstance(packet, dict):
        raise AuditError("packet payload is not an object")
    role = packet.get("role")
    revision = packet.get("model_revision")
    tap_id = packet.get("tap_id")
    if role not in SENDER_ROLES or not isinstance(revision, str) or not revision:
        raise AuditError("tap role/model revision is invalid")
    if not isinstance(tap_id, str) or not tap_id:
        raise AuditError("tap identity is invalid")
    if packet.get("role_state") != "INDEPENDENT_READ_ONLY_PREFILL":
        raise AuditError("tap is not an independent read-only prefill")
    for field in ("receiver_read_authority", "receiver_injection_authority", "body_learning_authority"):
        if packet.get(field) != 0:
            raise AuditError("tap authority invariant is not zero")
    metrics = packet.get("metrics")
    if not isinstance(metrics, dict):
        raise AuditError("tap metrics are missing")
    if (metrics.get("operation") != "PREFILL_TAP"
            or metrics.get("pooling") != "none"
            or metrics.get("whole_sequence_prefill") is not True
            or metrics.get("normalization") != EXPECTED_NORMALIZATION
            or metrics.get("CAN_LATENT_TAP") is not True
            or metrics.get("CAN_LATENT_INJECT") is not False
            or metrics.get("CAN_TRAIN_BODY") is not False):
        raise AuditError("tap is not the pinned final-RMSNorm read-only tap")
    token_ids = packet.get("token_ids")
    if (not isinstance(token_ids, list) or metrics.get("prompt_tokens") != len(token_ids)
            or any(type(token) is not int or token < 0 for token in token_ids)):
        raise AuditError("tap token/metric count mismatch")
    if metrics.get("tap_id") != tap_id:
        raise AuditError("tap identity differs from its metric receipt")
    event_id = packet.get("event_id")
    generation_id = packet.get("brain_generation_id")
    if not isinstance(event_id, str) or not event_id or not isinstance(generation_id, str) or not generation_id:
        raise AuditError("tap event/generation binding is invalid")
    return _source_key(packet.get("source_ref")), role, revision, event_id, generation_id


def _pool_without_position0(vectors: list[list[float]]) -> tuple[list[float], float | None, float | None]:
    """Mean-pool rows 1..N-1; also return pos0/median-rest norm and all-vs-rest cosine."""
    if len(vectors) < 2:
        raise AuditError("at least two tap rows are required to exclude position 0")
    dim = len(vectors[0])
    rest = vectors[1:]
    pooled_rest = [math.fsum(row[col] for row in rest) / len(rest) for col in range(dim)]
    pooled_all = [math.fsum(row[col] for row in vectors) / len(vectors) for col in range(dim)]
    rest_norms = [math.sqrt(math.fsum(value * value for value in row)) for row in rest]
    median_rest = statistics.median(rest_norms)
    first_norm = math.sqrt(math.fsum(value * value for value in vectors[0]))
    ratio = first_norm / median_rest if median_rest > 0 else None
    cosine = _cosine(pooled_all, pooled_rest)
    return pooled_rest, ratio, cosine


def _cosine(a: list[float], b: list[float]) -> float | None:
    if len(a) != len(b) or not a:
        return None
    aa = math.fsum(value * value for value in a)
    bb = math.fsum(value * value for value in b)
    if aa <= 0 or bb <= 0:
        return None
    dot = math.fsum(x * y for x, y in zip(a, b))
    return dot / math.sqrt(aa * bb)


def _normalize_rows(rows: list[list[float]]) -> list[list[float]]:
    output = []
    for row in rows:
        norm = math.sqrt(math.fsum(value * value for value in row))
        if norm <= 0:
            raise AuditError("pooled tap vector has zero norm")
        output.append([value / norm for value in row])
    return output


def _nearest_neighbors(rows: list[list[float]], k: int) -> list[set[int]]:
    normalized = _normalize_rows(rows)
    result = []
    for index, row in enumerate(normalized):
        scored = []
        for other_index, other in enumerate(normalized):
            if other_index == index:
                continue
            score = math.fsum(x * y for x, y in zip(row, other))
            scored.append((score, other_index))
        scored.sort(key=lambda item: (-item[0], item[1]))
        result.append({other_index for _, other_index in scored[:k]})
    return result


def _overlap_score(source_neighbors: list[set[int]], target_neighbors: list[set[int]],
                   permutation: list[int] | None = None) -> float:
    count = len(source_neighbors)
    if permutation is None:
        permutation = list(range(count))
    inverse = [0] * count
    for source_index, target_index in enumerate(permutation):
        inverse[target_index] = source_index
    k = len(source_neighbors[0])
    scores = []
    for source_index in range(count):
        target_index = permutation[source_index]
        mapped = {inverse[index] for index in target_neighbors[target_index]}
        scores.append(len(source_neighbors[source_index] & mapped) / k)
    return math.fsum(scores) / len(scores)


def cross_space_knn_overlap(source_rows: list[list[float]], target_rows: list[list[float]],
                            *, k: int = 3, permutations: int = 100, seed: int = 17) -> dict[str, Any]:
    """Compare same-source neighbourhoods across different feature dimensions.

    This is a transparent kNN-overlap proxy, not a claim to reproduce the
    paper's exact mutual-kNN implementation or to measure semantic utility.
    """
    if len(source_rows) != len(target_rows):
        raise AuditError("source/target sample counts differ")
    count = len(source_rows)
    if count < 3:
        raise AuditError("at least three paired source groups are required")
    if type(k) is not int or not 1 <= k < count:
        raise AuditError("k must be between 1 and paired_count-1")
    if type(permutations) is not int or not 1 <= permutations <= MAX_PERMUTATIONS:
        raise AuditError("permutation count is outside the bound")
    source_neighbors = _nearest_neighbors(source_rows, k)
    target_neighbors = _nearest_neighbors(target_rows, k)
    observed = _overlap_score(source_neighbors, target_neighbors)
    rng = random.Random(seed)
    null = []
    base = list(range(count))
    for _ in range(permutations):
        perm = base.copy()
        rng.shuffle(perm)
        null.append(_overlap_score(source_neighbors, target_neighbors, perm))
    ordered = sorted(null)
    p95_index = min(len(ordered) - 1, math.ceil(0.95 * len(ordered)) - 1)
    p_value = (1 + sum(value >= observed for value in null)) / (permutations + 1)
    return {
        "paired_sources": count,
        "k": k,
        "observed_overlap": observed,
        "permutation_null_mean": math.fsum(null) / len(null),
        "permutation_null_p95": ordered[p95_index],
        "empirical_p_value": p_value,
        "random_neighbor_chance": k / (count - 1),
        "permutations": permutations,
        "seed": seed,
    }


def _quantiles(values: list[float | None]) -> dict[str, float | None]:
    clean = sorted(float(value) for value in values if value is not None and math.isfinite(float(value)))
    if not clean:
        return {"median": None, "p95": None}
    index = min(len(clean) - 1, math.ceil(0.95 * len(clean)) - 1)
    return {"median": statistics.median(clean), "p95": clean[index]}


def load_tap_records(home: Path, *, max_records: int = MAX_RECORDS) -> list[dict[str, Any]]:
    """Read packet payloads through a read-only SQLite connection; never opens Store."""
    if type(max_records) is not int or not 1 <= max_records <= MAX_RECORDS:
        raise AuditError("max_records is outside the bound")
    home = home.resolve(strict=True)
    db_candidate = home / "data" / "db" / "brain.sqlite3"
    if db_candidate.is_symlink():
        raise AuditError("runtime database symlinks are refused")
    db_path = db_candidate.resolve(strict=True)
    uri = db_path.as_uri() + "?mode=ro"
    connection = sqlite3.connect(uri, uri=True, timeout=5.0)
    try:
        connection.execute("PRAGMA query_only=ON")
        rows = connection.execute(
            "SELECT created, payload FROM packets WHERE kind=? ORDER BY created DESC LIMIT ?",
            (PACKET_KIND, max_records),
        ).fetchall()
        return [{"created": created, "payload": json.loads(payload)} for created, payload in rows]
    finally:
        connection.close()


def audit_records(home: Path, records: list[dict[str, Any]], *, sender: str = "B1_DETAIL",
                  receiver: str = "B2_GIST", min_pairs: int = 20, max_pairs: int = MAX_SAMPLES,
                  k: int = 3, permutations: int = 100, seed: int = 17) -> dict[str, Any]:
    if sender not in SENDER_ROLES or receiver not in SENDER_ROLES or sender == receiver:
        raise AuditError("sender/receiver must be distinct B1/B2 roles")
    if type(min_pairs) is not int or min_pairs < 3:
        raise AuditError("min_pairs must be at least 3")
    if type(max_pairs) is not int or not 3 <= max_pairs <= MAX_SAMPLES:
        raise AuditError("max_pairs is outside the bound")
    if type(k) is not int or k < 1:
        raise AuditError("k must be a positive integer")
    if type(permutations) is not int or not 1 <= permutations <= MAX_PERMUTATIONS:
        raise AuditError("permutation count is outside the bound")

    latest: dict[tuple[tuple[str, str, int, int, str], str, str, str, str], tuple[tuple[int, str], dict[str, Any]]] = {}
    invalid_metadata = 0
    for record in records:
        packet = record.get("payload") if isinstance(record, dict) else None
        try:
            source_key, role, revision, event_id, generation_id = _validate_packet(packet)
            order = _packet_order(record.get("created"))
            key = (source_key, role, revision, event_id, generation_id)
            if key not in latest or order > latest[key][0]:
                latest[key] = (order, packet)
        except (AuditError, TypeError, KeyError, ValueError):
            invalid_metadata += 1

    by_event_source: dict[tuple[tuple[str, str, int, int, str], str, str], dict[str, dict[str, tuple[tuple[int, str], dict[str, Any]]]]] = defaultdict(
        lambda: defaultdict(dict)
    )
    for (source_key, role, revision, event_id, generation_id), value in latest.items():
        by_event_source[(source_key, event_id, generation_id)][role][revision] = value

    candidate_cohorts: dict[tuple[str, str], dict[tuple[str, str, int, int, str], tuple[tuple[int, str], dict[str, Any], dict[str, Any]]]] = defaultdict(dict)
    for (source_key, _event_id, _generation_id), roles in by_event_source.items():
        sender_items = roles.get(sender, {})
        receiver_items = roles.get(receiver, {})
        for sender_revision, (sender_order, sender_packet) in sender_items.items():
            for receiver_revision, (receiver_order, receiver_packet) in receiver_items.items():
                cohort_key = (sender_revision, receiver_revision)
                pair_order = max(sender_order, receiver_order)
                existing = candidate_cohorts[cohort_key].get(source_key)
                if existing is None or pair_order > existing[0]:
                    candidate_cohorts[cohort_key][source_key] = (pair_order, sender_packet, receiver_packet)

    # Only load a bounded cohort after metadata grouping. This avoids holding
    # thousands of full activation matrices in memory on mobile hardware.
    ranked = sorted(candidate_cohorts.items(), key=lambda item: (-len(item[1]), item[0]))[:MAX_COHORTS]
    cohorts = []
    invalid_blobs = 0
    for (sender_revision, receiver_revision), candidates in ranked:
        keys = sorted(candidates, key=lambda item: (item[1], item[2], item[3], item[4], item[0]))
        capped = len(keys) > max_pairs
        keys = keys[:max_pairs]
        sender_rows: list[list[float]] = []
        receiver_rows: list[list[float]] = []
        sender_ratios: list[float | None] = []
        receiver_ratios: list[float | None] = []
        sender_cosines: list[float | None] = []
        receiver_cosines: list[float | None] = []
        for source_key in keys:
            _, sender_packet, receiver_packet = candidates[source_key]
            try:
                sender_vectors, _ = _read_tap_blob(home, sender_packet)
                receiver_vectors, _ = _read_tap_blob(home, receiver_packet)
                sender_pooled, sender_ratio, sender_cosine = _pool_without_position0(sender_vectors)
                receiver_pooled, receiver_ratio, receiver_cosine = _pool_without_position0(receiver_vectors)
                sender_rows.append(sender_pooled)
                receiver_rows.append(receiver_pooled)
                sender_ratios.append(sender_ratio)
                receiver_ratios.append(receiver_ratio)
                sender_cosines.append(sender_cosine)
                receiver_cosines.append(receiver_cosine)
            except (AuditError, OSError, json.JSONDecodeError, TypeError, ValueError):
                invalid_blobs += 1

        count = len(sender_rows)
        cohort: dict[str, Any] = {
            "sender_model_revision": sender_revision,
            "receiver_model_revision": receiver_revision,
            "paired_sources": count,
            "candidate_paired_sources": len(candidates),
            "capped_at_max_pairs": capped,
            "max_cohorts_evaluated": MAX_COHORTS,
            "sender_position0_norm_ratio": _quantiles(sender_ratios),
            "receiver_position0_norm_ratio": _quantiles(receiver_ratios),
            "sender_all_vs_without_position0_cosine": _quantiles(sender_cosines),
            "receiver_all_vs_without_position0_cosine": _quantiles(receiver_cosines),
            "activation_kind": EXPECTED_NORMALIZATION,
            "position0_excluded_from_alignment_pool": True,
            "special_token_filter": "UNAVAILABLE_TOKENIZER_METADATA_NOT_STORED",
            "causal_transfer_proven": False,
            "semantic_utility_proven": False,
        }
        if count >= max(3, k + 1):
            cohort["alignment"] = cross_space_knn_overlap(
                sender_rows, receiver_rows, k=k, permutations=permutations, seed=seed,
            )
        else:
            cohort["alignment"] = None
        cohort["status"] = "MEASURED_ALIGNMENT_ONLY" if count >= min_pairs else "INSUFFICIENT_COHORT"
        cohorts.append(cohort)

    cohorts.sort(key=lambda item: (-item["paired_sources"], item["sender_model_revision"], item["receiver_model_revision"]))
    if not candidate_cohorts:
        status = "NO_PAIRED_TAPS" if latest else "NO_VALID_TAPS"
    elif not cohorts or cohorts[0]["paired_sources"] == 0:
        status = "NO_VALID_PAIRED_BLOBS"
    elif cohorts[0]["paired_sources"] < min_pairs:
        status = "INSUFFICIENT_COHORT"
    else:
        status = "MEASURED_ALIGNMENT_ONLY"
    return {
        "schema": "v14.latent-alignment-audit/1",
        "status": status,
        "sender_role": sender,
        "receiver_role": receiver,
        "cohorts": cohorts,
        "metadata_valid_tap_packets": len(latest),
        "max_records_scanned": len(records),
        "max_pairs_per_cohort": max_pairs,
        "invalid_metadata_packets": invalid_metadata,
        "invalid_or_unreadable_paired_blobs": invalid_blobs,
        "limits": {
            "read_only_sqlite": True,
            "source_text_read": False,
            "raw_vectors_exported": False,
            "model_loaded": False,
            "network_used": False,
            "weights_modified": False,
            "projection_training_performed": False,
            "train_test_split_performed": False,
            "production_route": False,
            "training_authority": 0,
            "native_receiver_authority": 0,
            "alignment_is_not_semantic_utility": True,
            "alignment_is_not_causal_generation_transfer": True,
            "not_the_paper_exact_mutual_knn_implementation": True,
        },
    }


def audit_home(home: Path, **kwargs: Any) -> dict[str, Any]:
    return audit_records(home, load_tap_records(home), **kwargs)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--home", required=True, type=Path, help="existing V13 runtime home (read-only)")
    parser.add_argument("--sender", choices=sorted(SENDER_ROLES), default="B1_DETAIL")
    parser.add_argument("--receiver", choices=sorted(SENDER_ROLES), default="B2_GIST")
    parser.add_argument("--min-pairs", type=int, default=20)
    parser.add_argument("--max-pairs", type=int, default=MAX_SAMPLES)
    parser.add_argument("--k", type=int, default=3)
    parser.add_argument("--permutations", type=int, default=100)
    parser.add_argument("--seed", type=int, default=17)
    args = parser.parse_args(argv)
    try:
        result = audit_home(
            args.home, sender=args.sender, receiver=args.receiver,
            min_pairs=args.min_pairs, max_pairs=args.max_pairs,
            k=args.k, permutations=args.permutations, seed=args.seed,
        )
    except (AuditError, OSError, sqlite3.Error, json.JSONDecodeError) as exc:
        print(json.dumps({"schema": "v14.latent-alignment-audit/1", "status": "ERROR",
                          "error_type": type(exc).__name__}, sort_keys=True))
        return 2
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0 if result["status"] == "MEASURED_ALIGNMENT_ONLY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
