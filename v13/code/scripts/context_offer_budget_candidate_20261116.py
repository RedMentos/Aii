"""Source-bound Context OS fix for selected offers and exact tool results.

Only returns replacement source bytes; it neither activates nor modifies the
frozen runtime. Character budgets are estimates, not native-token counts.
"""
from hashlib import sha256
from pathlib import Path


INPUT_SHA256 = {
    # Frozen release source, and its integrated Termux review-stage output.
    '2fe8bfc4c7857f24411fea71038485900ca6fcbad2ec3361fa4ede080657861f',
    'a35966dbe77a603470d73285eac9c8087163d8cf675a1b8516e3b9f38b267232',
}

_OLD_COMPACT = b'''        # volatile layers: keep order, drop trailing list items beyond the global compact share (POINTER)
        share=clamp(k['global_compact_state'])*budget;vol=[]
        for layer,head,payload in volatile:
            kept=payload;dropped=0
            if isinstance(payload,list):
                while len(kept)>1 and len(dumps(kept))+sum(len(h)+len(dumps(p)) for _,h,p in vol)>share:kept=kept[:-1];dropped+=1
            vol.append((layer,head,kept))
            items.append({'item_id':layer,'layer':layer,'form':'RAW' if not dropped else 'COMPRESSED','chars':len(head)+len(dumps(kept)),'pointers':dropped})
            if dropped:decisions.append('compact_'+layer.lower())
'''

_NEW_COMPACT = b'''        # C4-selected offers and exact tool results are part of the current
        # decision, not disposable history. Reserve them before compacting
        # optional list layers regardless of their position in volatile.
        protected={'HYPOTHESES','TOOL_RESULT','SOURCE_LINKS'}
        mandatory=sum(len(head)+len(dumps(payload)) for layer,head,payload in volatile if layer in protected)
        share=min(clamp(k['global_compact_state'])*budget,max(0,budget-len(stable)-len(query)-mandatory))
        vol=[];optional_used=0
        for layer,head,payload in volatile:
            kept=payload;dropped=0
            if isinstance(payload,list) and layer not in protected:
                while len(kept)>1 and len(head)+len(dumps(kept))+optional_used>share:kept=kept[:-1];dropped+=1
            vol.append((layer,head,kept))
            if layer not in protected:optional_used+=len(head)+len(dumps(kept))
            items.append({'item_id':layer,'layer':layer,'form':'RAW' if not dropped else 'COMPRESSED','chars':len(head)+len(dumps(kept)),'pointers':dropped})
            if dropped:decisions.append('compact_'+layer.lower())
'''

_OLD_PLAN = b'''        applied=st['mode']=='ACTIVE'
        fp_legacy,fp_planned=fingerprint(legacy),fingerprint(planned);last=st['last'].get(role,{})
        cache={'layout_requested':st['layout'],'layout':layout,'fallback_reason':reason,'prompt_cache':'cache_prompt',
'''

_NEW_PLAN = b'''        applied=st['mode']=='ACTIVE'
        fp_legacy,fp_planned=fingerprint(legacy),fingerprint(planned);last=st['last'].get(role,{})
        planned_chars=sum(c for _,c in fp_planned);legacy_chars=sum(c for _,c in fp_legacy)
        planned_over_budget=planned_chars>budget
        returned_over_budget=(planned_chars if applied else legacy_chars)>budget
        if planned_over_budget:decisions.append('estimated_budget_exceeded')
        if returned_over_budget:decisions.append('estimated_returned_budget_exceeded')
        cache={'layout_requested':st['layout'],'layout':layout,'fallback_reason':reason,'prompt_cache':'cache_prompt',
'''

_OLD_BUDGET = b"            mode=st['mode'],layout=layout,applied=applied,budget={'chars':budget,'planned_chars':cache['est_prompt_chars_planned'],'chars_per_token':CHARS_PER_TOKEN},\n"
_NEW_BUDGET = b"            mode=st['mode'],layout=layout,applied=applied,budget={'chars':budget,'planned_chars':cache['est_prompt_chars_planned'],'chars_per_token':CHARS_PER_TOKEN,'planned_over_budget':planned_over_budget,'returned_over_budget':returned_over_budget,'estimate_only':True},\n"


def _replace_once(raw, old, new, name):
    if raw.count(old) != 1:
        raise ValueError('Context OS source anchor mismatch: ' + name)
    return raw.replace(old, new, 1)


def apply_source(raw):
    """Transform only a reviewed exact RAW or integrated-stage source."""
    if not isinstance(raw, bytes) or sha256(raw).hexdigest() not in INPUT_SHA256:
        raise ValueError('Context OS source hash mismatch')
    raw = _replace_once(raw, _OLD_COMPACT, _NEW_COMPACT, 'volatile compaction')
    raw = _replace_once(raw, _OLD_PLAN, _NEW_PLAN, 'plan accounting')
    raw = _replace_once(raw, _OLD_BUDGET, _NEW_BUDGET, 'budget packet')
    compile(raw, 'v13/context_os.py', 'exec')
    return raw


def build_sources(code_dir):
    code_dir = Path(code_dir)
    path = code_dir / 'v13/context_os.py'
    if (code_dir / 'v13').is_symlink() or path.is_symlink() or not path.is_file():
        raise ValueError('Context OS source missing or unsafe')
    return {'v13/context_os.py': apply_source(path.read_bytes())}
