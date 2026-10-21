#!/usr/bin/env python3
"""WP-Z3c: extensible deterministic rule parser (budget, deadline, local_only).

Z3b showed the anchored parser reads only the canonical wording ("Budget N euros.", "Deadline N days.",
"Local-only requirement: x.") and C3-350M never reads yes/no rules. This parser reads reworded rules from a
lexicon that is data (lexicon.json, every entry with evidence) and a small fixed grammar:

  sentences   split on . ! ?; option sentences ("Option A: ...") and instruction sentences are skipped;
              a sentence with a hedge term (undecided, proposed, last year, ?) states no current rule and
              is ignored as a whole, numbers included
  clauses     split on ; and , inside a sentence
  numbers     digits or English number words; unit euro -> budget, unit day -> deadline, € before a number;
              no unit -> the clause's single rule noun gives it; another unit (weeks, dollars) -> unreadable.
              A value counts only with a limit cue in the clause: max term, rule noun, obligation, or a
              "greater than" term together with a negation or exclusion. A minimum term -> unreadable.
  local_only  locality terms give the subject polarity (local / non-local); predicate classes
              (require, allow, forbid, irrelevant) are flipped by a negation up to 3 tokens before them;
              a fixed table maps (subject, predicates) to true / false / unreadable
  result      per rule: one value -> value; two values -> CONFLICT; unreadable or a number that no rule
              accounts for -> UNREADABLE; nothing -> None. Anything but a value makes the recipe say UNKNOWN.

Never guesses: every path that is not covered by the table refuses. Diagnostic, no gate promotion.
"""
import json
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
LEXICON_PATH = HERE / 'lexicon.json'
RULES = ('budget', 'deadline', 'local_only')
CONFLICT = 'CONFLICT'
UNREADABLE = 'UNREADABLE'
CLASSES = {'unit_euro', 'unit_day', 'unit_other', 'rule_noun_euro', 'rule_noun_day', 'max', 'gt', 'min',
           'obligation', 'exclusion', 'loc_flag', 'loc_pos', 'loc_neg', 'require', 'allow', 'allow_weak', 'forbid',
           'irrelevant', 'matters', 'negation', 'hedge', 'instruction'}
CONTEXTS = {
    'numeric': {'unit_euro', 'unit_day', 'unit_other', 'rule_noun_euro', 'rule_noun_day', 'max', 'gt', 'min',
                'obligation', 'exclusion', 'negation'},
    'local': {'loc_flag', 'loc_pos', 'loc_neg', 'require', 'allow', 'allow_weak', 'forbid', 'irrelevant', 'matters', 'negation'},
    'hedge': {'hedge'},
    'instruction': {'instruction'},
}
NEGATE = {'require': 'irrelevant', 'allow': 'forbid', 'forbid': 'allow', 'irrelevant': 'require',
          'matters': 'irrelevant'}
NEG_WINDOW = 3
_SMALL = ['zero', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten', 'eleven', 'twelve',
          'thirteen', 'fourteen', 'fifteen', 'sixteen', 'seventeen', 'eighteen', 'nineteen']
_TENS = ['twenty', 'thirty', 'forty', 'fifty', 'sixty', 'seventy', 'eighty', 'ninety']
NUMBER_WORDS = {w: i for i, w in enumerate(_SMALL)} | {w: 20 + 10 * i for i, w in enumerate(_TENS)}
NUMBER_WORDS |= {t + '-' + s: 20 + 10 * i + j for i, t in enumerate(_TENS) for j, s in enumerate(_SMALL[1:10], 1)}
_TOKEN = re.compile(r'\d+|€|\$|%|\?|[a-z]+(?:-[a-z]+)*')
_OPTION_SENTENCE = re.compile(r'\boption\s+[ab]\s*:', re.I)
_PROJECT_SENTENCE = re.compile(r'^project\s+\w+\.?$', re.I)


# ---------------------------------------------------------------- lexicon

