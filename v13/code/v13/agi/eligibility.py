"""WP-W2c: deterministic eligibility recipe with a rule-anchored evidence guard (Canon §6.5 tool recipe).

Measured basis (docs/proofs/continuation-20261012/calc-tool-ablation, calc-tool-span-ablation): 0.35-1.2B
consumers do not compute budget/deadline/locality eligibility, but read typed values well; they never return
null for a missing rule (they invent budgets) and cannot quote exact spans. So the model only extracts typed
values and this recipe decides; the guard is deterministic and never asks the model for quotes:

  rule value   counts only if the evidence states it directly after its rule word
               ("budget 61 euros", "deadline 8 days", "local-only requirement: false");
               a value that conflicts with a rule stated in the current source counts as unavailable
               (current rules override earlier ones; the recipe refuses instead of repairing)
  option value counts only inside that option's own clause ("Option A: cost 45 euros, duration 7 days, local true")
  anything unavailable -> UNKNOWN with null remaining/eligible

Evidence is only the current source and verified quotes, never analyst hypotheses. READ_LOCAL, off until the
user enables it (IH-H29); SHADOW evidence level, not learned utility.
"""
import re

REVISION = 'eligibility-v2-anchored'
_RULE = {'budget': r'\bbudget(?:\s+of)?\s+{v}\s+euros?\b',
         'deadline': r'\bdeadline(?:\s+of)?\s+{v}\s+days?\b',
         'local_only': r'\blocal-only\s+requirement:?\s+{v}\b'}
_ANY = {'budget': r'\d+', 'deadline': r'\d+', 'local_only': r'(?:true|false)'}


def _token(value):
    if isinstance(value, bool): return 'true' if value else 'false'
    if type(value) is int and value >= 0: return str(value)
    return None


def stated(rule, value, text):
    tok = _token(value)
    return tok is not None and re.search(_RULE[rule].format(v=re.escape(tok)), text, re.I) is not None


def stated_values(rule, text):
    found = re.findall(_RULE[rule].format(v='('+_ANY[rule]+')'), text, re.I)
    return {(v.lower() == 'true') if rule == 'local_only' else int(v) for v in found}


def option_clause(entity, text):
    m = re.search(r'\boption\s+'+re.escape(entity)+r'\b[^.]*', text, re.I)
    return m.group(0) if m else ''


def option_stated(option, texts):
    for text in texts:
        clause = option_clause(option['entity'], text)
        if (clause and re.search(r'\bcost\s+'+str(option['cost'])+r'\b', clause, re.I)
                and re.search(r'\b'+str(option['days'])+r'\s+days?\b', clause, re.I)
                and re.search(r'\blocal\s+'+_token(bool(option['local']))+r'\b', clause, re.I)):
            return True
    return False


def recipe(budget, deadline, local_only, options):
    """Cheapest eligible option, A on a tie; any missing rule -> UNKNOWN with null remaining/eligible."""
    known = budget is not None and deadline is not None and local_only is not None
    out = []
    for o in options:
        ok = None if not known else o['cost'] <= budget and o['days'] <= deadline and (o['local'] or not local_only)
        out.append({'entity': o['entity'], 'cost': o['cost'], 'remaining': budget-o['cost'] if known else None,
                    'days': o['days'], 'local': o['local'], 'eligible': ok})
    if not known: return 'UNKNOWN', out
    eligible = [o for o in out if o['eligible']]
    return (min(eligible, key=lambda o: (o['cost'], o['entity']))['entity'] if eligible else 'NONE'), out


def decide(rules, options, current, quotes=()):
    """rules: {'budget','deadline','local_only'} extracted (None = model says unavailable).
    current: current source text; quotes: verified exact quotes. Returns action, options, rejected reasons."""
    texts = [current, *quotes]; rejected = []; kept = {}
    for rule in ('budget', 'deadline', 'local_only'):
        v = rules.get(rule)
        if v is None: kept[rule] = None; continue
        override = stated_values(rule, current)
        if override and v not in override: rejected.append(rule+':conflicts_current'); kept[rule] = None
        elif not any(stated(rule, v, t) for t in texts): rejected.append(rule+':not_stated'); kept[rule] = None
        else: kept[rule] = v
    for o in options:
        if not option_stated(o, texts): rejected.append(o['entity']+':option_not_stated')
    if any(r.endswith('option_not_stated') for r in rejected): kept['budget'] = None
    action, out = recipe(kept['budget'], kept['deadline'], kept['local_only'], options)
    return {'action': action, 'options': out, 'rejected': rejected, 'revision': REVISION}


