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
_OBSERVED_LEARNING_STATUSES = {"FINAL", "FAILED", "ERROR", "DEADLINE", "REJECTED"}
MAX_ACTION_OUTCOMES_PER_EVENT = 4096
MAX_SOURCE_REFS_PER_ACTION = 16


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
    source_char_start: int
    source_char_end: int
    source_modality: str
    source_refs: tuple
    selection_sha256: str
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
    def event_id(self):
        return self._proof.event_id

    @property
    def generation_id(self):
        return self._proof.generation_id

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
                      "source_sha256": self._proof.source_sha256,
                      "source_refs": list(self._proof.source_refs),
                      "selection_sha256": self._proof.selection_sha256,
                      "outcome_sha256": self._proof.outcome_sha256})

    @property
    def source_ref(self):
        # Consumers comparing packet provenance need the complete SourceRef,
        # not only its identity/digest pair. The verifier below has already
        # validated the exact span and modality against Store.read_source().
        return {
            "source_id": self._proof.source_id,
            "sha256": self._proof.source_sha256,
            "char_start": self._proof.source_char_start,
            "char_end": self._proof.source_char_end,
            "modality": self._proof.source_modality,
        }

    @property
    def source_refs(self):
        return [dict(ref) for ref in self._proof.source_refs]

    @property
    def evidence_ref(self):
        return "T8:" + self._proof.action_id + ":" + self._proof.outcome_sha256

    def training_row(self):
        if self._seal is not _SEAL:
            raise PermissionError("unissued receipt")
        row = dict(self._row)
        row["source_refs"] = self.source_refs
        return row

    def public_provenance(self):
        return {"event_id": self._proof.event_id, "generation_id": self._proof.generation_id,
                "source_id": self._proof.source_id, "source_sha256": self._proof.source_sha256,
                "source_refs": self.source_refs,
                "selection_sha256": self._proof.selection_sha256,
                "outcome_sha256": self._proof.outcome_sha256}


def _verified_selection_sources(store, event_id, generation_id, created, primary_ref, route):
    """Return the committed ActionSelection's complete, source-verified influence set.

    The EventEnvelope still has exactly one ingress source. The ActionSelection
    provenance may additionally name the bounded Memory/observer/workspace
    sources that actually influenced the selected action. Until the Core
    producer supplies those refs, the legacy one-source form remains valid.
    """
    rows = store.rows(
        """SELECT payload,created FROM packets
           WHERE kind='ActionSelection' AND event_id=? AND generation_id=? AND created<=?
           ORDER BY created DESC LIMIT 17""",
        (event_id, generation_id, created),
    )
    if type(rows) is not list or len(rows) >= 17:
        raise ValueError("ActionSelection scan bound")
    committed = []
    for raw in rows:
        item = _mapping(raw, "ActionSelection row")
        payload = _object(item.get("payload"), "ActionSelection payload")
        if (payload.get("event_id") != event_id
                or payload.get("brain_generation_id") != generation_id):
            raise ValueError("ActionSelection binding")
        stage = payload.get("stage")
        if stage not in (None, "PREDICTION", "COMMIT"):
            raise ValueError("ActionSelection stage")
        if stage != "PREDICTION":
            committed.append(payload)
    if len(committed) != 1:
        raise ValueError("committed ActionSelection cardinality")
    selection = committed[0]
    if selection.get("route_hint") != route:
        raise ValueError("ActionSelection route mismatch")
    refs = selection.get("provenance")
    if (type(refs) is not list or not 1 <= len(refs) <= MAX_SOURCE_REFS_PER_ACTION
            or refs[0] != primary_ref):
        raise ValueError("ActionSelection source provenance")
    normalized, seen = [], set()
    for ref in refs:
        if (type(ref) is not dict
                or set(ref) != {"source_id", "sha256", "char_start", "char_end", "modality"}):
            raise ValueError("ActionSelection SourceRef shape")
        source_id, source_sha = ref.get("source_id"), ref.get("sha256")
        start, end, modality = ref.get("char_start"), ref.get("char_end"), ref.get("modality")
        if (type(source_id) is not str or not source_id or len(source_id) > 256
                or type(source_sha) is not str or not _HEX64.fullmatch(source_sha)
                or type(start) is not int or type(end) is not int or not 0 <= start <= end
                or type(modality) is not str or not modality):
            raise ValueError("ActionSelection SourceRef identity")
        identity = (source_id, source_sha, start, end, modality)
        if identity in seen:
            raise ValueError("duplicate ActionSelection SourceRef")
        seen.add(identity)
        if type(store.read_source(ref)) is not str:
            raise ValueError("ActionSelection source read")
        normalized.append(dict(ref))
    return tuple(normalized), _hash(selection)


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
    source_start, source_end, source_modality = (
        source_ref.get("char_start"), source_ref.get("char_end"), source_ref.get("modality"))
    if (type(source_id) is not str or source_id != meta.get("source_id")
            or type(source_sha) is not str or not _HEX64.fullmatch(source_sha)
            or type(source_start) is not int or type(source_end) is not int
            or not 0 <= source_start <= source_end
            or type(source_modality) is not str or not source_modality):
        raise ValueError("source identity/span")
    # V13 Store._event_in_tx persists packet-level provenance, not source_refs.
    source_refs = event.get("provenance")
    if type(source_refs) is not list or len(source_refs) != 1 or source_refs[0] != source_ref:
        raise ValueError("event provenance")
    # Store.read_source verifies source row, blob digest and span; text is discarded.
    if type(store.read_source(source_ref)) is not str:
        raise ValueError("source read")
    source_refs, selection_sha = _verified_selection_sources(
        store, meta["event_id"], meta["generation_id"], float(created), source_ref, row["a"]
    )
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
                       source_start, source_end, source_modality, source_refs, selection_sha,
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


