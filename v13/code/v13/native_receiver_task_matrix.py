"""In-memory eight-condition native receiver task-matrix helpers.

The cohort object can be shared by a local harness across Runtime sessions.
It is deliberately process-local: no receipt, text, token ID or vector is written
to disk, and it carries no production, training or B3 authority.
"""
from __future__ import annotations

from copy import deepcopy


CONDITIONS = (
    "NO_MESSAGE",
    "EXACT_MESSAGE",
    "LATENT_CANDIDATE",
    "ZERO",
    "SHUFFLE",
    "REPEAT",
    "OOD",
    "ENTITY_SUBSTITUTION",
)


class NativeReceiverTaskMatrixError(ValueError):
    pass


class NativeReceiverTaskScoreCohort:
    """Bounded ephemeral cohort holder shared across Runtime session objects."""

    def __init__(self):
        self._native_receiver_task_score_receipts = []

    def status(self):
        from .native_receiver_task_score import task_score_status
        return task_score_status(self)

    def evaluate(self):
        from .native_receiver_task_score import evaluate_task_score_cohort
        return evaluate_task_score_cohort(self)

    def clear(self):
        from .native_receiver_task_score import clear_task_score_cohort
        return clear_task_score_cohort(self)


def build_task_matrix_conditions(record, candidate_packet, control_packets):
    """Build exact, candidate and negative-control inputs without persisting vectors."""
    if not isinstance(record, dict) or not isinstance(record.get("pairs"), list) or not record["pairs"]:
        raise NativeReceiverTaskMatrixError("paired source record is required for EXACT_MESSAGE")
    if not isinstance(candidate_packet, dict):
        raise NativeReceiverTaskMatrixError("anchor-preserving candidate packet is required")
    vectors = candidate_packet.get("vectors")
    positions = candidate_packet.get("position_ids")
    input_dim = candidate_packet.get("input_dim")
    if (not isinstance(vectors, list) or len(vectors) < 2
            or type(input_dim) is not int or input_dim < 1
            or not isinstance(positions, list) or positions != list(range(len(vectors)))):
        raise NativeReceiverTaskMatrixError("candidate input needs at least two contiguous rows")
    if any(not isinstance(row, list) or len(row) != input_dim for row in vectors):
        raise NativeReceiverTaskMatrixError("candidate vector dimensions are inconsistent")

    exact = [pair.get("receiver_vector") for pair in record["pairs"] if isinstance(pair, dict)]
    if (len(exact) != len(vectors)
            or any(not isinstance(row, list) or len(row) != input_dim for row in exact)):
        raise NativeReceiverTaskMatrixError("exact receiver rows do not align with candidate rows")

    if not isinstance(control_packets, dict) or set(control_packets) != {"OOD", "ENTITY_SUBSTITUTION"}:
        raise NativeReceiverTaskMatrixError("OOD and entity-substitution source packets are required")
    controls = {}
    for condition in ("OOD", "ENTITY_SUBSTITUTION"):
        item = control_packets[condition]
        packet = item.get("packet") if isinstance(item, dict) else None
        source_ref = item.get("source_ref") if isinstance(item, dict) else None
        control_vectors = packet.get("vectors") if isinstance(packet, dict) else None
        control_positions = packet.get("position_ids") if isinstance(packet, dict) else None
        if (not isinstance(source_ref, dict) or not isinstance(source_ref.get("source_id"), str)
                or not isinstance(source_ref.get("sha256"), str) or len(source_ref["sha256"]) != 64
                or not isinstance(control_vectors, list) or not control_vectors
                or not isinstance(control_positions, list)
                or control_positions != list(range(len(control_vectors)))
                or packet.get("input_dim") != input_dim
                or any(not isinstance(row, list) or len(row) != input_dim for row in control_vectors)):
            raise NativeReceiverTaskMatrixError(condition + " control packet/source is malformed")
        controls[condition] = {
            "vectors": deepcopy(control_vectors),
            "position_ids": list(control_positions),
            "source_ref": {"source_id": source_ref["source_id"], "sha256": source_ref["sha256"]},
        }

    source_ref = record.get("source_ref")
    if (not isinstance(source_ref, dict) or not isinstance(source_ref.get("source_id"), str)
            or not isinstance(source_ref.get("sha256"), str) or len(source_ref["sha256"]) != 64):
        raise NativeReceiverTaskMatrixError("original source reference is malformed")
    if any(controls[name]["source_ref"]["sha256"] == source_ref["sha256"] for name in controls):
        raise NativeReceiverTaskMatrixError("negative controls must use distinct source content")
    if controls["OOD"]["source_ref"]["sha256"] == controls["ENTITY_SUBSTITUTION"]["source_ref"]["sha256"]:
        raise NativeReceiverTaskMatrixError("OOD and entity-substitution controls must be distinct sources")

    zero = [[0.0] * input_dim for _ in vectors]
    shuffled = list(reversed(deepcopy(vectors)))
    repeated = [list(vectors[0]) for _ in vectors]
    conditions = [
        {"condition": "NO_MESSAGE", "vectors": [], "position_ids": []},
        {"condition": "EXACT_MESSAGE", "vectors": deepcopy(exact), "position_ids": list(range(len(exact)))},
        {"condition": "LATENT_CANDIDATE", "vectors": deepcopy(vectors), "position_ids": list(positions)},
        {"condition": "ZERO", "vectors": zero, "position_ids": list(positions)},
        {"condition": "SHUFFLE", "vectors": shuffled, "position_ids": list(positions)},
        {"condition": "REPEAT", "vectors": repeated, "position_ids": list(positions)},
        {"condition": "OOD", "vectors": controls["OOD"]["vectors"], "position_ids": controls["OOD"]["position_ids"]},
        {"condition": "ENTITY_SUBSTITUTION", "vectors": controls["ENTITY_SUBSTITUTION"]["vectors"],
         "position_ids": controls["ENTITY_SUBSTITUTION"]["position_ids"]},
    ]
    message_sources = {
        "NO_MESSAGE": None,
        "EXACT_MESSAGE": {"source_id": source_ref["source_id"], "sha256": source_ref["sha256"]},
        "LATENT_CANDIDATE": {"source_id": source_ref["source_id"], "sha256": source_ref["sha256"]},
        "ZERO": {"source_id": source_ref["source_id"], "sha256": source_ref["sha256"]},
        "SHUFFLE": {"source_id": source_ref["source_id"], "sha256": source_ref["sha256"]},
        "REPEAT": {"source_id": source_ref["source_id"], "sha256": source_ref["sha256"]},
        "OOD": controls["OOD"]["source_ref"],
        "ENTITY_SUBSTITUTION": controls["ENTITY_SUBSTITUTION"]["source_ref"],
    }
    return conditions, message_sources