def tool(current, a_cost, a_days, a_local, b_cost, b_days, b_local, quotes='', budget=None, deadline=None, local_only=None):
    """ToolRegistry entry point (scalar typed args; quotes joined by newlines; omitted rule = unavailable)."""
    options = [{'entity': 'A', 'cost': a_cost, 'days': a_days, 'local': a_local},
               {'entity': 'B', 'cost': b_cost, 'days': b_days, 'local': b_local}]
    return decide({'budget': budget, 'deadline': deadline, 'local_only': local_only}, options, current,
                  [q for q in quotes.split('\n') if q])


SCHEMA = {'current': 'text', 'quotes': 'text?', 'a_cost': 'int', 'a_days': 'int', 'a_local': 'bool',
          'b_cost': 'int', 'b_days': 'int', 'b_local': 'bool', 'budget': 'int?', 'deadline': 'int?', 'local_only': 'bool?'}


# Live answer path (2026-10-20 thread "STEP2-Nutzen Engpass", follow-up): v13/toolstep.ToolStep proposes this tool for a
# decision question when the user enabled it. C3 only extracts typed values from the current source and the verified
# body quotes (offer evidence refs); the recipe above decides. Measured replay basis: docs/proofs/continuation-20261020/
# step2-quote-context/BEFUND.md (24/30 retain rows exact, 0 wrong committed, with B2 quote context on).
LIVE_PROPOSER = 'boot-eligibility-v1'
_OPTION = {'type': 'object', 'additionalProperties': False, 'required': ['entity', 'cost', 'days', 'local'],
           'properties': {'entity': {'type': 'string', 'enum': ['A', 'B']}, 'cost': {'type': 'integer'},
                          'days': {'type': 'integer'}, 'local': {'type': 'boolean'}}}
EXTRACT_SCHEMA = {'type': 'object', 'additionalProperties': False,
                  'required': ['project', 'options', 'budget', 'deadline', 'local_only'],
                  'properties': {'project': {'type': 'string'},
                                 'options': {'type': 'array', 'minItems': 2, 'maxItems': 2, 'items': _OPTION},
                                 'budget': {'type': ['integer', 'null']},
                                 'deadline': {'type': ['integer', 'null']},
                                 'local_only': {'type': ['boolean', 'null']}}}
EXTRACT_SYSTEM = ('You read a decision task and return the required JSON only. Extract typed values, do not decide. '
                  'For option A and option B give its own cost, days and local flag. Give the project rules: budget (euros), '
                  'deadline (days) and local_only (true or false). Rules may be stated in the current source or in verified '
                  'quotes of earlier project rules; explicit updated rules in the current source override earlier rules. '
                  'If a rule is stated in neither, return null for it. Never invent a missing rule.')
_ASK = re.compile(r'\boption\s+a\b[\s\S]*\boption\s+b\b', re.I)
_DECIDE = re.compile(r'\beligib|\bcheapest\b|\bwhich option\b|\bbudget\b', re.I)


def asks(text):
    """BOOT wording rule: a choice between option A and option B under budget/eligibility rules (not learned)."""
    t = str(text)
    return len(t) <= 4000 and bool(_ASK.search(t)) and bool(_DECIDE.search(t))


def read(runner, current, quotes, cancel, deadline, max_tokens=256):
    """C3 extracts typed values only; returns the parsed dict or raises ValueError/JSON errors."""
    import json
    user = json.dumps({'current_source': str(current), 'verified_quotes': list(quotes)}, ensure_ascii=False)
    raw = ''.join(runner.generate([{'role': 'system', 'content': EXTRACT_SYSTEM}, {'role': 'user', 'content': user}],
                                  cancel, deadline, max_tokens, EXTRACT_SCHEMA))
    x = json.loads(raw)
    if not isinstance(x, dict) or set(x) != set(EXTRACT_SCHEMA['required']) or sorted(o.get('entity') for o in x['options']) != ['A', 'B']:
        raise ValueError('extract_schema')
    return x


def args_from(extracted, current, quotes):
    """Extracted values -> ToolRegistry args (unavailable rules are omitted, never None)."""
    o = {x['entity']: x for x in extracted['options']}
    args = {'current': str(current), 'quotes': '\n'.join(quotes), 'a_cost': o['A']['cost'], 'a_days': o['A']['days'],
            'a_local': o['A']['local'], 'b_cost': o['B']['cost'], 'b_days': o['B']['days'], 'b_local': o['B']['local']}
    for k in ('budget', 'deadline', 'local_only'):
        if extracted[k] is not None: args[k] = extracted[k]
    return args


def label(result):
    """Readable decision line for the answering body (the measured lesson of R4: raw JSON is ignored by C3)."""
    if result['action'] == 'UNKNOWN':
        return 'UNKNOWN: a required project rule (budget, deadline or local-only) is not stated in the source or a verified quote.'
    parts = [f"option {o['entity']}: remaining {o['remaining']}, {'eligible' if o['eligible'] else 'not eligible'}" for o in result['options']]
    return ('choose option '+result['action'] if result['action'] in ('A', 'B') else 'no option is eligible (NONE)')+'; '+'; '.join(parts)
