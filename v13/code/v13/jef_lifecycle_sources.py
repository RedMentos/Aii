"""§14.6 JEF lifecycle: exact source lineage, never serialized-text guesses."""
import json


def matching_updates(rows, source_ids):
    """Read-only exact source_ids intersection; malformed manifests fail closed."""
    sources = {x for x in source_ids if type(x) is str and x}
    if not sources:
        return []
    matched = []
    for row in rows:
        try:
            manifest = json.loads(row['manifest'])
            if type(manifest) is not dict:
                continue
            ids = manifest.get('source_ids')
            if type(ids) is not list or any(type(x) is not str for x in ids):
                continue
            if sources.intersection(ids):
                matched.append(row)
        except (ValueError,TypeError,KeyError):
            continue
    return matched
