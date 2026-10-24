"""§3.3.8 JEF readout: bounded exact-context human-feedback precedence.

Read-only: no authority is created. Candidate contexts are provided by existing
outcome state; a human RECORD decision vetoes an outcome self-label even if the
human decision falls outside the recent training-label sampling window.
"""


def blocked_human_contexts(store, component, revision, context_hashes):
    """Return context SHA-256 keys with an extant linked human decision.

    Each query has <=203 bound parameters, independent of feedback history size.
    No serialized substring matches or dynamic SQL values beyond placeholders.
    """
    keys = sorted({k for k in context_hashes if type(k) is str and k})
    blocked = set()
    for start in range(0, len(keys), 200):
        chunk = keys[start:start + 200]
        params = ','.join('?' for _ in chunk)
        rows = store.rows(
            "SELECT DISTINCT json_extract(d.payload,'$.context_ref.sha256') AS context_sha256 "
            "FROM feedback f "
            "JOIN sources src ON src.id=f.source_id AND src.deleted=0 "
            "JOIN packets h ON h.event_id=f.event_id AND h.kind='HumanDecision' "
            "AND json_extract(h.payload,'$.source_ref.source_id')=f.source_id "
            "JOIN packets d ON d.id=json_extract(h.payload,'$.decision_packet_id') "
            "AND d.event_id=f.event_id AND d.kind='ExecutiveDecision' "
            "WHERE f.kind=? AND json_extract(d.payload,'$.component')=? "
            "AND json_extract(d.payload,'$.context_revision')=? "
            f"AND json_extract(d.payload,'$.context_ref.sha256') IN ({params})",
            (component, component, revision, *chunk),
        )
        blocked.update(row['context_sha256'] for row in rows if row['context_sha256'] in chunk)
    return blocked