def _transition_from_action_row(store, raw_row):
    row = _mapping(raw_row, "action page row")
    action_id, status, created = row.get("id"), row.get("status"), row.get("created")
    if (type(action_id) is not str or not action_id or len(action_id) > 128
            or status not in _TERMINAL
            or type(created) not in (int, float) or not math.isfinite(created)):
        raise ValueError("terminal action identity")
    expected, actual = _object(row.get("expected"), "expected"), _object(row.get("outcome"), "actual")
    forecast = expected.get("forecast")
    if type(forecast) is not dict:
        raise ValueError("forecast")
    censored_statuses = {"CANCELLED", "ABORTED", "OUTCOME_UNKNOWN", "INTERRUPTED"}
    duration = actual.get("action_duration_s")
    characters = actual.get("characters")
    if status in censored_statuses:
        duration = 0 if duration is None else duration
        characters = 0 if characters is None else characters
    if (not world_model._finite_nonnegative(forecast.get("input_chars"))
            or not world_model._finite_nonnegative(duration)
            or not world_model._finite_nonnegative(characters)):
        raise ValueError("terminal action numeric")
    resource = forecast.get("resource_state", "NORMAL")
    if type(resource) is not str:
        raise ValueError("resource state")
    selections = store.rows(
        """SELECT payload FROM packets
           WHERE kind='ActionSelection' AND event_id=? AND generation_id=? AND created<=?
           ORDER BY created DESC LIMIT 17""",
        (row.get("event_id"), row.get("generation_id"), created),
    )
    if type(selections) is not list or len(selections) >= 17:
        raise ValueError("ActionSelection scan bound")
    committed = []
    for raw_selection in selections:
        selection_row = _mapping(raw_selection, "ActionSelection row")
        selected = _object(selection_row.get("payload"), "ActionSelection payload")
        if (selected.get("event_id") != row.get("event_id")
                or selected.get("brain_generation_id") != row.get("generation_id")):
            raise ValueError("ActionSelection binding")
        stage = selected.get("stage")
        if stage not in (None, "PREDICTION", "COMMIT"):
            raise ValueError("ActionSelection stage")
        if stage != "PREDICTION":
            committed.append(selected)
    if len(committed) != 1:
        raise ValueError("committed ActionSelection cardinality")
    route = committed[0].get("route_hint")
    if route not in world_model.ACTIONS:
        raise ValueError("ActionSelection route")
    hour = (float(created) % 86400.0) / 3600.0
    latent_record = forecast.get("learned_latent_prediction") or {}
    latent = latent_record.get("latent") if type(latent_record) is dict else None
    if not isinstance(latent, list) or not latent or not world_model._finite_vector(latent, len(latent)):
        latent = None
    return {
        "action_id": action_id,
        "s": world_model.state_vec(forecast["input_chars"], resource, hour),
        "a": route,
        "y": [math.log1p(float(duration)),
              1.0 if status == "FINAL" else 0.0,
              math.log1p(float(characters)) / 8.0],
        "latent": latent,
    }


