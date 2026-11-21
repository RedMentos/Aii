"""V14 source-bound authority for committed V13 T8 transitions.

world_model.transitions() validates the forecast and committed ActionSelection.
This adapter additionally binds each row to the persisted event source,
CorollaryCopy and exactly one matching ActionOutcome packet. It is an in-process
provenance check, not a security boundary against arbitrary code in the process.
"""
from dataclasses import dataclass
import hashlib
import json
import math
import re
from v13 import world_model

_HEX64 = re.compile(r"[0-9a-f]{64}\Z")
_SEAL = object()
_TERMINAL = {"FINAL", "FAILED", "CANCELLED", "ERROR", "DEADLINE", "INTERRUPTED", "OUTCOME_UNKNOWN", "ABORTED", "REJECTED"}
MAX_ACTION_OUTCOMES_PER_EVENT = 4096


def _unique(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise ValueError("duplicate JSON key")
        out[key] = value
    return out


def _object(raw, name):
    if type(raw) is dict:
        return raw
    if type(raw) is not str:
        raise ValueError(name)
    value = json.loads(raw, object_pairs_hook=_unique)
    if type(value) is not dict:
        raise ValueError(name)
    return value


def _mapping(row, name):
    """Normalize Store dict/SQLite Row results without assuming dict.get()."""
    if type(row) is dict:
        return row
    try:
        return {key: row[key] for key in row.keys()}
    except Exception as exc:
        raise ValueError(name) from exc


def _hash(value):
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _vector(value, size):
    return (isinstance(value, (list, tuple)) and len(value) == size
            and all(type(x) in (int, float) and math.isfinite(x) for x in value))


@dataclass(frozen=True)
class Provenance:
    action_id: str
    event_id: str
    generation_id: str
    source_id: str
    source_sha256: str
    outcome_sha256: str
    created: float
    outcome_created: float
    status: str
    actual: dict


class VerifiedT8Transition:
    __slots__ = ("_row", "_proof", "_seal")

    def __init__(self, seal, row, proof):
        if seal is not _SEAL:
            raise TypeError("use verify_committed_transitions")
        object.__setattr__(self, "_row", dict(row))
        object.__setattr__(self, "_proof", proof)
        object.__setattr__(self, "_seal", seal)

    def __setattr__(self, name, value):
        raise AttributeError("immutable verified T8 transition")

    @property
    def action_id(self):
        return self._proof.action_id

    @property
    def outcome_created(self):
        return self._proof.outcome_created

    @property
    def status(self):
        return self._proof.status

    @property
    def actual(self):
        return dict(self._proof.actual)

    @property
    def created(self):
        return self._proof.created

    @property
    def fingerprint(self):
        return _hash({"action_id": self._proof.action_id, "event_id": self._proof.event_id,
                      "generation_id": self._proof.generation_id, "source_id": self._proof.source_id,
                      "source_sha256": self._proof.source_sha256, "outcome_sha256": self._proof.outcome_sha256})

    @property
    def source_ref(self):
        return {"source_id": self._proof.source_id, "sha256": self._proof.source_sha256}

    @property
    def evidence_ref(self):
        return "T8:" + self._proof.action_id + ":" + self._proof.outcome_sha256

    def training_row(self):
        if self._seal is not _SEAL:
            raise PermissionError("unissued receipt")
        return dict(self._row)

    def public_provenance(self):
        return {"event_id": self._proof.event_id, "generation_id": self._proof.generation_id,
                "source_id": self._proof.source_id, "source_sha256": self._proof.source_sha256,
                "outcome_sha256": self._proof.outcome_sha256}


def _verify_one(store, row):
    if type(row) is not dict:
        raise ValueError("transition shape")
    action_id = row.get("action_id")
    if type(action_id) is not str or not action_id or len(action_id) > 128:
        raise ValueError("action id")
    if row.get("a") not in world_model.ACTIONS or not _vector(row.get("s"), 4) or not _vector(row.get("y"), 3):
        raise ValueError("transition numeric")
    meta = store.one(
        """SELECT a.id AS action_id,a.event_id,a.status,a.expected,a.outcome,a.created,
                  a.corollary_id,e.generation_id,e.source_id,e.packet AS event_packet,
                  cp.kind AS corollary_kind,cp.payload AS corollary_payload
           FROM actions a JOIN events e ON e.id=a.event_id
           LEFT JOIN packets cp ON cp.id=a.corollary_id WHERE a.id=?""", (action_id,))
    if not meta:
        raise ValueError("action row missing")
    meta = _mapping(meta, "action row")
    if meta.get("action_id") != action_id:
        raise ValueError("action row identity")
    status = meta.get("status")
    if type(status) is not str or status not in _TERMINAL:
        raise ValueError("action not terminal")
    created = meta.get("created")
    if type(created) not in (int, float) or not math.isfinite(created):
        raise ValueError("action time")
    expected = _object(meta.get("expected"), "expected")
    actual = _object(meta.get("outcome"), "actual")
    event = _object(meta.get("event_packet"), "event packet")
    corollary = _object(meta.get("corollary_payload"), "corollary")
    if meta.get("corollary_kind") != "CorollaryCopy":
        raise ValueError("corollary kind")
    if (corollary.get("action_id") != action_id or corollary.get("event_id") != meta.get("event_id")
            or corollary.get("brain_generation_id") != meta.get("generation_id")
            or corollary.get("expected") != expected):
        raise ValueError("corollary mismatch")
    if event.get("event_id") != meta.get("event_id") or event.get("brain_generation_id") != meta.get("generation_id"):
        raise ValueError("event binding")
    source_ref = event.get("source_ref")
    if type(source_ref) is not dict:
        raise ValueError("source ref")
    source_id, source_sha = source_ref.get("source_id"), source_ref.get("sha256")
    if (type(source_id) is not str or source_id != meta.get("source_id")
            or type(source_sha) is not str or not _HEX64.fullmatch(source_sha)):
        raise ValueError("source identity")
    # V13 Store._event_in_tx persists packet-level provenance, not source_refs.
    source_refs = event.get("provenance")
    if type(source_refs) is not list or len(source_refs) != 1 or source_refs[0] != source_ref:
        raise ValueError("event provenance")
    # Store.read_source verifies source row, blob digest and span; text is discarded.
    if type(store.read_source(source_ref)) is not str:
        raise ValueError("source read")
    # Scan the complete event history up to a hard bound. A small LIMIT could
    # hide an older duplicate and incorrectly certify the remaining packet as
    # the unique ActionOutcome. Over-bound histories fail closed.
    packets = store.rows(
        """SELECT id,payload,created FROM packets WHERE kind='ActionOutcome' AND event_id=? AND generation_id=?
           ORDER BY created DESC LIMIT ?""",
        (meta["event_id"], meta["generation_id"], MAX_ACTION_OUTCOMES_PER_EVENT + 1))
    if type(packets) is not list or len(packets) > MAX_ACTION_OUTCOMES_PER_EVENT:
        raise ValueError("ActionOutcome scan bound")
    matching = []
    for packet_row in packets:
        packet_row = _mapping(packet_row, "ActionOutcome row")
        payload = _object(packet_row.get("payload"), "ActionOutcome")
        if payload.get("action_id") == action_id:
            matching.append((packet_row, payload))
    if len(matching) != 1:
        raise ValueError("ActionOutcome cardinality")
    outcome_row, outcome_packet = matching[0]
    outcome_created = outcome_row.get("created")
    if type(outcome_created) not in (int, float) or not math.isfinite(outcome_created):
        raise ValueError("ActionOutcome time")
    if (outcome_packet.get("event_id") != meta["event_id"]
            or outcome_packet.get("brain_generation_id") != meta["generation_id"]
            or outcome_packet.get("status") != status or outcome_packet.get("actual") != actual):
        raise ValueError("ActionOutcome mismatch")
    if row["y"][1] != (1.0 if status == "FINAL" else 0.0):
        raise ValueError("transition status mismatch")
    proof = Provenance(action_id, meta["event_id"], meta["generation_id"], source_id, source_sha,
                       _hash(outcome_packet), float(created), float(outcome_created), status, actual)
    return VerifiedT8Transition(_SEAL, row, proof)


def verify_rows(store, rows):
    """Verify a caller-selected bounded transition batch without rescanning T8."""
    if not all(callable(getattr(store, name, None)) for name in ("one", "rows", "read_source")):
        raise TypeError("Store reader API required")
    if type(rows) is not list:
        raise ValueError("T8 feed")
    verified, rejected, seen = [], 0, set()
    for row in rows:
        try:
            item = _verify_one(store, row)
            if item.action_id in seen:
                raise ValueError("duplicate action")
            seen.add(item.action_id)
            verified.append(item)
        except (ValueError, TypeError, KeyError, OSError, OverflowError, json.JSONDecodeError):
            rejected += 1
    return verified, rejected


def verify_committed_transitions(store, limit=world_model.MAX_ROWS):
    if type(limit) is not int or not 1 <= limit <= world_model.MAX_ROWS:
        raise ValueError("limit")
    return verify_rows(store, world_model.transitions(store, limit=limit))
