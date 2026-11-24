"""Bounded operator-approved exact answers at the existing C5/F6 boundary.

No fuzzy matching, model judge, inferred fact authority or implicit activation.
Free-text rules stay prompt guidance. Invalid active exact rules fail closed.
"""
import re
from .common import safe_text, visible_text, uid

KIND = 'FIXED_EXACT'
QUERY_KIND = 'HUMAN_FIXED_RULE_QUERY'
ANSWER_KIND = 'HUMAN_FIXED_RULE_ANSWER'
MAX_FIXED = 32
MAX_QUERY_BYTES = 4096
MAX_ANSWER_BYTES = 16384
FIELDS = {'kind', 'rule_id', 'query_ref', 'answer_ref', 'owner',
          'model_authority', 'matcher'}
REF_FIELDS = {'source_id', 'sha256', 'char_start', 'char_end', 'modality'}


class InvalidRule(ValueError):
    """An exact rule cannot safely be used; never silently use native fallback."""


def bounded_text(text, cap, label):
    if not isinstance(text, str):
        raise InvalidRule(label + ': Text erforderlich')
    try:
        size = len(text.encode('utf-8'))
    except UnicodeError as exc:
        raise InvalidRule(label + ': ungültiges UTF-8') from exc
    if not 1 <= size <= cap or not visible_text(text) or safe_text(text) != text:
        raise InvalidRule(label + ': leer, unsicher oder zu lang')
    return text


def _read(store, ref, expected_kind, cap, label):
    if not isinstance(ref, dict) or set(ref) != REF_FIELDS:
        raise InvalidRule(label + ': vollständiger SourceRef erforderlich')
    if (not isinstance(ref['source_id'], str) or
            not isinstance(ref['sha256'], str) or
            not re.fullmatch(r'[a-f0-9]{64}', ref['sha256']) or ref['modality'] != 'text' or
            type(ref['char_start']) is not int or type(ref['char_end']) is not int):
        raise InvalidRule(label + ': SourceRef-Typ ungültig')
    row = store.one('SELECT * FROM sources WHERE id=?', (ref['source_id'],))
    if (not row or row['deleted'] or row['kind'] != expected_kind or
            ref['char_start'] != 0 or ref['char_end'] != row['chars'] or
            not 1 <= row['bytes'] <= cap):
        raise InvalidRule(label + ': Operator-Quelle gelöscht oder ungültig')
    try:
        # Reject an externally replaced oversized blob before reading it.
        if (store.home / 'data/blobs' / ref['sha256']).stat().st_size > cap:
            raise InvalidRule(label + ': Quelle überschreitet das Byte-Limit')
        return bounded_text(store.read_source(ref), cap, label)
    except (OSError, ValueError, UnicodeError, KeyError) as exc:
        raise InvalidRule(label + ': Operator-Quelle beschädigt') from exc


def validate_rules(store, rules):
    """Validate every active typed rule, returning exact source text snapshots."""
    if not isinstance(rules, list):
        raise InvalidRule('Regeln müssen eine Liste sein')
    fixed = []
    queries = set()
    ids = set()
    for entry in rules:
        if isinstance(entry, str):
            continue  # Legacy guidance semantics remain unchanged.
        if not isinstance(entry, dict) or set(entry) != FIELDS:
            raise InvalidRule('Unbekannter typisierter Regelaufbau')
        if (entry['kind'] != KIND or entry['owner'] != 'OPERATOR_TTY' or
                entry['model_authority'] is not False or
                entry['matcher'] != 'UTF8_EXACT' or
                not isinstance(entry['rule_id'], str) or
                not re.fullmatch(r'fixed_[a-f0-9]{32}', entry['rule_id'])):
            raise InvalidRule('Unzulässige Regelautorität oder Vergleichsart')
        if len(fixed) >= MAX_FIXED:
            raise InvalidRule('Höchstens 32 feste Antworten')
        query = _read(store, entry['query_ref'], QUERY_KIND, MAX_QUERY_BYTES,
                      'Feste Frage')
        answer = _read(store, entry['answer_ref'], ANSWER_KIND, MAX_ANSWER_BYTES,
                       'Feste Antwort')
        if query in queries or entry['rule_id'] in ids:
            raise InvalidRule('Doppelte oder widersprüchliche feste Frage/Regel-ID')
        queries.add(query)
        ids.add(entry['rule_id'])
        fixed.append({'entry': entry, 'query': query, 'answer': answer})
    return fixed


def create(store, query, answer):
    """Create bounded human-authored sources; activation still needs approval."""
    bounded_text(query, MAX_QUERY_BYTES, 'Feste Frage')
    bounded_text(answer, MAX_ANSWER_BYTES, 'Feste Antwort')
    return {'kind': KIND, 'rule_id': uid('fixed'),
            'query_ref': store.source(query, QUERY_KIND),
            'answer_ref': store.source(answer, ANSWER_KIND),
            'owner': 'OPERATOR_TTY', 'model_authority': False,
            'matcher': 'UTF8_EXACT'}


def preview(store, rules):
    return [{'rule_id': item['entry']['rule_id'], 'query': item['query'],
             'answer': item['answer']} for item in validate_rules(store, rules)]


def match(store, text):
    """Read current rule generation atomically and revalidate its source blobs."""
    with store.mutex:
        generation = store.generation()
        row = store.one('SELECT rules FROM rules WHERE id=?',
                        (generation['rule_version'],))
        if not row:
            raise InvalidRule('Aktive Regelversion fehlt')
        import json
        try:
            rules = json.loads(row['rules'])
        except (ValueError, TypeError) as exc:
            raise InvalidRule('Aktive Regeln beschädigt') from exc
        fixed = validate_rules(store, rules)
        for item in fixed:
            if item['query'] == text:
                return {'kind': KIND, 'rule_id': item['entry']['rule_id'],
                        'rule_version': generation['rule_version'],
                        'query_ref': dict(item['entry']['query_ref']),
                        'answer_ref': dict(item['entry']['answer_ref']),
                        'answer': item['answer'], 'model_generated': False,
                        'output_authority': 'APPROVED_FIXED_RULE'}
        return None
