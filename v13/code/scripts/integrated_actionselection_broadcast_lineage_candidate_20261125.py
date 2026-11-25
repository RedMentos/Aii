"""Staged Core overlay: preserve C1 executive-broadcast source lineage in C5.

The canonical V13 focal.py bytes stay pinned and untouched. This patch applies
only to the isolated integrated candidate after its reviewed source overlays.
"""
from pathlib import Path

MARKER = b"ACTION_SELECTION_C1_BROADCAST_LINEAGE_V1"

PROVENANCE_ANCHOR = b'''        if not event_row or event_row["source_id"]!=event_ref.get("source_id"):
            raise ValueError("ActionSelection event/source binding")
'''
PROVENANCE_REPLACEMENT = b'''        if not event_row or event_row["source_id"]!=event_ref.get("source_id"):
            raise ValueError("ActionSelection event/source binding")

        # ACTION_SELECTION_C1_BROADCAST_LINEAGE_V1: C1 memory/context shaped
        # routing before C5. Keep those exact source pointers even if no body
        # offer reaches the coalition; never convert a receipt into an observation.
        broadcast_rows=self.s.rows(
            "SELECT payload FROM packets WHERE kind='JEFBroadcastPacket' AND event_id=? ORDER BY rowid DESC LIMIT 2",
            (event_id,))
        if type(broadcast_rows) is not list or len(broadcast_rows)>1:
            raise ValueError("ActionSelection executive broadcast cardinality")
        broadcast_payload=None
        if broadcast_rows:
            try:broadcast_payload=json.loads(broadcast_rows[0]["payload"])
            except (TypeError,ValueError,KeyError) as exc:
                raise ValueError("ActionSelection executive broadcast malformed") from exc
            if type(broadcast_payload) is not dict:
                raise ValueError("ActionSelection executive broadcast malformed")
            broadcast_refs=broadcast_payload.get("source_refs")
            if (type(broadcast_payload.get("packet_id")) is not str or not broadcast_payload["packet_id"]
                    or broadcast_payload.get("producer_component")!="C1_EXEC"
                    or broadcast_payload.get("event_id")!=event_id
                    or broadcast_payload.get("brain_generation_id")!=generation_id
                    or type(broadcast_payload.get("state_version")) is not int
                    or broadcast_payload.get("state_version")<0
                    or type(broadcast_refs) is not list
                    or broadcast_payload.get("provenance")!=broadcast_refs):
                raise ValueError("ActionSelection executive broadcast binding")
            for ref in broadcast_refs:add(ref)
'''
QUERY_BINDING_ANCHOR = b'''                        or query.get("based_on_state_version")!=offer.get("based_on_state_version")
                        or query.get("context_source_refs",[])!=offer.get("context_source_refs",[])
'''
QUERY_BINDING_REPLACEMENT = b'''                        or query.get("based_on_state_version")!=offer.get("based_on_state_version")
                        or query.get("broadcast_packet_id")!=offer.get("broadcast_packet_id")
                        or query.get("context_source_refs",[])!=offer.get("context_source_refs",[])
'''
QUERY_TAIL_ANCHOR = b'''                for field in ("provenance","source_refs","context_source_refs","enlightened_source_refs"):
                    values=query.get(field,[])
                    if type(values) is not list:
                        raise ValueError("ActionSelection query "+field)
                    for ref in values:add(ref)
'''
QUERY_TAIL_REPLACEMENT = b'''                query_broadcast_id=query.get("broadcast_packet_id")
                if query_broadcast_id is not None:
                    if (broadcast_payload is None
                            or broadcast_payload.get("packet_id")!=query_broadcast_id
                            or broadcast_payload.get("state_version")!=query.get("based_on_state_version")):
                        raise ValueError("ActionSelection query broadcast binding")
                for field in ("provenance","source_refs","context_source_refs","enlightened_source_refs"):
                    values=query.get(field,[])
                    if type(values) is not list:
                        raise ValueError("ActionSelection query "+field)
                    for ref in values:add(ref)
'''

def _replace_once(raw, anchor, replacement, label):
    if raw.count(anchor) != 1:
        raise ValueError("ActionSelection lineage overlay anchor mismatch: " + label)
    return raw.replace(anchor, replacement, 1)

def apply_staged_actionselection_lineage(code_dir: Path, staging: Path):
    code_dir = Path(code_dir).resolve(strict=True)
    staging = Path(staging).resolve(strict=True)
    source = code_dir / "v13/focal.py"
    target = staging / "v13/focal.py"
    if source.is_symlink() or not source.is_file() or target.is_symlink() or not target.is_file():
        raise ValueError("ActionSelection lineage focal source/stage missing or unsafe")
    source_raw = source.read_bytes()
    staged_raw = target.read_bytes()
    if (source_raw.count(PROVENANCE_ANCHOR) != 1
            or source_raw.count(QUERY_BINDING_ANCHOR) != 1
            or source_raw.count(QUERY_TAIL_ANCHOR) != 1):
        raise ValueError("ActionSelection lineage source contract changed")
    if MARKER in staged_raw or b"SCALE_AWARE_C4_RULE" not in staged_raw:
        raise ValueError("ActionSelection lineage staged base mismatch")
    patched = _replace_once(staged_raw, PROVENANCE_ANCHOR, PROVENANCE_REPLACEMENT, "broadcast provenance")
    patched = _replace_once(patched, QUERY_BINDING_ANCHOR, QUERY_BINDING_REPLACEMENT, "query binding")
    patched = _replace_once(patched, QUERY_TAIL_ANCHOR, QUERY_TAIL_REPLACEMENT, "query broadcast state")
    if MARKER not in patched:
        raise ValueError("ActionSelection lineage marker missing")
    compile(patched.decode("utf-8"), str(target), "exec")
    return {"v13/focal.py": patched}
