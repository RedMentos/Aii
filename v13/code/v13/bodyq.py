"""WP-Z2f: a body question built from the current message by a fixed rule (cfg body_question_mode='derived').

WP-Z2e: a task-agnostic standing question does not help (+.03), the STEP2-specific one does (+.33); the gain comes from
naming what is needed. Here the needed things are taken from the message itself, without a model: named entities
(two capitalised words such as "Option A", "Project Kestrel") and phrases the message points back to ("the earlier
project rules", "the latest supplier data sheet"). Nothing found -> the general WP-Z2e question. The question is an
executive question (authority EXECUTIVE_QUESTION_NOT_FACT), never evidence.
"""
import re

ENTITY = re.compile(r'\b([A-Z][a-z]+(?:\s+(?:[A-Z]\b|[A-Z][a-z]+))+)')
POINTER = re.compile(r'\bthe\s+(?:earlier|previous|prior|latest|last|original|agreed)\s+((?:[a-z][a-z-]*\s+){0,2}[a-z][a-z-]*)')
STOP = {'the', 'a', 'an', 'and', 'or', 'of', 'from', 'to', 'for', 'with', 'using', 'in', 'on', 'at', 'is', 'are'}
GENERAL = {'B1_DETAIL': 'Which exact details (numbers, names, values) does the current message need? '
                        'Quote the exact source sentences that state them, or say they are not in the source.',
           'B2_GIST': 'Which earlier statements (rules, constraints, decisions) does the current message depend on? '
                      'Quote the exact earlier source sentences that state them, or say they are not in the source.'}
MAX_ITEMS = 4


def _uniq(items):
    out = []
    for x in items:
        x = ' '.join(x.split())
        if x and x.lower() not in {o.lower() for o in out}: out.append(x)
    return out[:MAX_ITEMS]


def _join(xs):
    return xs[0] if len(xs) == 1 else ', '.join(xs[:-1])+' and '+xs[-1]


def parts(text):
    """(entities, pointed-at phrases) of a message; fixed regex, no model."""
    t = str(text)[:2000]
    ents = _uniq(ENTITY.findall(t))
    ptr = []
    for m in POINTER.findall(t):
        words = m.split()
        while words and words[-1] in STOP: words.pop()
        if words: ptr.append(' '.join(words))
    return ents, _uniq(ptr)


def question(role, text):
    ents, ptr = parts(text)
    if role == 'B1_DETAIL':
        if not ents and not ptr: return GENERAL[role]
        what = 'exact values of '+_join(ents) if ents else 'exact details'
        src = ' (from the '+_join(ptr)+')' if ptr else ''
        return f'Which {what}{src} does the current message need? Quote the exact source sentences that state them, or say they are not in the source.'
    if not ptr and not ents: return GENERAL[role]
    about = 'earlier '+_join(ptr) if ptr else 'earlier statements about '+_join(ents)
    of = ' for '+_join(ents) if ptr and ents else ''
    return f'Which {about}{of} does the current message depend on? Quote the exact earlier source sentences that state them, or say they are not in the source.'


def focus(role, text):
    return {'question': question(role, text)[:400], 'kind': 'FILL_GAP', 'target_role': role, 'reason': 'DERIVED_FROM_CURRENT_MESSAGE',
            'authority': 'EXECUTIVE_QUESTION_NOT_FACT'}
