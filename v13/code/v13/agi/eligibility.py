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


def newest_values(rule, history):
    """Values of the newest source in history (oldest -> newest) that states this rule, or an empty set."""
    for text in reversed(history):
        found = stated_values(rule, text)
        if found: return found
    return set()


def newest_quoted(rule, current, quotes, history):
    """WP-Z2k reader: the one value the current source states for this rule, else the one value of the newest earlier
    session source that states it, if a verified quote or the current source states that value; otherwise None."""
    override = stated_values(rule, current)
    if len(override) == 1: return next(iter(override))
    if override: return None
    newest = newest_values(rule, history)
    if len(newest) == 1 and any(stated(rule, next(iter(newest)), t) for t in [current, *quotes]): return next(iter(newest))
    return None


def decide(rules, options, current, quotes=(), history=(), rule_reader='model'):
    """rules: {'budget','deadline','local_only'} extracted (None = model says unavailable).
    current: current source text; quotes: verified exact quotes. Returns action, options, rejected reasons.
    history (WP-Z2g recency guard, empty = previous behaviour): earlier exact sources of this session, oldest -> newest.
    A rule value not stated in the current source counts only if the newest earlier source that states that rule
    states this value; an exact but superseded quote ('Budget 60 euros' before 'New budget 80 euros') -> unavailable.
    WP-Z2f: with more B2 context, 27/27 wrong decisions came from such stale quotes.
    rule_reader (WP-Z2k, needs history): 'model' = the extracted values (default); 'newest_quoted' = a rule value the
    extraction got wrong or left empty is replaced by newest_quoted() when that finds one. WP-Z2j: with kickoff and
    revision both quoted, the 350M consumer took the superseded value in 10/10 rows."""
    if rule_reader not in ('model', 'newest_quoted'): raise ValueError('rule_reader model|newest_quoted')
    texts = [current, *quotes]; rejected = []; kept = {}; read = []
    if rule_reader == 'newest_quoted' and history:
        rules = dict(rules)
        for rule in ('budget', 'deadline', 'local_only'):
            n = newest_quoted(rule, current, quotes, history)
            if n is not None and n != rules.get(rule): rules[rule] = n; read.append(rule)
    for rule in ('budget', 'deadline', 'local_only'):
        v = rules.get(rule)
        if v is None: kept[rule] = None; continue
        override = stated_values(rule, current)
        if override and v not in override: rejected.append(rule+':conflicts_current'); kept[rule] = None
        elif not any(stated(rule, v, t) for t in texts): rejected.append(rule+':not_stated'); kept[rule] = None
        elif history and not override and (newest := newest_values(rule, history)) and v not in newest: rejected.append(rule+':superseded'); kept[rule] = None
        else: kept[rule] = v
    for o in options:
        if not option_stated(o, texts): rejected.append(o['entity']+':option_not_stated')
    if any(r.endswith('option_not_stated') for r in rejected): kept['budget'] = None
    action, out = recipe(kept['budget'], kept['deadline'], kept['local_only'], options)
    return {'action': action, 'options': out, 'rejected': rejected, 'read_newest': read,
            'revision': REVISION+('+recency' if history else '')+('+newest' if rule_reader == 'newest_quoted' and history else '')}


def tool(current, a_cost, a_days, a_local, b_cost, b_days, b_local, quotes='', budget=None, deadline=None, local_only=None, history='', rule_reader='model'):
    """ToolRegistry entry point (scalar typed args; quotes and history joined by newlines; omitted rule = unavailable;
    empty history = recency guard off)."""
    options = [{'entity': 'A', 'cost': a_cost, 'days': a_days, 'local': a_local},
               {'entity': 'B', 'cost': b_cost, 'days': b_days, 'local': b_local}]
    return decide({'budget': budget, 'deadline': deadline, 'local_only': local_only}, options, current,
                  [q for q in quotes.split('\n') if q], [h for h in history.split('\n') if h], rule_reader)


SCHEMA = {'current': 'text', 'quotes': 'text?', 'a_cost': 'int', 'a_days': 'int', 'a_local': 'bool',
          'b_cost': 'int', 'b_days': 'int', 'b_local': 'bool', 'budget': 'int?', 'deadline': 'int?', 'local_only': 'bool?', 'history': 'text?', 'rule_reader': 'text?'}
