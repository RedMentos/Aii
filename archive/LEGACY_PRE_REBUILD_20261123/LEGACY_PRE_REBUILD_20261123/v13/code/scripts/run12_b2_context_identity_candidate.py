"""Source-exact B2 historical-context identity candidate (OFF, software-only).

A retrospective TP/s27 trace found that the current "project rules" and an
unrelated "Project Atlas" distractor both yielded the pseudo-entity "rules"
under the older generic regex. The newest-first 768-char B2 context then spent
its budget on Atlas before reaching the relevant older Project Aquila note.

This candidate changes NO runtime or registered cohort. It accepts only a
caller-provided verified source reader, keeps B2's existing bounded excerpt
shape, refuses cross-project/ambiguous identities, and returns no fact/answer.
Future native comparison must use a fresh preregistered cohort.
"""
import json
import re
from collections import Counter

REVISION = 'b2-context-named-entity-guard-candidate-v1'
ENTITY = re.compile(r'\b(?:project|projekt|client|kunde|person)\s+["\']?([\w-]+)', re.I)
GENERIC = frozenset('rules rule policy policies budget budgets deadline deadlines requirements requirement '
                    'status history archive note notes document documents report reports data sheet sheets '
                    'source sources decision decisions options option context summary plan plans'.split())
MAX_SOURCE_CHARS = 10_000


def named_entities(text):
    """A named project must not be confused with a generic 'project rules' noun phrase."""
    if type(text) is not str or len(text) > MAX_SOURCE_CHARS:
        raise ValueError('SOURCE_TEXT_SIZE')
    return {m.group(1).casefold() for m in ENTITY.finditer(text)
            if m.group(1).casefold() not in GENERIC}


def _json_len(obj):
    return len(json.dumps(obj,ensure_ascii=False,sort_keys=True,separators=(',',':')))


def select_context(current, current_event_id, session, generation, revision,
                   retained, read_source, cap=768, slots=4, excerpt_chars=240):
    """Read-only B2 candidate.

    `retained`: newest-first B2 offers with event/session/generation/model
    binding, exact original `source_ref` and fallible `hypothesis`. The reader
    MUST verify source digest, deletion and span on each call (Store.read_source).
    A source without a matching named entity is excluded rather than guessed.
    """
    if type(retained) is not list or len(retained) > 64 or not callable(read_source):
        raise ValueError('UNBOUNDED_OR_UNVERIFIED_INPUT')
    if not (isinstance(cap,int) and 128 <= cap <= 4096 and
            isinstance(slots,int) and 1 <= slots <= 12 and
            isinstance(excerpt_chars,int) and 1 <= excerpt_chars <= 960):
        raise ValueError('BOUNDS')
    entities = named_entities(current)
    if not entities:
        return {'revision':REVISION,'items':[],'reasons':{'NO_CURRENT_NAMED_ENTITY':len(retained)},
                'authority':'SOURCE_POINTER_ONLY','canonical_gate_pass':False}
    selected=[];native=[];reasons=Counter();seen=set();eligible=[]
    for item in retained[:slots]:
        if type(item) is not dict:
            reasons['BAD_ITEM'] += 1;continue
        if (item.get('role')!='B2_GIST' or item.get('session')!=session or
                item.get('generation')!=generation or item.get('model_revision')!=revision or
                item.get('event_id')==current_event_id):
            reasons['OUT_OF_SCOPE'] += 1;continue
        ref=item.get('source_ref')
        if (type(ref) is not dict or type(ref.get('source_id')) is not str or
                type(ref.get('sha256')) is not str or
                re.fullmatch(r'[0-9a-f]{64}',ref['sha256']) is None or
                type(ref.get('char_start')) is not int or type(ref.get('char_end')) is not int or
                ref['char_start'] < 0 or ref['char_end'] < ref['char_start'] or
                ref.get('modality')!='text'):
            reasons['BAD_REF'] += 1;continue
        if ref['source_id'] in seen:
            reasons['DUPLICATE_SOURCE'] += 1;continue
        try:
            source=read_source(ref)
            if type(source) is not str or len(source) > MAX_SOURCE_CHARS or len(source)!=ref['char_end']-ref['char_start']:
                raise ValueError('SOURCE_LENGTH')
            prior=named_entities(source)
            if not prior or not (entities & prior):
                reasons['PROJECT_MISMATCH'] += 1;continue
            excerpt_ref=dict(ref,char_end=min(ref['char_end'],ref['char_start']+excerpt_chars))
            excerpt=read_source(excerpt_ref)
            if excerpt!=source[:len(excerpt)] or len(excerpt)!=excerpt_ref['char_end']-excerpt_ref['char_start']:
                raise ValueError('EXCERPT_CHANGED')
        except (ValueError,OSError):
            reasons['SOURCE_UNAVAILABLE'] += 1;continue
        hypothesis=item.get('hypothesis','')
        if type(hypothesis) is not str:hypothesis=''
        context={'exact_source_excerpt':excerpt,'hypothesis':hypothesis[:120],
                 'authority':'PRIOR_HYPOTHESIS_NOT_FACT'}
        seen.add(ref['source_id'])
        cues=sum(bool(re.search(rx,excerpt,re.I)) for rx in
                 (r'\bbudget\b',r'\bdeadline\b',r'\blocal-only\s+requirement\b'))
        eligible.append((item,excerpt_ref,context,cues))
    # A value-free JEF attention cue: when the current question explicitly
    # requires older rules, spend B2's bounded context on the older source
    # containing the rule *words*, not on a recent supplier sheet. B1 handles
    # recent exact options. This is source selection, never rule truth.
    current_has_rules = all(re.search(rx,current,re.I) for rx in (
        r'\bbudget\s+\d+\s+euros?\b',
        r'\bdeadline\s+\d+\s+days?\b',
        r'\blocal-only\s+requirement:?\s+(?:true|false)\b'))
    prior_requested = (bool(re.search(r'\b(?:earlier|prior|previous)\b',current,re.I)) and
                       bool(re.search(r'\brules?\b',current,re.I)) and
                       not current_has_rules and
                       not re.search(r'\b(?:superseded|revised)\b',current,re.I))
    if prior_requested:
        eligible.sort(key=lambda row:row[3],reverse=True)
    for item,excerpt_ref,context,_ in eligible:
        if _json_len(native+[context]) > cap:
            reasons['CAP'] += 1;continue
        native.append(context)
        selected.append({'offer_id':item.get('offer_id'),'source_ref':excerpt_ref,'native_context':context})
    return {'revision':REVISION,'items':selected,'reasons':dict(reasons),
            'authority':'SOURCE_POINTER_ONLY','canonical_gate_pass':False}
