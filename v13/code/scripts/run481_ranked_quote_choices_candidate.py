#!/usr/bin/env python3
"""Run481 source-only candidate: goal-ranked *exact* B2 quote choices.

Does not change Cognition/Context OS production, frozen cohorts or Age gates.
The output is a list of source-index/character-span pointers, never generated
facts. Zero relevant evidence means abstain, not a fabricated quotation.
"""
import hashlib
import re
from v13.cognition import sentence_spans

STOP = frozenset('a an and are as at be by can do does for from have here how i in is it of on or our project source sources the these this those to us we what when where which who why with you your earlier apply rules'.split())


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def words(text):
    return frozenset(t for t in re.findall(r'[^\W_]+', text.casefold())
                     if len(t) >= 3 and t not in STOP)


def ranked_quote_choices(sources, goal, cap=24):
    """Return (source_index,start,end) ranked by lexical relevance.

    Exact source spans only. Does not establish truth, temporal precedence,
    quote authorization or relevance beyond token overlap; shadow candidate.
    """
    require(type(sources) in (list, tuple) and 1 <= len(sources) <= 16 and
            all(type(s) is str and len(s) <= 16_384 for s in sources) and
            sum(map(len, sources)) <= 32_768,
            'RANKED_QUOTE_SOURCE_BUDGET')
    require(type(goal) is str and 0 < len(goal) <= 512 and
            type(cap) is int and 1 <= cap <= 24,
            'RANKED_QUOTE_QUERY_BUDGET')
    terms = words(goal)
    require(bool(terms), 'RANKED_QUOTE_NO_QUERY_TERMS')
    candidates = []
    for si, source in enumerate(sources):
        for a, b in sentence_spans(source):
            if b <= a:
                continue
            found = words(source[a:b]) & terms
            if not found:
                continue
            # Prefer coverage of the actual goal, not the first source line.
            # Equal scores preserve source and sentence order deterministically.
            candidates.append((-len(found), si, a, b))
    candidates.sort()
    result = [(si, a, b) for _, si, a, b in candidates[:cap]]
    require(all(sources[si][a:b] for si, a, b in result),
            'RANKED_QUOTE_EMPTY_SPAN')
    return result


def diagnostic(sources, goal, cap=24):
    choices = ranked_quote_choices(sources, goal, cap)
    return {'schema':'V13_RUN481_B2_RANKED_EXACT_QUOTE_CANDIDATE_V1',
            'goal_sha256':hashlib.sha256(goal.encode('utf-8')).hexdigest(),
            'choices':[{'source_index':si,'char_start':a,'char_end':b,
                        'text':sources[si][a:b],
                        'source_sha256':hashlib.sha256(sources[si].encode('utf-8')).hexdigest()} for si,a,b in choices],
            'status':'SHADOW_SOURCE_ONLY_NO_AUTHORITY',
            'canonical_gate_pass':False,'latent_authority':0,
            'step2_exit':'UTILITY_FAIL','b3_l1':'FAIL',
            'body_jepa':'UNAVAILABLE','jepa_weight':0,
            'redmi_measured':False,
            'claim_limit':'Lexical ranking only; no native B2 improvement, accuracy, trust, time revision, or causal utility established.'}
