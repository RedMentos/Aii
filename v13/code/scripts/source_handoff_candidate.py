"""Frozen-run-safe source-handoff candidate; does not modify runtime files.

Render a reviewable patch, or load the candidate modules for offline regression
tests. Native-model utility must be measured separately after the frozen cohort.
"""
import argparse
import difflib
import hashlib
import json
from pathlib import Path
import types

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = 'docs/proofs/continuation-20261011/source-handoff-baseline'
NAMES = ('v13/bodyview.py', 'v13/cognition.py', 'v13/runtime.py')


ANALYST_CONTEXT = '''    def analyst_context(self,offers,e,version):
        """Render selected hypotheses and only their source-verified quotations.

        An exact quote proves transport of source text, not semantic truth. A
        retained source merely available to a body is never copied wholesale.
        Persisted Query/Offer bindings, current event/generation/version, exact
        quote equality and source digest/range are rechecked before delivery.
        """
        rendered=[]
        for supplied in offers:
            row=self.s.one("SELECT payload FROM packets WHERE id=? AND kind='OfferPacket'",(supplied.get('packet_id'),))
            if not row:raise ValueError('Consumer offer is not stored')
            offer=json.loads(row['payload'])
            if (offer!=supplied or not offer_is_fresh(offer,e['event_id'],e['brain_generation_id'],version)
                    or offer.get('model_revision')!=self.r.models.revision(offer['role'])):
                raise ValueError('Consumer offer binding changed or expired')
            query_row=self.s.one("SELECT payload FROM packets WHERE id=? AND kind='QueryPacket'",(offer.get('query_packet_id'),))
            if not query_row:raise ValueError('Consumer query binding missing')
            query=json.loads(query_row['payload'])
            if (query['event_id']!=e['event_id'] or query['brain_generation_id']!=e['brain_generation_id']
                    or query['target_role']!=offer['role'] or query.get('based_on_state_version')!=version
                    or query['source_refs']!=[e['source_ref']]
                    or query.get('context_source_refs',[])!=offer.get('context_source_refs',[])):
                raise ValueError('Consumer query scope changed')
            allowed=[e['source_ref']]+query.get('context_source_refs',[])
            verified=[]
            for ref in offer['evidence_refs']:
                bound=any(all(ref.get(k)==base.get(k) for k in ('source_id','sha256','modality'))
                    and base['char_start']<=ref['char_start']<ref['char_end']<=base['char_end'] for base in allowed)
                if not bound:raise ValueError('Consumer quote outside supplied source scope')
                text=self.s.read_source(ref)
                if text not in offer['offer'].get('quotes',[]):raise ValueError('Consumer quote differs from offered quote')
                verified.append({'text':text,'source_ref':dict(ref),'verification':'EXACT_SOURCE_SUBSTRING_ONLY',
                                 'semantic_truth_authority':False})
            rendered.append({'role':offer['role'],'offer_packet_id':offer['packet_id'],
                'hypothesis':{k:offer['offer'][k] for k in ('summary','uncertainty','needs_reentry')},
                'hypothesis_authority':'MODEL_HYPOTHESIS_NOT_FACT','verified_quotes':verified})
        return rendered
'''


def _replace(text, old, new):
    if text.count(old) != 1:
        raise ValueError('Candidate source anchor changed: ' + old[:100])
    return text.replace(old, new, 1)


