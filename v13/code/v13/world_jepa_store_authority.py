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
MAX_ACTION_SOURCE_REFS = 64
_SOURCE_REF_KEYS = {"source_id", "sha256", "char_start", "char_end", "modality"}


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


def _validated_source_ref(store, value):
    if type(value) is not dict or set(value) != _SOURCE_REF_KEYS:
        raise ValueError("ActionSelection source ref shape")
    source_id, source_sha = value.get("source_id"), value.get("sha256")
    start, end, modality = value.get("char_start"), value.get("char_end"), value.get("modality")
    if (type(source_id) is not str or not source_id or len(source_id) > 256
            or type(source_sha) is not str or not _HEX64.fullmatch(source_sha)
            or type(start) is not int or type(end) is not int or not 0 <= start <= end
            or type(modality) is not str or not modality or len(modality) > 64):
        raise ValueError("ActionSelection source ref identity")
    if type(store.read_source(value)) is not str:
        raise ValueError("ActionSelection source ref read")
    return {
        "source_id": source_id, "sha256": source_sha,
        "char_start": start, "char_end": end, "modality": modality,
    }


def _focal_cycle_source_refs(store, event_id, generation_id, action_created):
    """Recover final C4 coalition sources and prove the FocalCycle list was not truncated."""
    rows = store.rows(
        """SELECT payload FROM packets
           WHERE kind='FocalCycle' AND event_id=? AND generation_id=? AND created<=?
           ORDER BY created DESC,rowid DESC LIMIT 17""",
        (event_id, generation_id, action_created),
    )
    if type(rows) is not list or len(rows) >= 17:
        raise ValueError("FocalCycle source scan bound")
    if not rows:
        return []

    cycle_row = _mapping(rows[0], "FocalCycle source row")
    cycle = _object(cycle_row.get("payload"), "FocalCycle source payload")
    if (cycle.get("event_id") != event_id
            or cycle.get("brain_generation_id") != generation_id):
        raise ValueError("FocalCycle source binding")
    cycle_index = cycle.get("cycle")
    coalition = cycle.get("coalition")
    if (type(cycle_index) is not int or cycle_index < 0
            or type(coalition) is not list or len(coalition) > 64
            or any(type(item_id) is not str or not item_id or len(item_id) > 256
                   for item_id in coalition)
            or len(set(coalition)) != len(coalition)):
        raise ValueError("FocalCycle coalition")
    raw_cycle_refs = cycle.get("provenance")
    if (type(raw_cycle_refs) is not list
            or len(raw_cycle_refs) > MAX_ACTION_SOURCE_REFS):
        raise ValueError("FocalCycle source refs")
    if not coalition:
        if raw_cycle_refs:
            raise ValueError("empty FocalCycle coalition has source refs")
        return []

    item_rows = store.rows(
        """SELECT payload FROM packets
           WHERE kind='FocalItem' AND event_id=? AND generation_id=? AND created<=?
           ORDER BY created DESC,rowid DESC LIMIT 65""",
        (event_id, generation_id, action_created),
    )
    if type(item_rows) is not list or len(item_rows) >= 65:
        raise ValueError("FocalItem source scan bound")
    by_id = {}
    for raw in item_rows:
        item_row = _mapping(raw, "FocalItem source row")
        item = _object(item_row.get("payload"), "FocalItem source payload")
        if (item.get("event_id") != event_id
                or item.get("brain_generation_id") != generation_id):
            raise ValueError("FocalItem source binding")
        item_id = item.get("item_id")
        if item_id not in coalition:
            continue
        if item_id in by_id:
            raise ValueError("duplicate FocalItem coalition member")
        raw_item_refs = item.get("source_refs")
        if (type(raw_item_refs) is not list
                or not 1 <= len(raw_item_refs) <= MAX_ACTION_SOURCE_REFS
                or item.get("provenance") != raw_item_refs):
            raise ValueError("FocalItem source refs")
        item_refs = []
        item_seen = set()
        for raw_ref in raw_item_refs:
            ref = _validated_source_ref(store, raw_ref)
            key = (ref["source_id"], ref["sha256"], ref["char_start"],
                   ref["char_end"], ref["modality"])
            if key not in item_seen:
                item_seen.add(key)
                item_refs.append(ref)
        if not item_refs:
            raise ValueError("empty FocalItem source refs")
        by_id[item_id] = item_refs
    if set(by_id) != set(coalition):
        raise ValueError("FocalCycle coalition member missing FocalItem")

    coalition_keys = set()
    coalition_hashes = {}
    for item_id in coalition:
        for ref in by_id[item_id]:
            key = (ref["source_id"], ref["sha256"], ref["char_start"],
                   ref["char_end"], ref["modality"])
            prior = coalition_hashes.get(ref["source_id"])
            if prior is not None and prior != ref["sha256"]:
                raise ValueError("FocalItem source digest changed")
            coalition_hashes[ref["source_id"]] = ref["sha256"]
            coalition_keys.add(key)

    cycle_refs = []
    cycle_seen = set()
    cycle_hashes = {}
    for raw_ref in raw_cycle_refs:
        ref = _validated_source_ref(store, raw_ref)
        key = (ref["source_id"], ref["sha256"], ref["char_start"],
               ref["char_end"], ref["modality"])
        prior = cycle_hashes.get(ref["source_id"])
        if prior is not None and prior != ref["sha256"]:
            raise ValueError("FocalCycle source digest changed")
        cycle_hashes[ref["source_id"]] = ref["sha256"]
        if key not in cycle_seen:
            cycle_seen.add(key)
            cycle_refs.append(ref)
    if cycle_seen != coalition_keys:
        # The current C4 producer caps FocalCycle provenance at 16 refs. Compare
        # it with the full FocalItem union so a truncated list cannot certify
        # incomplete JEPA training lineage.
        raise ValueError("FocalCycle provenance does not cover its coalition")
    if len(cycle_seen) > MAX_ACTION_SOURCE_REFS:
        raise ValueError("FocalCycle source ref bound")
    return cycle_refs


