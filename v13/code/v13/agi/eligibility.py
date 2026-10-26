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


# Option markers are boundaries, even when A and B share one sentence.
# A current option *statement* overrides earlier quotes; a bare mention does not.
_OPTION_MARKER = re.compile(r'\boption\s+([AB])\b', re.I)
_OPTION_FIELD = re.compile(r'\b(?:costs?|price|duration|days?|local|euros?)\b', re.I)
_OPTION_COST = re.compile(r'\bcost\s+(\d+)\b', re.I)
_OPTION_DAYS = re.compile(r'\b(\d+)\s+days?\b', re.I)
_OPTION_LOCAL = re.compile(r'\blocal\s+(true|false)\b', re.I)


def option_clauses(entity, text):
    markers = list(_OPTION_MARKER.finditer(str(text)))
    clauses = []
    for i, match in enumerate(markers):
        if match.group(1).upper() != entity.upper():
            continue
        end = markers[i + 1].start() if i + 1 < len(markers) else len(text)
        clauses.append(str(text)[match.start():end].split('.', 1)[0])
    return clauses


def option_clause(entity, text):
    clauses = option_clauses(entity, text)
    return clauses[0] if clauses else ''


def _option_statement(clause):
    return _OPTION_FIELD.search(clause) is not None


def _option_matches(option, clause):
    # Never convert a model-provided string 'false' using bool('false') == True.
    if (type(option.get('cost')) is not int or type(option.get('days')) is not int
            or type(option.get('local')) is not bool):
        return False
    costs = {int(v) for v in _OPTION_COST.findall(clause)}
    days = {int(v) for v in _OPTION_DAYS.findall(clause)}
    local = {v.lower() == 'true' for v in _OPTION_LOCAL.findall(clause)}
    return (costs == {option['cost']} and days == {option['days']}
            and local == {option['local']})


def option_stated(option, texts):
    for text in texts:
        for clause in option_clauses(option['entity'], text):
            if _option_matches(option, clause):
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
        if override and (len(override) != 1 or v not in override): rejected.append(rule+':conflicts_current'); kept[rule] = None
        elif not any(stated(rule, v, t) for t in texts): rejected.append(rule+':not_stated'); kept[rule] = None
        else: kept[rule] = v
    for o in options:
        current_statements = [c for c in option_clauses(o['entity'], current) if _option_statement(c)]
        if current_statements and not all(_option_matches(o, c) for c in current_statements):
            # Keep the original option_not_stated diagnostic for existing callers.
            # The additional conflicts_current tag identifies stale-source precedence.
            rejected.extend((o['entity']+':option_not_stated', o['entity']+':conflicts_current'))
        elif not current_statements and not option_stated(o, texts):
            rejected.append(o['entity']+':option_not_stated')
    if any(r.endswith(('option_not_stated', 'conflicts_current')) and
           r.split(':')[0] in ('A', 'B') for r in rejected):
        kept['budget'] = None
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


# Live path (Thread Q, 2026-10-21): the same recipe as a C5 TOOL_CALL in the runtime turn (toolstep.py), like list_arith.
# A BOOT wording rule spots a decision over Option A/B; C3 only copies typed values (READ_SCHEMA); decide() keeps the
# guard, so values that are not stated after their rule word, or that conflict with the current message, never count.
# Evidence = current user message + EARLIER_EXACT texts: the user's own earlier messages of this session (stored source
# text, not model output) and source-verified quotes of the selected body offers. Claim limit: English, the fixture
# wording ("budget 61 euros", "Option A: cost 45 euros, duration 7 days, local true"); other wordings get UNKNOWN.
OPTION_PAIR = re.compile(r'\boption\s+A\b[\s\S]*\boption\s+B\b', re.I)
DECIDE = re.compile(r'(?i)\b(?:choose|chooses|pick|select|recommend|cheapest|eligib\w*|which\s+option|go\s+with|decide)\b')
MAX_TEXT = 2000
MAX_EARLIER = 6

# Run576: narrow explicit project evidence before either fixed or model typed read.
# The label is deliberately lexical: uncertain aliases never become authority.
_PROJECT_LABEL = re.compile(r'\\bproject[ \\t]+([a-z][a-z0-9_-]{0,39})\\b', re.I)