def _transform(original):
    changed = dict(original)
    changed['v13/bodyview.py'] = _replace(changed['v13/bodyview.py'],
        "view={'world':{'mode':world.get('mode','NO_OBSERVATIONS'),'observed_actions':world.get('observed_action_count',0),",
        "action_mode=world.get('mode','NO_OBSERVATIONS')\n"
        "    if action_mode=='NO_OBSERVATIONS':action_mode='NO_COMPLETED_OWN_DIGITAL_ACTIONS'\n"
        "    view={'world':{'scope':'OWN_DIGITAL_ACTION_OUTCOMES_ONLY','mode':action_mode,'observed_actions':world.get('observed_action_count',0),")
    changed['v13/cognition.py'] = _replace(changed['v13/cognition.py'],
        "body_state is your own world/self/skill state, not a fact.'",
        "body_state is own world/self/skill state, never source evidence. Its world.mode counts only completed own digital actions; it says nothing about available source knowledge. self.external_tools limits tool execution, not reading supplied text or reasoning about its constraints.'")
    changed['v13/cognition.py'] = _replace(changed['v13/cognition.py'],
        "Earlier context contains exact source excerpts and fallible prior hypotheses. Never treat a prior hypothesis as a fact. Quotes may cite only the current source or an exact source excerpt.'",
        "Earlier context separates exact source excerpts from fallible prior hypotheses. Use relevant earlier source excerpts when current text leaves a rule unstated; prefer an explicit current-source revision when the same rule changes. Never treat a prior hypothesis as a fact. Select short exact quotes carrying the source rules needed by your summary; only your verified quotes, not the full earlier context, are passed to the answer component. If required evidence is absent, state that uncertainty and request re-entry rather than inventing it. Quotes may cite only current source text or an exact earlier source excerpt, never own-state or hypotheses.'")
    changed['v13/cognition.py'] = _replace(changed['v13/cognition.py'],
        '    def communicate(self,offer,receiver,fast=None):',
        ANALYST_CONTEXT + '    def communicate(self,offer,receiver,fast=None):')
    changed['v13/runtime.py'] = _replace(changed['v13/runtime.py'],
        "if selected:volatile.append(('HYPOTHESES','\\n'+prompt(self.cfg,'hypotheses'),[p['offer'] for p in selected]))",
        "if selected:volatile.append(('HYPOTHESES','\\n'+prompt(self.cfg,'hypotheses'),self.cognition.analyst_context(selected,e,version)))")
    changed['v13/runtime.py'] = _replace(changed['v13/runtime.py'],
        "for item in selected:context_refs.extend(item['provenance'])",
        "for item in selected:context_refs.extend(item['provenance']+item['evidence_refs'])")
    return original, changed


def sources(root=ROOT):
    """Accept only the exact frozen baseline or complete exact candidate.

    Mixed or independently edited runtime sources fail shut. The archived
    baseline is digest-bound; this also keeps candidate regressions runnable
    after the reviewed patch is integrated, without permissive anchor fallback.
    """
    folder = root / SNAPSHOT
    manifest = json.loads((folder/'manifest.json').read_text())
    if manifest.get('schema') != 'SOURCE_HANDOFF_FROZEN_BASELINE_V1' or set(manifest['files']) != set(NAMES):
        raise ValueError('Candidate baseline manifest changed')
    original = {}
    for name, expected in manifest['files'].items():
        data = (folder/Path(name).name).read_bytes()
        if hashlib.sha256(data).hexdigest() != expected:
            raise ValueError('Candidate frozen baseline digest changed: '+name)
        original[name] = data.decode()
    original, changed = _transform(original)
    actual = {name:(root/name).read_text() for name in NAMES}
    if actual != original and actual != changed:
        raise ValueError('Runtime is neither exact frozen baseline nor complete reviewed candidate')
    return original, changed


def patch_text(root=ROOT):
    original, changed = sources(root)
    return ''.join(''.join(difflib.unified_diff(original[name].splitlines(True),
        changed[name].splitlines(True), fromfile='a/'+name, tofile='b/'+name)) for name in original)


def load_candidate(name, root=ROOT):
    """Load in the v13 package namespace; no on-disk runtime mutation."""
    _, changed = sources(root)
    module = types.ModuleType('v13._source_handoff_candidate_' + name)
    module.__package__ = 'v13'
    module.__file__ = str(root / ('v13/' + name + '.py'))
    exec(compile(changed['v13/' + name + '.py'], module.__file__, 'exec'), module.__dict__)
    return module


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(patch_text())
    print(str(args.out))


if __name__ == '__main__':
    main()