def load_lexicon(path=LEXICON_PATH):
    lexicon = json.loads(Path(path).read_text())
    validate(lexicon)
    return lexicon


def validate(lexicon):
    seen = set()
    for e in lexicon['entries']:
        if e['class'] not in CLASSES:
            raise ValueError('Unknown lexicon class: ' + e['class'])
        if not e.get('term') or not e.get('evidence'):
            raise ValueError('Lexicon entry without term or evidence')
        if 'holdout' in e['evidence'].lower():
            raise ValueError('Holdout data is never lexicon evidence')
        key = (e['term'], e['class'])
        if key in seen:
            raise ValueError('Duplicate lexicon entry: ' + repr(key))
        seen.add(key)


def extend(lexicon, term, cls, evidence):
    """New lexicon with one more entry (the only sanctioned way to learn a wording)."""
    out = {**lexicon, 'entries': [*lexicon['entries'], {'term': term.lower(), 'class': cls, 'evidence': evidence}]}
    validate(out)
    return out


def _phrases(lexicon, context):
    allowed = CONTEXTS[context]
    table = {}
    for e in lexicon['entries']:
        if e['class'] in allowed:
            table.setdefault(tuple(tokens(e['term'], numbers=False)), set()).add(e['class'])
    return sorted(table.items(), key=lambda kv: -len(kv[0]))


# ---------------------------------------------------------------- text

def tokens(text, numbers=True):
    text = text.lower().replace('’', "'").replace("can't", 'can not').replace('cannot', 'can not')
    text = text.replace("won't", 'will not').replace("n't", ' not')
    out = _TOKEN.findall(text)
    return [str(NUMBER_WORDS[t]) if numbers and t in NUMBER_WORDS else t for t in out]


def sentences(text):
    return [s.strip() for s in re.split(r'(?<=[.!?])\s+', text.strip()) if s.strip()]


def clauses(sentence):
    return [c.strip() for c in re.split(r'[;,]', sentence) if c.strip()]


def match(toks, phrases):
    """Greedy longest match, non-overlapping: list of (start, end, classes)."""
    out, i = [], 0
    while i < len(toks):
        for phrase, classes in phrases:
            if tuple(toks[i:i + len(phrase)]) == phrase:
                out.append((i, i + len(phrase), classes))
                i += len(phrase)
                break
        else:
            i += 1
    return out


# ---------------------------------------------------------------- readers

def read_numeric(toks, hits):
    """(rule, value) pairs or (rule, UNREADABLE) / (None, UNREADABLE) for unaccounted numbers."""
    classes = set().union(*(c for _, _, c in hits)) if hits else set()
    at = {i: c for s, e, c in hits for i in range(s, e)}
    nouns = {c for c in classes if c.startswith('rule_noun_')}
    out = []
    for i, t in enumerate(toks):
        if not t.isdigit():
            continue
        after, before = at.get(i + 1, set()), at.get(i - 1, set())
        if 'unit_other' in after or (i > 0 and toks[i - 1] in ('$',)):
            out.append((None, UNREADABLE))
            continue
        if 'unit_euro' in after or 'unit_euro' in before:
            rule = 'budget'
        elif 'unit_day' in after or (i > 0 and toks[i - 1] == 'day'):
            rule = 'deadline'
        elif len(nouns) == 1:
            rule = 'budget' if nouns == {'rule_noun_euro'} else 'deadline'
        else:
            out.append((None, UNREADABLE))
            continue
        noun = ('rule_noun_euro' if rule == 'budget' else 'rule_noun_day') in classes
        if 'min' in classes:
            out.append((rule, UNREADABLE))
        elif 'max' in classes or noun or 'obligation' in classes:
            out.append((rule, int(t)))
        elif 'gt' in classes and ('negation' in classes or 'exclusion' in classes):
            out.append((rule, int(t)))
        else:
            out.append((rule, UNREADABLE))
    return out