def project_labels(text):
    """Explicit English 'Project <name>' labels; no guessed aliases or topic inference."""
    return frozenset(m.group(1).casefold() for m in _PROJECT_LABEL.finditer(str(text)))


def scope_earlier(current, history=(), quotes=()):
    """Separate earlier exact evidence by the current named project.

    One explicit label admits only earlier sources with exactly that label.
    No label admits only unlabelled sources. Multiple current labels admit no
    earlier evidence. The caller retains its current-source rules and options.
    This is a fail-closed source boundary, not a semantic project resolver.
    """
    target = project_labels(current)
    if len(target) > 1:
        return [], []
    def allowed(source):
        labels = project_labels(source)
        return labels == target if target else not labels
    return ([source for source in history if allowed(source)],
            [source for source in quotes if allowed(source)])
READ_SYSTEM = ('Read the project rules and the two options. Return JSON only. Copy every number exactly as written; never '
               'calculate anything. budget, deadline, local_only: the value written right after that rule word; if the current '
               'message states a rule, take it from there, otherwise from the earlier text; if a rule is not written anywhere, '
               'use null. options: cost, duration in days and local (true or false) of option A and of option B.')
_READ_OPTION = {'type': 'object', 'additionalProperties': False, 'required': ['entity', 'cost', 'days', 'local'],
                'properties': {'entity': {'type': 'string', 'enum': ['A', 'B']}, 'cost': {'type': 'integer'},
                               'days': {'type': 'integer'}, 'local': {'type': 'boolean'}}}
READ_SCHEMA = {'type': 'object', 'additionalProperties': False, 'required': ['options', 'budget', 'deadline', 'local_only'],
               'properties': {'options': {'type': 'array', 'minItems': 2, 'maxItems': 2, 'items': _READ_OPTION},
                              'budget': {'type': ['integer', 'null']}, 'deadline': {'type': ['integer', 'null']},
                              'local_only': {'type': ['boolean', 'null']}}}
LIVE_NOTE = ('Answer with this decision first, in your own words, then the remaining budget. If the decision is UNKNOWN, say '
             'which rule is missing and do not choose an option.')
FIRST_NOTE = ('The user already sees the "answer" sentence as the start of your reply. Continue right after it with one or two '
              'short sentences that explain it with the numbers in "details". Do not repeat it and do not choose a different option.')


def question(text):
    """BOOT rule: the message names Option A and Option B and asks for a choice/eligibility."""
    t = str(text)
    return len(t) <= MAX_TEXT and OPTION_PAIR.search(t) is not None and DECIDE.search(t) is not None


def read_prompt(current, earlier):
    body = ''
    if earlier:
        body = 'Earlier exact text (older):\n'+'\n'.join('- '+str(t) for t in earlier)+'\n\n'
    body += 'Current message (newest; a rule stated here overrides the earlier text):\n'+str(current)
    return [{'role': 'system', 'content': READ_SYSTEM}, {'role': 'user', 'content': body}]


def read_values(runner, current, earlier, cancel, deadline, max_tokens=200):
    """The model only copies typed values; returns the READ_SCHEMA object or raises ValueError/JSON errors."""
    import json
    x = json.loads(''.join(runner.generate(read_prompt(current, earlier), cancel, deadline, max_tokens, READ_SCHEMA)))
    if not isinstance(x, dict) or set(x) != set(READ_SCHEMA['required']): raise ValueError('read_schema')
    ents = [o.get('entity') for o in x['options']] if isinstance(x['options'], list) else []
    if ents != ['A', 'B']: raise ValueError('options')
    return x


_OPT_VALUE = {'cost': r'\bcost\s+(\d+)\b', 'days': r'\b(\d+)\s+days?\b', 'local': r'\blocal\s+(true|false)\b'}


def _one(values):
    return next(iter(values)) if len(values) == 1 else None


