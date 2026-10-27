"""WP-BP2b: bounded, question-only English locality anchors for body LoRA.

Subject-shift near misses are KL anchors to the *base* model, never training
answers. No target, memory content, or evaluator-heldout data enters this path.
Unsupported syntax yields no anchor, not a guessed rephrasing. This is a
candidate behind BodyJepaTrainer.locality_policy='bp2b', not an age/learning gate.
"""
import hashlib
import re

REVISION = 'bp2b-question-subject-shift-v1'
TRAIN_SUBJECTS = ('friend', 'mother', 'father', 'boss', 'cousin', 'uncle',
                  'colleague', 'neighbour', 'grandmother', 'son')
# Reserved for independent evaluations; never chosen as replacement subjects.
RESERVED_EVAL_SUBJECTS = ('sister', 'wife', 'nephew', 'dog', 'rabbit', 'turtle', 'parrot')
MAX_QUESTION_CHARS = 256
MAX_ITEMS = 256
_UNSUPPORTED = re.compile(r"\b(?:we|our|ours|us|mine|me|myself|ourselves|i'm|i've|i'll|i'd)\b", re.I)
_FIRST_PERSON = re.compile(r'\b(?:I|my)\b', re.I)
_MY = re.compile(r'\bmy\b', re.I)
_I = re.compile(r'\bI\b')
_AUX_I = re.compile(r'\b(do|did|am|have|can|could|should|would|will|may|might|must) I\b', re.I)
_AUX = {'do': 'does', 'did': 'did', 'am': 'is', 'have': 'has',
        'can': 'can', 'could': 'could', 'should': 'should',
        'would': 'would', 'will': 'will', 'may': 'may',
        'might': 'might', 'must': 'must'}


def shift_question(question, subject):
    """Return one conservative subject-shift or None; only source question used."""
    if (type(question) is not str or type(subject) is not str
            or subject not in TRAIN_SUBJECTS or not 8 <= len(question) <= MAX_QUESTION_CHARS
            or question != question.strip() or question.count('?') != 1
            or not question.endswith('?') or any(ord(c) < 32 or ord(c) == 127 for c in question)
            or any(c in question for c in (chr(96), '{', '}', '<', '>', '"', '\\'))
            or _UNSUPPORTED.search(question) or not _FIRST_PERSON.search(question)):
        return None
    # Do not silently rewrite third-person quoted claims or a free-standing I.
    if re.search(r"\bI\b", _AUX_I.sub('', question)):
        return None
    def possessive(m):
        return ('My' if m.group(0)[0].isupper() else 'my') + ' ' + subject + "'s"
    shifted = _MY.sub(possessive, question)
    def auxiliary(m):
        aux = _AUX[m.group(1).lower()]
        if m.group(1)[0].isupper():
            aux = aux.capitalize()
        return aux + ' my ' + subject
    shifted = _AUX_I.sub(auxiliary, shifted)
    if shifted == question or _I.search(shifted):
        return None
    return shifted


def generate_anchors(items, count=2):
    """Deterministic bounded distinct KL prompts; ignores target/answer_keys by construction."""
    if type(count) is not int or not 0 <= count <= len(TRAIN_SUBJECTS):
        raise ValueError('locality anchor count out of bounds')
    if type(items) not in (tuple, list) or len(items) > MAX_ITEMS:
        raise ValueError('locality items must be a bounded sequence')
    if not count:
        return []
    out, seen = [], set()
    for item in items:
        if type(item) is not dict:
            continue
        question = item.get('prompt')
        if type(question) is not str:
            continue
        offset = int.from_bytes(hashlib.sha256(question.encode('utf-8')).digest()[:4], 'big') % len(TRAIN_SUBJECTS)
        added = 0
        for j in range(len(TRAIN_SUBJECTS)):
            subject = TRAIN_SUBJECTS[(offset + j) % len(TRAIN_SUBJECTS)]
            candidate = shift_question(question, subject)
            if candidate is None or candidate == question or candidate in seen:
                continue
            seen.add(candidate)
            out.append(candidate)
            added += 1
            if added == count:
                break
    return out
