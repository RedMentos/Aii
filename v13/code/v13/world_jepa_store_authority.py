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
MAX_FOCAL_CYCLE_SOURCE_REFS = 16
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


def _focal_cycle_source_refs(store, event_id, generation_id, before_packet_rowid):
    """Return the bounded union of all source refs in the pre-action C4 trajectory.

    The final cycle is checked against its persisted FocalItem members. Earlier
    cycles have only their FocalCycle provenance list; because the producer caps
    that list at 16, an earlier cycle at the cap is ambiguous and fails closed.
    """
    if type(before_packet_rowid) is not int or before_packet_rowid < 1:
        raise ValueError("ActionSelection packet boundary")
    rows = store.rows(
        """SELECT rowid AS packet_rowid,payload FROM packets
           WHERE kind='FocalCycle' AND event_id=? AND generation_id=? AND rowid<?
             AND COALESCE(json_extract(payload,'$.stage'),'COMMIT')!='PREDICTION'
           ORDER BY rowid DESC LIMIT 17""",
        (event_id, generation_id, before_packet_rowid),
    )
    if type(rows) is not list or len(rows) >= 17:
        raise ValueError("FocalCycle source scan bound")
    if not rows:
        return []

    cycles = []
    for offset, raw in enumerate(rows):
        cycle_row = _mapping(raw, "FocalCycle source row")
        cycle = _object(cycle_row.get("payload"), "FocalCycle source payload")
        if (cycle.get("event_id") != event_id
                or cycle.get("brain_generation_id") != generation_id):
            raise ValueError("FocalCycle source binding")
        if cycle.get("stage") not in (None, "COMMIT"):
            raise ValueError("FocalCycle source stage")
        cycle_index = cycle.get("cycle")
        coalition = cycle.get("coalition")
        if (type(cycle_index) is not int or cycle_index < 1
                or cycle_index != len(rows) - offset
                or type(coalition) is not list or len(coalition) > 64
                or any(type(item_id) is not str or not item_id or len(item_id) > 256
                       for item_id in coalition)
                or len(set(coalition)) != len(coalition)):
            raise ValueError("FocalCycle trajectory/coalition")
        raw_refs = cycle.get("provenance")
        if (type(raw_refs) is not list
                or len(raw_refs) > MAX_FOCAL_CYCLE_SOURCE_REFS
                or bool(coalition) != bool(raw_refs)):
            raise ValueError("FocalCycle source refs")
        if offset > 0 and len(raw_refs) >= MAX_FOCAL_CYCLE_SOURCE_REFS:
            # Earlier cycles do not persist per-item FocalItem packets. At the
            # producer cap we cannot prove that their source list is complete.
            raise ValueError("historical FocalCycle provenance may be truncated")

        refs = []
        seen = set()
        source_hashes = {}
        for raw_ref in raw_refs:
            ref = _validated_source_ref(store, raw_ref)
            key = (ref["source_id"], ref["sha256"], ref["char_start"],
                   ref["char_end"], ref["modality"])
            prior = source_hashes.get(ref["source_id"])
            if prior is not None and prior != ref["sha256"]:
                raise ValueError("FocalCycle source digest changed")
            source_hashes[ref["source_id"]] = ref["sha256"]
            if key not in seen:
                seen.add(key)
                refs.append(ref)
        cycles.append((cycle, refs))

    # Only the final coalition has per-item receipts in the current producer.
    # Verify that its packet-level source list is the exact union of those
    # receipts; this catches the 16-ref producer cap rather than certifying a
    # truncated final coalition.
    final_cycle, final_refs = cycles[0]
    coalition = final_cycle["coalition"]
    if coalition:
        item_rows = store.rows(
            """SELECT payload FROM packets
               WHERE kind='FocalItem' AND event_id=? AND generation_id=? AND rowid<?
               ORDER BY rowid DESC LIMIT 65""",
            (event_id, generation_id, before_packet_rowid),
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
            item_hashes = {}
            for raw_ref in raw_item_refs:
                ref = _validated_source_ref(store, raw_ref)
                key = (ref["source_id"], ref["sha256"], ref["char_start"],
                       ref["char_end"], ref["modality"])
                prior = item_hashes.get(ref["source_id"])
                if prior is not None and prior != ref["sha256"]:
                    raise ValueError("FocalItem source digest changed")
                item_hashes[ref["source_id"]] = ref["sha256"]
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
        final_keys = {
            (ref["source_id"], ref["sha256"], ref["char_start"],
             ref["char_end"], ref["modality"])
            for ref in final_refs
        }
        if final_keys != coalition_keys:
            raise ValueError("FocalCycle provenance does not cover its coalition")
    elif final_refs:
        raise ValueError("empty final FocalCycle coalition has source refs")

    # Earlier-cycle provenance is part of the same causal trajectory as the
    # final coalition. Merge it into the immutable T8 receipt so source-disjoint
    # holdouts and the source-forget checkpoint guard see the same influence set.
    union = []
    union_seen = set()
    union_hashes = {}
    for _cycle, cycle_refs in cycles:
        for ref in cycle_refs:
            key = (ref["source_id"], ref["sha256"], ref["char_start"],
                   ref["char_end"], ref["modality"])
            prior = union_hashes.get(ref["source_id"])
            if prior is not None and prior != ref["sha256"]:
                raise ValueError("FocalCycle trajectory source digest changed")
            union_hashes[ref["source_id"]] = ref["sha256"]
            if key not in union_seen:
                if len(union) >= MAX_ACTION_SOURCE_REFS:
                    raise ValueError("FocalCycle trajectory source ref bound")
                union_seen.add(key)
                union.append(ref)
    return union



def _merge_context_source_refs(store, raw_refs, refs, seen, source_hashes, *, expand_body_state=True):
    if raw_refs is None:
        return
    if isinstance(raw_refs, dict):
        raw_refs = [raw_refs]
    if type(raw_refs) is not list or len(raw_refs) > MAX_ACTION_SOURCE_REFS:
        raise ValueError("context source ref list")
    for raw_ref in raw_refs:
        ref = _validated_source_ref(store, raw_ref)
        key = (ref["source_id"], ref["sha256"], ref["char_start"],
               ref["char_end"], ref["modality"])
        prior = source_hashes.get(ref["source_id"])
        if prior is not None and prior != ref["sha256"]:
            raise ValueError("context source digest changed")
        source_hashes[ref["source_id"]] = ref["sha256"]
        if key not in seen:
            if len(refs) >= MAX_ACTION_SOURCE_REFS:
                raise ValueError("merged context source ref bound")
            seen.add(key)
            refs.append(ref)
        if expand_body_state:
            _merge_body_state_nested_refs(
                store, ref, refs, seen, source_hashes
            )


def _merge_body_state_nested_refs(store, ref, refs, seen, source_hashes):
    source_row = store.one(
        "SELECT kind FROM sources WHERE id=?", (ref["source_id"],)
    )
    if not source_row:
        raise ValueError("body-state source row missing")
    source_row = _mapping(source_row, "body-state source row")
    if source_row.get("kind") != "BODY_STATE":
        return
    raw = store.read_source(ref)
    try:
        body = _object(raw, "body-state source")
    except (ValueError, TypeError, json.JSONDecodeError) as exc:
        raise ValueError("body-state source JSON") from exc
    audit = body.get("temporal_world_jepa_audit")
    if audit is None:
        return
    if type(audit) is not dict:
        raise ValueError("body-state temporal audit")
    # The compact prompt carries only hashes/IDs for the prediction history.
    # Rehydrate full, live SourceRefs from Store rows so deletion and holdout
    # logic see the same lineage that produced the receiver readout.
    for key in ("history_lineage_source_ids", "query_lineage_source_ids"):
        source_ids = audit.get(key, [])
        if type(source_ids) is not list or len(source_ids) > MAX_ACTION_SOURCE_REFS:
            raise ValueError("body-state lineage IDs")
        for source_id in source_ids:
            if type(source_id) is not str or not source_id or len(source_id) > 256:
                raise ValueError("body-state lineage source identity")
            row = store.one(
                "SELECT hash,chars,deleted FROM sources WHERE id=?", (source_id,)
            )
            if not row:
                raise ValueError("body-state lineage source missing")
            row = _mapping(row, "body-state lineage source")
            if row.get("deleted") or type(row.get("hash")) is not str:
                raise ValueError("body-state lineage source revoked")
            chars = row.get("chars")
            if type(chars) is not int or chars < 0:
                raise ValueError("body-state lineage source length")
            nested = {
                "source_id": source_id, "sha256": row["hash"],
                "char_start": 0, "char_end": chars, "modality": "text",
            }
            _merge_context_source_refs(
                store, [nested], refs, seen, source_hashes,
                expand_body_state=False,
            )
    recall = audit.get("episodic_recall")
    if recall is not None:
        if type(recall) is not dict:
            raise ValueError("body-state episodic audit")
        query_ids = recall.get("query_lineage_source_ids", [])
        if type(query_ids) is not list or len(query_ids) > MAX_ACTION_SOURCE_REFS:
            raise ValueError("body-state episodic query lineage")
        for source_id in query_ids:
            if type(source_id) is not str or not source_id or len(source_id) > 256:
                raise ValueError("body-state episodic source identity")
            row = store.one(
                "SELECT hash,chars,deleted FROM sources WHERE id=?", (source_id,)
            )
            if not row:
                raise ValueError("body-state episodic source missing")
            row = _mapping(row, "body-state episodic source")
            if row.get("deleted") or type(row.get("hash")) is not str:
                raise ValueError("body-state episodic source revoked")
            chars = row.get("chars")
            if type(chars) is not int or chars < 0:
                raise ValueError("body-state episodic source length")
            nested = {
                "source_id": source_id, "sha256": row["hash"],
                "char_start": 0, "char_end": chars, "modality": "text",
            }
            _merge_context_source_refs(
                store, [nested], refs, seen, source_hashes,
                expand_body_state=False,
            )
        items = recall.get("items", [])
        if type(items) is not list or len(items) > 8:
            raise ValueError("body-state episodic item bound")
        for item in items:
            if type(item) is not dict:
                raise ValueError("body-state episodic item")
            _merge_context_source_refs(
                store, item.get("source_ref"), refs, seen, source_hashes
            )
            _merge_context_source_refs(
                store, item.get("window_source_refs"), refs, seen, source_hashes
            )


def _context_packet(store, packet_id, expected_kinds, event_id, generation_id,
                    *, before_rowid=None):
    if type(packet_id) is not str or not packet_id or len(packet_id) > 256:
        raise ValueError("context packet identity")
    rows = store.rows(
        """SELECT rowid AS packet_rowid,id,kind,event_id,generation_id,payload
           FROM packets WHERE id=? LIMIT 2""",
        (packet_id,),
    )
    if type(rows) is not list or len(rows) != 1:
        raise ValueError("context packet cardinality")
    row = _mapping(rows[0], "context packet row")
    if (row.get("id") != packet_id or row.get("kind") not in expected_kinds
            or row.get("event_id") != event_id
            or row.get("generation_id") != generation_id):
        raise ValueError("context packet binding")
    packet_rowid = row.get("packet_rowid")
    if type(packet_rowid) is not int or packet_rowid < 1:
        raise ValueError("context packet row boundary")
    if before_rowid is not None and packet_rowid >= before_rowid:
        raise ValueError("context packet is not pre-selection")
    payload = _object(row.get("payload"), "context packet payload")
    if (payload.get("packet_id") != packet_id
            or payload.get("event_id") != event_id
            or payload.get("brain_generation_id") != generation_id):
        raise ValueError("context packet payload binding")
    return packet_rowid, payload


def _collect_context_broadcast(store, packet_id, event_id, generation_id,
                               before_rowid, refs, seen, source_hashes, visited):
    if packet_id in visited:
        return
    visited.add(packet_id)
    if len(visited) > 32:
        raise ValueError("context packet traversal bound")
    _rowid, payload = _context_packet(
        store, packet_id, {"JEFBroadcastPacket"}, event_id, generation_id,
        before_rowid=before_rowid,
    )
    _merge_context_source_refs(
        store, payload.get("provenance"), refs, seen, source_hashes
    )
    _merge_context_source_refs(
        store, payload.get("source_refs"), refs, seen, source_hashes
    )


def _collect_context_message(store, packet_id, event_id, generation_id,
                             before_rowid, refs, seen, source_hashes,
                             visited_messages, visited_offers, visited_queries,
                             visited_packets, depth):
    if depth > 4:
        raise ValueError("peer offer provenance depth")
    if packet_id in visited_messages:
        return
    visited_messages.add(packet_id)
    if len(visited_packets) >= 32:
        raise ValueError("context packet traversal bound")
    visited_packets.add(packet_id)
    _rowid, payload = _context_packet(
        store, packet_id, {"MessagePacket"}, event_id, generation_id,
        before_rowid=before_rowid,
    )
    _merge_context_source_refs(
        store, payload.get("provenance"), refs, seen, source_hashes
    )
    _merge_context_source_refs(
        store, payload.get("source_refs"), refs, seen, source_hashes
    )
    parent_offer_id = payload.get("parent_offer_packet_id")
    if parent_offer_id:
        _collect_context_offer(
            store, parent_offer_id, event_id, generation_id, before_rowid,
            refs, seen, source_hashes, visited_offers, visited_queries,
            visited_messages, visited_packets, depth + 1,
        )


def _collect_context_query(store, packet_id, event_id, generation_id,
                           before_rowid, refs, seen, source_hashes,
                           visited_offers, visited_queries, visited_messages,
                           visited_packets, depth, expected_role=None):
    if depth > 4:
        raise ValueError("query provenance depth")
    if packet_id in visited_queries:
        return
    visited_queries.add(packet_id)
    if len(visited_packets) >= 32:
        raise ValueError("context packet traversal bound")
    visited_packets.add(packet_id)
    _rowid, payload = _context_packet(
        store, packet_id, {"QueryPacket"}, event_id, generation_id,
        before_rowid=before_rowid,
    )
    target_role = payload.get("target_role")
    if expected_role is not None and target_role != expected_role:
        raise ValueError("OfferPacket/QueryPacket role mismatch")
    for key in ("provenance", "source_refs", "context_source_refs",
                "enlightened_source_refs", "bv_refs"):
        _merge_context_source_refs(
            store, payload.get(key), refs, seen, source_hashes
        )
    bodyview = payload.get("bodyview")
    if bodyview is not None:
        if type(bodyview) is not dict:
            raise ValueError("QueryPacket bodyview")
        for key in ("body_state_ref", "source_ref"):
            _merge_context_source_refs(
                store, bodyview.get(key), refs, seen, source_hashes
            )
        for key in ("source_refs", "provenance"):
            _merge_context_source_refs(
                store, bodyview.get(key), refs, seen, source_hashes
            )
    broadcast_id = payload.get("broadcast_packet_id")
    if broadcast_id:
        _collect_context_broadcast(
            store, broadcast_id, event_id, generation_id, before_rowid,
            refs, seen, source_hashes, visited_packets,
        )
    peer_id = payload.get("peer_message_packet_id")
    if peer_id:
        _collect_context_message(
            store, peer_id, event_id, generation_id, before_rowid,
            refs, seen, source_hashes, visited_messages, visited_offers,
            visited_queries, visited_packets, depth + 1,
        )
    context_offer_ids = payload.get("context_offer_ids", [])
    if type(context_offer_ids) is not list or len(context_offer_ids) > 16:
        raise ValueError("QueryPacket context offer bound")
    for offer_id in context_offer_ids:
        _collect_context_offer(
            store, offer_id, event_id, generation_id, before_rowid,
            refs, seen, source_hashes, visited_offers, visited_queries,
            visited_messages, visited_packets, depth + 1,
        )


def _collect_context_offer(store, packet_id, event_id, generation_id,
                           before_rowid, refs, seen, source_hashes,
                           visited_offers, visited_queries, visited_messages,
                           visited_packets, depth=0):
    if depth > 4:
        raise ValueError("offer provenance depth")
    if packet_id in visited_offers:
        return
    visited_offers.add(packet_id)
    if len(visited_packets) >= 32:
        raise ValueError("context packet traversal bound")
    visited_packets.add(packet_id)
    _rowid, payload = _context_packet(
        store, packet_id, {"OfferPacket"}, event_id, generation_id,
        before_rowid=before_rowid,
    )
    for key in ("provenance", "evidence_refs", "context_source_refs",
                "enlightened_source_refs"):
        _merge_context_source_refs(
            store, payload.get(key), refs, seen, source_hashes
        )
    query_id = payload.get("query_packet_id")
    if type(query_id) is not str or not query_id:
        raise ValueError("OfferPacket query link")
    _collect_context_query(
        store, query_id, event_id, generation_id, before_rowid,
        refs, seen, source_hashes, visited_offers, visited_queries,
        visited_messages, visited_packets, depth + 1,
        expected_role=payload.get("role"),
    )


def _assistant_context_source_refs(store, event_id, generation_id,
                                   selection_packet_id, selection_rowid,
                                   event_source_ref):
    rows = store.rows(
        """SELECT id,status,metadata FROM messages
           WHERE event_id=? AND role='assistant'
           ORDER BY id DESC LIMIT 4""",
        (event_id,),
    )
    if type(rows) is not list:
        raise ValueError("assistant context message scan")
    matches = []
    for raw in rows:
        message = _mapping(raw, "assistant context message")
        metadata = _object(message.get("metadata"), "assistant context metadata")
        if metadata.get("action_selection") == selection_packet_id:
            matches.append((message, metadata))
    if not matches:
        return [], "LEGACY_PARTIAL"
    if len(matches) != 1:
        raise ValueError("assistant context message cardinality")
    message, metadata = matches[0]
    if message.get("status") not in {
        "FINAL", "CANCELLED", "DEADLINE", "ERROR", "INTERRUPTED"
    }:
        raise ValueError("assistant context message not terminal")
    raw_context_refs = metadata.get("context_source_refs")
    raw_offer_ids = metadata.get("selected_offer_ids")
    if (type(raw_context_refs) is not list
            or not 1 <= len(raw_context_refs) <= MAX_ACTION_SOURCE_REFS
            or type(raw_offer_ids) is not list or len(raw_offer_ids) > 16
            or any(type(item) is not str or not item or len(item) > 256
                   for item in raw_offer_ids)
            or len(set(raw_offer_ids)) != len(raw_offer_ids)):
        raise ValueError("assistant context receipt shape")
    refs, seen, source_hashes = [], set(), {}
    _merge_context_source_refs(
        store, raw_context_refs, refs, seen, source_hashes
    )
    visited_offers, visited_queries = set(), set()
    visited_messages, visited_packets = set(), set()
    for offer_id in raw_offer_ids:
        _collect_context_offer(
            store, offer_id, event_id, generation_id, selection_rowid,
            refs, seen, source_hashes, visited_offers, visited_queries,
            visited_messages, visited_packets,
        )
    # ContextPlan is emitted after C5 selection but before the final C3 prompt.
    # It binds the exact selected/compacted history blocks; its source list is
    # merged when present. A future C3ContextPlan packet is accepted by the
    # same receipt path without changing the verifier contract.
    for key in ("context_plan", "c3_context_plan"):
        plan = metadata.get(key)
        if plan is None:
            continue
        if type(plan) is not dict:
            raise ValueError("ContextPlan receipt shape")
        plan_id = plan.get("packet_id")
        if not plan_id:
            continue
        _rowid, payload = _context_packet(
            store, plan_id, {"ContextPlan", "C3ContextPlan"},
            event_id, generation_id,
        )
        _merge_context_source_refs(
            store, payload.get("provenance"), refs, seen, source_hashes
        )
        _merge_context_source_refs(
            store, payload.get("source_refs"), refs, seen, source_hashes
        )
        _merge_context_source_refs(
            store, plan.get("source_refs"), refs, seen, source_hashes
        )
    future_id = metadata.get("c3_context_plan_packet_id")
    if future_id:
        _rowid, payload = _context_packet(
            store, future_id, {"C3ContextPlan"}, event_id, generation_id
        )
        if payload.get("action_selection_packet_id") != selection_packet_id:
            raise ValueError("C3ContextPlan selection binding")
        _merge_context_source_refs(
            store, payload.get("source_refs") or payload.get("provenance"),
            refs, seen, source_hashes,
        )
    if event_source_ref not in refs:
        raise ValueError("assistant context receipt omitted event source")
    refs.sort(key=lambda item: (
        item["source_id"], item["sha256"], item["char_start"],
        item["char_end"], item["modality"],
    ))
    return refs, "RUNTIME_SOURCE_COMPLETE"


def _selection_source_refs(store, event_id, generation_id, event_source_ref,
                           *, with_status=False):

    rows = store.rows(
        """SELECT rowid AS packet_rowid,id,payload FROM packets
           WHERE kind='ActionSelection' AND event_id=? AND generation_id=?
           ORDER BY rowid DESC LIMIT 17""",
        (event_id, generation_id),
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
            committed.append((selection, packet_row.get("packet_rowid"), packet_row.get("id")))
    if len(committed) != 1:
        raise ValueError("ActionSelection source cardinality")
    selection, selection_rowid, selection_packet_id = committed[0]
    if (type(selection_rowid) is not int or selection_rowid < 1
            or type(selection_packet_id) is not str
            or selection.get("packet_id") != selection_packet_id):
        raise ValueError("ActionSelection packet boundary")
    raw_refs = selection.get("provenance")
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

    # The current C5 producer can still write only the event SourceRef. The
    # bounded union of all pre-action C4 cycles is part of the deliberation
    # trajectory; final-cycle FocalItems verify the final coalition, while
    # earlier cycles contribute their capped source refs. Merge it without
    # changing Core-owned packet production.
    for ref in _focal_cycle_source_refs(
            store, event_id, generation_id, selection_rowid):
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

    context_refs, context_status = _assistant_context_source_refs(
        store, event_id, generation_id, selection_packet_id,
        selection_rowid, event_source_ref,
    )
    for ref in context_refs:
        key = (ref["source_id"], ref["sha256"], ref["char_start"],
               ref["char_end"], ref["modality"])
        prior = source_hashes.get(ref["source_id"])
        if prior is not None and prior != ref["sha256"]:
            raise ValueError("assistant context source digest conflicts with action lineage")
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
    packed = tuple(
        (item["source_id"], item["sha256"], item["char_start"],
         item["char_end"], item["modality"])
        for item in refs
    )
    return (packed, context_status) if with_status else packed

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
    context_lineage_status: str


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
    def context_lineage_status(self):
        return self._proof.context_lineage_status

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
                "context_lineage_status": self._proof.context_lineage_status,
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
    selected_source_refs, context_lineage_status = _selection_source_refs(
        store, meta["event_id"], meta["generation_id"], source_ref,
        with_status=True,
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
                       _hash(outcome_packet), float(created), float(outcome_created), status,
                       actual, context_lineage_status)
    verified_row = dict(row)
    verified_row["context_lineage_status"] = context_lineage_status
    return VerifiedT8Transition(_SEAL, verified_row, proof)


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



def committed_history_references_source(store, source_id, through_seq, *,
                                         include_censored=False,
                                         pending_action_ids=(), max_rows=2048):
    """Fail-closed source scan over the exact verified T8 prefix used by a checkpoint.

    This reuses the same ActionSelection/C4/Offer/Query/peer/ContextPlan and
    BODY_STATE nested lineage as normal learning. A legacy row without the
    persisted assistant context receipt cannot prove that a source was unused.
    """
    if (type(source_id) is not str or not source_id or len(source_id) > 256
            or type(through_seq) is not int or through_seq < 0
            or type(max_rows) is not int or not 1 <= max_rows <= 10000):
        return True
    if through_seq == 0:
        return False
    try:
        pending = set(pending_action_ids)
        if any(type(item) is not str or not item for item in pending):
            return True
        statuses = (
            "'FINAL','FAILED','ERROR','DEADLINE','REJECTED',"
            "'CANCELLED','ABORTED','OUTCOME_UNKNOWN','INTERRUPTED'"
            if include_censored else
            "'FINAL','FAILED','ERROR','DEADLINE','REJECTED'"
        )
        rows = store.rows(
            """SELECT a.rowid AS scan_seq,a.id,a.event_id,a.status,a.expected,
                      a.outcome,a.created,e.generation_id
               FROM actions a JOIN events e ON e.id=a.event_id
               WHERE a.rowid<=? AND a.outcome IS NOT NULL AND a.expected LIKE ?
                 AND a.status IN (""" + statuses + """)
               ORDER BY a.rowid ASC LIMIT ?""",
            (through_seq, '%"forecast"%', max_rows + 1),
        )
        if type(rows) is not list or len(rows) > max_rows:
            return True
        for raw in rows:
            action_row = _mapping(raw, "source-forget action row")
            if action_row.get("id") in pending:
                continue
            transition = _transition_from_action_row(store, action_row)
            receipt = _verify_one(store, transition)
            if receipt.context_lineage_status != "RUNTIME_SOURCE_COMPLETE":
                return True
            if any(item.get("source_id") == source_id for item in receipt.source_refs):
                return True
        return False
    except Exception:
        # Revoked/malformed/ambiguous lineage is never proof of non-use.
        return True


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