def fixed_read(current, history=(), quotes=()):
    """Non-generative reader (2026-10-21 user decision: rules are read and checked by a fixed component, never by a
    language model). Same READ_SCHEMA shape as read_values, without any model call.

      rule value  from the fixed rule wording only ("budget 61 euros", "deadline 8 days", "local-only requirement: true");
                  the current message wins; else the newest earlier user message that states it; else body quotes only
                  if they all agree. Two different values in the same text, or disagreeing quotes -> null (recipe UNKNOWN).
      options     from each option's own clause ("Option A: cost 45 euros, duration 7 days, local true"), current
                  message first, then newest earlier text; a missing value raises ValueError (no proposal).
    Claim limit: the canonical English wording; anything else stays null and the recipe refuses instead of guessing."""
    out = {}
    for rule in ('budget', 'deadline', 'local_only'):
        value = None; found = stated_values(rule, current)
        if found: value = _one(found)
        else:
            for text in reversed(list(history)):
                found = stated_values(rule, text)
                if found: value = _one(found); break
            else:
                found = set().union(*(stated_values(rule, q) for q in quotes)) if quotes else set()
                value = _one(found)
        out[rule] = value
    options = []
    for entity in ('A', 'B'):
        clause = next((c for c in (option_clause(entity, x) for x in [current, *reversed(list(history)), *quotes]) if c), '')
        o = {'entity': entity}
        for key, rx in _OPT_VALUE.items():
            m = re.search(rx, clause, re.I)
            if not m: raise ValueError('option_'+entity+'_'+key)
            o[key] = (m.group(1).lower() == 'true') if key == 'local' else int(m.group(1))
        options.append(o)
    out['options'] = options
    return out


def args_for(values, current, earlier):
    """READ_SCHEMA values -> tool args (an unavailable rule is omitted, so the tool treats it as unavailable)."""
    a, b = values['options']
    args = {'current': str(current), 'a_cost': a['cost'], 'a_days': a['days'], 'a_local': a['local'],
            'b_cost': b['cost'], 'b_days': b['days'], 'b_local': b['local']}
    if earlier: args['quotes'] = '\n'.join(str(t).replace('\n', ' ') for t in earlier)
    for k in ('budget', 'deadline', 'local_only'):
        if values.get(k) is not None: args[k] = values[k]
    return args


# Fixed reader (Thread „STEP2-Nutzen Engpass“, 2026-10-22; cfg eligibility_reader='fixed'). User decision 2026-10-21: rules are
# read by a fixed, non-generative component, never by a language model (WP-Z3b: C3 350M always says local_only=true and
# often keeps a stale rule). Rule values: the current message wins; otherwise the newest earlier text that states the rule.
# A text that states two different values for one rule gives no value (refuse, never guess). Options: their own clause in
# the current message, else in the newest earlier text; an option this wording does not cover leaves options to the model.
_OPT_VALUES = (r'\bcost\s+(\d+)\b', r'\b(\d+)\s+days?\b', r'\blocal\s+(true|false)\b')


def fixed_rule(rule, current, earlier=()):
    for text in (current, *reversed(list(earlier))):
        found = stated_values(rule, str(text))
        if found: return found.pop() if len(found) == 1 else None
    return None


def fixed_option(entity, current, earlier=()):
    for text in (current, *reversed(list(earlier))):
        clauses = [c for c in option_clauses(entity, str(text)) if _option_statement(c)]
        if not clauses: continue
        values = []
        for clause in clauses:
            got = [re.findall(rx, clause, re.I) for rx in _OPT_VALUES]
            if any(len(set(g)) != 1 for g in got): return None
            values.append({'entity': entity, 'cost': int(got[0][0]),
                           'days': int(got[1][0]), 'local': got[2][0].lower() == 'true'})
        return values[0] if all(v == values[0] for v in values) else None
    return None


def read_fixed(current, earlier=()):
    """READ_SCHEMA-shaped values without a model; 'options' is None when this wording does not cover both options."""
    opts = [fixed_option(x, current, earlier) for x in 'AB']
    out = {k: fixed_rule(k, current, earlier) for k in ('budget', 'deadline', 'local_only')}
    out['options'] = opts if all(opts) else None
    return out


def with_fixed_rules(values, fixed):
    """Model-read options, rules only from the fixed reader (the model's rule values are discarded)."""
    return dict(values, **{k: fixed[k] for k in ('budget', 'deadline', 'local_only')})