def _selection_source_refs(store, event_id, generation_id, action_created, event_source_ref):
    rows = store.rows(
        """SELECT payload FROM packets
           WHERE kind='ActionSelection' AND event_id=? AND generation_id=? AND created<=?
           ORDER BY created DESC LIMIT 17""",
        (event_id, generation_id, action_created),
    )
    if type(rows) is not list or len(rows) >= 17:
        raise ValueError("ActionSelection source scan bound")
    committed = []
    for raw in rows:
        packet_row = _mapping(raw, "ActionSelection source row")
        selection = _object(packet_row.get("payload"), "ActionSelection source payload")
        if (selection.get("event_id") != event_id
                or selection.get("brain_generation_id") != generation_id):
            raise ValueError("ActionSelection source binding")
        stage = selection.get("stage")
        if stage not in (None, "PREDICTION", "COMMIT"):
            raise ValueError("ActionSelection source stage")
        if stage != "PREDICTION":
            committed.append(selection)
    if len(committed) != 1:
        raise ValueError("ActionSelection source cardinality")
    raw_refs = committed[0].get("provenance")
    if type(raw_refs) is not list or not 1 <= len(raw_refs) <= MAX_ACTION_SOURCE_REFS:
        raise ValueError("ActionSelection source refs")
    refs, seen, source_hashes = [], set(), {}
    for raw_ref in raw_refs:
        ref = _validated_source_ref(store, raw_ref)
        key = (ref["source_id"], ref["sha256"], ref["char_start"],
               ref["char_end"], ref["modality"])
        if key in seen:
            raise ValueError("duplicate ActionSelection source ref")
        prior = source_hashes.get(ref["source_id"])
        if prior is not None and prior != ref["sha256"]:
            raise ValueError("ActionSelection source digest changed")
        source_hashes[ref["source_id"]] = ref["sha256"]
        seen.add(key)
        refs.append(ref)
    if event_source_ref not in refs:
        raise ValueError("ActionSelection omitted event source")

    # The current C5 producer can still write only the event SourceRef. The final
    # C4 FocalCycle and its FocalItem members preserve the source set admitted to
    # the selected coalition; merge it without changing Core-owned packet production.
    for ref in _focal_cycle_source_refs(
            store, event_id, generation_id, action_created):
        key = (ref["source_id"], ref["sha256"], ref["char_start"],
               ref["char_end"], ref["modality"])
        prior = source_hashes.get(ref["source_id"])
        if prior is not None and prior != ref["sha256"]:
            raise ValueError("FocalCycle source digest conflicts with ActionSelection")
        source_hashes[ref["source_id"]] = ref["sha256"]
        if key not in seen:
            if len(refs) >= MAX_ACTION_SOURCE_REFS:
                raise ValueError("merged action source ref bound")
            seen.add(key)
            refs.append(ref)

    refs.sort(key=lambda item: (
        item["source_id"], item["sha256"], item["char_start"],
        item["char_end"], item["modality"],
    ))
    return tuple(
        (item["source_id"], item["sha256"], item["char_start"],
         item["char_end"], item["modality"])
        for item in refs
    )

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
        value = {"action_id": self._proof.action_id, "event_id": self._proof.event_id,
                 "generation_id": self._proof.generation_id, "source_id": self._proof.source_id,
                 "source_sha256": self._proof.source_sha256, "outcome_sha256": self._proof.outcome_sha256}
        # Preserve the historical single-event-source fingerprint. Additional
        # admitted context refs become part of the immutable T8 identity.
        if len(self._proof.source_refs) > 1:
            value["source_refs"] = [list(item) for item in self._proof.source_refs]
        return _hash(value)

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
        return [
            {"source_id": item[0], "sha256": item[1], "char_start": item[2],
             "char_end": item[3], "modality": item[4]}
            for item in self._proof.source_refs
        ]

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
                "source_refs": self.source_refs,
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
    # ActionSelection refs are authoritative when present. The current C5 producer
    # can still be event-only, so also verify the final C4 FocalCycle against its
    # FocalItem members and merge that coalition lineage. Truncation or revocation
    # fails closed rather than certifying an incomplete JEPA training row.
    selected_source_refs = _selection_source_refs(
        store, meta["event_id"], meta["generation_id"], created, source_ref
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
                       source_start, source_end, source_modality, selected_source_refs,
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