def read_local(toks, hits):
    """True / False / UNREADABLE / None (no locality term in the clause)."""
    flags = [e for _, e, cs in hits if 'loc_flag' in cs]
    if flags:  # key-value form "local-only requirement: true"
        values = {toks[e] if e < len(toks) else '' for e in flags}
        return {'true': True, 'false': False, 'yes': True, 'no': False}.get(values.pop(), UNREADABLE) \
            if len(values) == 1 and len(flags) == 1 else UNREADABLE
    implied = ['require' for s, e, _ in hits if toks[s:e] == ['local-only']]
    subject = {c for _, _, cs in hits for c in cs if c in ('loc_pos', 'loc_neg')}
    if not subject:
        return None
    preds, negs = list(implied), [s for s, _, cs in hits if 'negation' in cs]
    used = set()
    for s, _, cs in hits:
        for c in cs:
            if c in ('require', 'allow', 'allow_weak', 'forbid', 'irrelevant', 'matters'):
                neg = [n for n in negs if 0 < s - n <= NEG_WINDOW]
                if neg and c != 'allow_weak':
                    used.update(neg)
                    preds.append(NEGATE[c])
                elif c == 'matters' and not neg:
                    preds.append('ambiguous')
                else:
                    preds.append(c)
    if len(set(negs) - used) or len(used) > 1:
        return UNREADABLE  # dangling or double negation
    strong = {p for p in preds if p != 'allow_weak'}
    if not strong:
        strong = {'allow'} if 'allow_weak' in preds else set()
    if not strong or 'ambiguous' in strong:
        return UNREADABLE
    pos, neg = 'loc_pos' in subject, 'loc_neg' in subject
    if pos and not neg:
        if strong <= {'require', 'allow'} and 'require' in strong:
            return True
        if strong == {'irrelevant'}:
            return False
    elif neg and not pos:
        if strong <= {'forbid', 'require'} and 'forbid' in strong:
            return True
        if strong <= {'allow', 'irrelevant'}:
            return False
    elif strong <= {'allow', 'irrelevant'}:
        return False
    return UNREADABLE


def parse(texts, lexicon=None):
    """Read the three rules from source texts. Returns {'rules': ..., 'trace': [...]}."""
    lexicon = lexicon or load_lexicon()
    ph = {k: _phrases(lexicon, k) for k in CONTEXTS}
    found = {r: [] for r in RULES}
    trace, unaccounted = [], False
    for text in texts:
        for sentence in sentences(text):
            toks = tokens(sentence)
            if _OPTION_SENTENCE.search(sentence) or _PROJECT_SENTENCE.match(sentence):
                continue
            if toks and match(toks[:1], ph['instruction']):
                continue
            if match(toks, ph['hedge']):
                trace.append({'sentence': sentence, 'ignored': 'hedge'})
                continue
            for clause in clauses(sentence):
                ct = tokens(clause)
                for rule, value in read_numeric(ct, match(ct, ph['numeric'])):
                    if rule is None:
                        unaccounted = True
                    else:
                        found[rule].append(value)
                    trace.append({'clause': clause, 'rule': rule, 'value': value})
                local = read_local(ct, match(ct, ph['local']))
                if local is not None:
                    found['local_only'].append(local)
                    trace.append({'clause': clause, 'rule': 'local_only', 'value': local})
    rules = {}
    for rule in RULES:
        values = found[rule]
        if unaccounted or UNREADABLE in values:
            rules[rule] = UNREADABLE
        elif len(set(values)) > 1:
            rules[rule] = CONFLICT
        else:
            rules[rule] = values[0] if values else None
    return {'rules': rules, 'trace': trace, 'unaccounted_number': unaccounted}


def usable(rules):
    """Rule values the recipe may use (CONFLICT / UNREADABLE / missing -> None)."""
    return {r: (v if v not in (CONFLICT, UNREADABLE) else None) for r, v in rules.items()}