def decision_line(result):
    """One readable line: what the recipe decided (used by the TOOL_RESULT layer and the broker correction)."""
    act = result['action']
    head = {'A': 'choose Option A', 'B': 'choose Option B', 'NONE': 'no option is eligible',
            'UNKNOWN': 'decision UNKNOWN (a rule is missing or not stated exactly)'}.get(act, str(act))
    parts = []
    for o in result['options']:
        if o['eligible'] is None: parts.append(f"Option {o['entity']}: cost {o['cost']} euros, {o['days']} days")
        else: parts.append(f"Option {o['entity']}: remaining budget {o['remaining']} euros, {'eligible' if o['eligible'] else 'not eligible'}")
    return head+' ('+'; '.join(parts)+')'


def unresolved(args, result):
    """Rules the recipe could not use: not read at all, not stated after the rule word, or conflicting with the current message."""
    out = [k for k in ('budget', 'deadline', 'local_only') if args.get(k) is None]
    out += [r.split(':')[0] for r in result.get('rejected', []) if r.split(':')[0] in ('budget', 'deadline', 'local_only')]
    return sorted(set(out), key=out.index)


def answer_sentence(args, result):
    """The decision phrased as the start of an answer (TOOL_RESULT layer)."""
    act = result['action']
    left = {o['entity']: o['remaining'] for o in result['options']}
    if act in ('A', 'B'): return f'Choose Option {act}. Remaining budget: {left[act]} euros.'
    if act == 'NONE': return 'Neither option is eligible.'
    miss = unresolved(args, result)
    if miss:
        names = [m.replace('_', '-') for m in miss]
        both = names[0] if len(names) == 1 else ', '.join(names[:-1])+' and '+names[-1]
        return f"I cannot decide yet: the {both} {'rule is' if len(names) == 1 else 'rules are'} missing or not stated exactly."
    return 'I cannot decide yet: an option is not stated exactly.'


def final_text(args, result):
    """UNKNOWN/NONE under cfg tool_answer_first: the whole answer, fixed text, no body continuation (dev seed 7: the 350M
    body went on to pick an option after "I cannot decide yet" in 2 of 3 missing-rule tasks)."""
    if result['action'] == 'NONE':
        return answer_sentence(args, result)+' '+'; '.join(
            f"Option {o['entity']}: {o['cost']} euros, {o['days']} days, {'local' if o['local'] else 'not local'}, not eligible" for o in result['options'])+'.'
    miss = unresolved(args, result)
    names = [m.replace('_', '-') for m in miss]
    both = ', '.join(names[:-1])+' and '+names[-1] if len(names) > 1 else ''.join(names)
    ask = ('Please tell me the '+both+(' rule.' if len(names) == 1 else ' rules.')) if miss \
        else 'Please state both options with cost, duration and local.'
    return answer_sentence(args, result)+' '+ask


_UNKNOWN = re.compile(r"(?i)\b(?:unknown|cannot (?:be )?(?:decide|determine|choose|tell|make)\w*|can't (?:decide|determine|choose|tell)|"
                      r"not enough information|insufficient information|missing|not (?:stated|given|provided|specified|known)|unavailable)\b")
_NONE = re.compile(r'(?i)\b(?:neither|none of (?:the|them)|no option|no eligible|nothing is eligible|both (?:are|options are) (?:not|in)eligible)\b')
_PICK = re.compile(r'(?i)\b(?:choose|chose|pick|select|recommend|go with|cheapest eligible(?: option)? is|best (?:choice|option) is|answer(?: is)?:?)\s+(?:is\s+)?(?:the\s+)?(?:option\s+)?([AB])\b')
_POS = re.compile(r"(?i)\boption\s+([AB])\s+(?:is|would be|remains)\s+(?:the\s+)?(?:cheaper|cheapest|best|better|most affordable|only|right|recommended|eligible|valid)\b")
_OPT = re.compile(r'(?i)\boption\s+([AB])\b')


def answer_action(text):
    """Which decision a free-text answer commits to: 'A'|'B'|'NONE'|'UNKNOWN'|None (no or mixed signal). Fixed parser."""
    t = str(text or '')
    picks = {m.upper() for m in _PICK.findall(t)}
    if len(picks) == 1: return picks.pop()
    if _NONE.search(t): return 'NONE'
    pos = {m.upper() for m in _POS.findall(t)}
    if len(pos) == 1: return pos.pop()
    if _UNKNOWN.search(t): return 'UNKNOWN'
    opts = {m.upper() for m in _OPT.findall(t)}
    return opts.pop() if len(opts) == 1 else None
