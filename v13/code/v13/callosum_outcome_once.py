"""B3-H9 Callosum utility accounting: one automatic outcome per packet ID.

Called inside Callosum._mutate's optimistic persisted-state transaction.
No Store, packet, age, latent or feedback authority is granted here.
"""


def apply_once(pending, scores, update):
    """Apply (message, utility, components) only to unscored current messages.

    Returns (packet_id, utility) records actually applied. The updater mutates only the same
    pending-state copy that will be committed by the caller's CAS.
    """
    groups = {}
    for item in pending:
        if isinstance(item, dict) and isinstance(item.get('msg'), str):
            groups.setdefault(item['msg'], []).append(item)
    seen = set()
    applied = []
    for message, utility, components in scores:
        msg_id = message['msg']
        if msg_id in seen:
            continue
        seen.add(msg_id)
        items = groups.get(msg_id) or []
        if not items:
            continue
        if not any(item.get('scored') for item in items):
            update(items[0], utility, components)
            applied.append((msg_id, utility))
        for item in items:
            item['scored'] = True
    return applied