def verify_committed_transition_page(store, *, after_seq=0, limit=world_model.MAX_ROWS):
    """Oldest-first source-verified T8 page; censored outcomes never enter learning IDs."""
    if type(after_seq) is not int or after_seq < 0:
        raise ValueError("after_seq")
    if type(limit) is not int or not 1 <= limit <= world_model.MAX_ROWS:
        raise ValueError("limit")
    if not all(callable(getattr(store, name, None)) for name in ("one", "rows", "read_source")):
        raise TypeError("Store reader API required")
    rows = store.rows(
        """SELECT a.rowid AS scan_seq,a.id,a.event_id,a.status,a.expected,a.outcome,a.created,
                  e.generation_id
           FROM actions a JOIN events e ON e.id=a.event_id
           WHERE a.rowid>? AND a.outcome IS NOT NULL AND a.expected LIKE ?
             AND a.status IN ('FINAL','FAILED','ERROR','DEADLINE','REJECTED')
           ORDER BY a.rowid ASC LIMIT ?""",
        (after_seq, '%"forecast"%', limit + 1),
    )
    if type(rows) is not list:
        raise ValueError("T8 page")
    has_more = len(rows) > limit
    page = rows[:limit]
    if not page:
        return [], 0, after_seq, 0, 0, False
    next_cursor, verified, rejected, seen = after_seq, [], 0, set()
    for raw_row in page:
        try:
            action_row = _mapping(raw_row, "action page row")
            scan_seq = action_row.get("scan_seq")
            if type(scan_seq) is not int or scan_seq <= next_cursor:
                raise ValueError("T8 scan sequence")
            next_cursor = scan_seq
            receipt = _verify_one(store, _transition_from_action_row(store, action_row))
            if receipt.action_id in seen:
                raise ValueError("duplicate action in page")
            seen.add(receipt.action_id)
            verified.append(receipt)
        except (ValueError, TypeError, KeyError, OSError, OverflowError, json.JSONDecodeError):
            rejected += 1
    skipped = store.one(
        """SELECT COUNT(*) AS n FROM actions
           WHERE rowid>? AND rowid<=? AND outcome IS NOT NULL AND expected LIKE ?
             AND status IN ('CANCELLED','ABORTED','OUTCOME_UNKNOWN','INTERRUPTED')""",
        (after_seq, next_cursor, '%"forecast"%'),
    )
    skipped_row = _mapping(skipped, "censored count") if skipped else {"n": 0}
    censored_skipped = skipped_row.get("n", 0)
    if type(censored_skipped) is not int or censored_skipped < 0:
        raise ValueError("censored count")
    return verified, rejected, next_cursor, len(page), censored_skipped, has_more
def verify_committed_temporal_page(store, *, after_seq=0, limit=64):
    """Oldest-first page of verified terminal outcomes, including censored ledger-only records."""
    if type(after_seq) is not int or after_seq < 0:
        raise ValueError("after_seq")
    if type(limit) is not int or not 1 <= limit <= 64:
        raise ValueError("limit")
    if not all(callable(getattr(store, name, None)) for name in ("one", "rows", "read_source")):
        raise TypeError("Store reader API required")
    rows = store.rows(
        """SELECT a.rowid AS scan_seq,a.id,a.event_id,a.status,a.expected,a.outcome,a.created,
                  e.generation_id
           FROM actions a JOIN events e ON e.id=a.event_id
           WHERE a.rowid>? AND a.outcome IS NOT NULL AND a.expected LIKE ?
             AND a.status IN ('FINAL','FAILED','ERROR','DEADLINE','REJECTED',
                              'CANCELLED','ABORTED','OUTCOME_UNKNOWN','INTERRUPTED')
           ORDER BY a.rowid ASC LIMIT ?""",
        (after_seq, '%"forecast"%', limit + 1),
    )
    if type(rows) is not list:
        raise ValueError("T8 temporal page")
    has_more = len(rows) > limit
    page = rows[:limit]
    if not page:
        return [], 0, after_seq, 0, 0, False
    next_cursor, verified, rejected, censored_observed, seen = after_seq, [], 0, 0, set()
    censored = {"CANCELLED", "ABORTED", "OUTCOME_UNKNOWN", "INTERRUPTED"}
    for raw_row in page:
        try:
            action_row = _mapping(raw_row, "action temporal page row")
            scan_seq = action_row.get("scan_seq")
            if type(scan_seq) is not int or scan_seq <= next_cursor:
                raise ValueError("T8 temporal scan sequence")
            next_cursor = scan_seq
            receipt = _verify_one(store, _transition_from_action_row(store, action_row))
            if receipt.action_id in seen:
                raise ValueError("duplicate action in temporal page")
            seen.add(receipt.action_id)
            if receipt.status in censored:
                censored_observed += 1
            verified.append(receipt)
        except (ValueError, TypeError, KeyError, OSError, OverflowError, json.JSONDecodeError):
            rejected += 1
    return verified, rejected, next_cursor, len(page), censored_observed, has_more
