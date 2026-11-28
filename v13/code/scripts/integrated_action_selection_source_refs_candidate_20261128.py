"""Add validated coalition SourceRefs to the staged C5 ActionSelection packet.

The source Focal module remains byte-pinned. This overlay runs after the
existing staged C4/arithmetic/audio/receiver builders and modifies only the
reviewed staged ActionGate consumer.
"""
from pathlib import Path
import hashlib


FOCAL_SOURCE_BLOB_SHA1 = "a0588a768cc91266ef02243bcfda2e631860d8ad"
MAX_CONTEXT_SOURCE_REFS = 64
MAX_CONTEXT_ITEMS = 16


def _git_blob_sha1(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def _replace(raw: bytes, old: bytes, new: bytes, label: str) -> bytes:
    if not isinstance(raw, bytes) or raw.count(old) != 1:
        raise ValueError("ActionSelection source-context anchor changed: " + label)
    return raw.replace(old, new, 1)


def apply_sources(code_dir: Path, sources: dict[str, bytes]) -> dict[str, bytes]:
    code_dir = Path(code_dir).resolve(strict=True)
    source_path = code_dir / "v13/focal.py"
    if source_path.is_symlink() or not source_path.is_file():
        raise ValueError("pinned Focal source missing or unsafe")
    if _git_blob_sha1(source_path.read_bytes()) != FOCAL_SOURCE_BLOB_SHA1:
        raise ValueError("pinned Focal source changed; review a new ActionSelection overlay")
    if not isinstance(sources, dict) or not isinstance(sources.get("v13/focal.py"), bytes):
        raise ValueError("staged Focal output missing")
    result = dict(sources)
    focal = result["v13/focal.py"]
    if b"SCALE_AWARE_C4_RULE" not in focal or b"direct_action='SOURCE_COPY'" not in focal:
        raise ValueError("staged C4/arithmetic ActionGate contract missing")

    anchor = (
        b"        return out\n"
        b"    def select(self,e,*,route,direct,resource_state,coalition=(),view=None,age=None,predicted=False,effort=None,gain_action=None,tool=None,clarify=None,direct_action='SOURCE_COPY'):\n"
        b"        if direct_action not in {'SOURCE_COPY','LOCAL_EXACT_ARITHMETIC'} or (not direct and direct_action!='SOURCE_COPY'):\n"
    )
    helper = b'''        return out
    MAX_CONTEXT_SOURCE_REFS=64
    MAX_CONTEXT_ITEMS=16
    def _context_source_receipt(self,e,coalition):
        """Bind C5's actual coalition inputs to validated source bytes."""
        refs=[];seen=set();index_by_key={};contexts=[];organs=['A_SOURCE']
        total=0;refs_truncated=False;items_truncated=False
        def add(ref):
            nonlocal total,refs_truncated
            if type(ref) is not dict:raise ValueError('ActionSelection source ref must be an object')
            key=dumps(ref)
            if key in seen:return key
            self.s.read_source(ref)
            seen.add(key);total+=1
            if len(refs)<self.MAX_CONTEXT_SOURCE_REFS:
                index_by_key[key]=len(refs);refs.append(dict(ref))
            else:refs_truncated=True
            return key
        add(e['source_ref'])
        for index,item in enumerate(coalition):
            if type(item) is not dict:raise ValueError('ActionSelection coalition item must be an object')
            item_id=item.get('item_id');kind=item.get('source_kind')
            if not isinstance(item_id,str) or not isinstance(kind,str):
                raise ValueError('ActionSelection coalition item identity missing')
            if kind not in organs:organs.append(kind)
            item_refs=item.get('source_refs',[])
            if item_refs is None:item_refs=[]
            if not isinstance(item_refs,list):raise ValueError('ActionSelection item source_refs must be a list')
            local=[];local_seen=set()
            for ref in item_refs:
                key=add(ref)
                if key not in local_seen:
                    local.append(dict(ref));local_seen.add(key)
            raw_layers=item.get('source_layers',{})
            if raw_layers is None:raw_layers={}
            if type(raw_layers) is not dict:raise ValueError('ActionSelection source_layers must be an object')
            layer_receipts={}
            for layer in ('offer_provenance','context_source_refs','enlightened_source_refs'):
                values=raw_layers.get(layer,[])
                if values is None:values=[]
                if not isinstance(values,list):raise ValueError('ActionSelection source layer must be a list')
                indices=[];layer_seen=set();layer_count=0;layer_truncated=False
                for ref in values:
                    key=add(ref)
                    if key not in local_seen:
                        raise ValueError('ActionSelection source layer is not bound to its coalition item')
                    if key in layer_seen:continue
                    layer_seen.add(key);layer_count+=1
                    position=index_by_key.get(key)
                    if position is None:layer_truncated=True
                    else:indices.append(position)
                layer_receipts[layer]={'ref_indices':indices,'count':layer_count,'truncated':layer_truncated}
            if layer_receipts['context_source_refs']['count'] and 'ADMITTED_CONTEXT' not in organs:
                organs.append('ADMITTED_CONTEXT')
            if layer_receipts['enlightened_source_refs']['count'] and 'ENLIGHTENED_SPACE' not in organs:
                organs.append('ENLIGHTENED_SPACE')
            if index<self.MAX_CONTEXT_ITEMS:
                contexts.append({'item_id':item_id,'source_kind':kind,'source_refs':local,
                                 'source_layers':layer_receipts,'source_bound':bool(local)})
            else:items_truncated=True
        return {'source_refs':refs,'source_ref_count':total,'source_refs_truncated':refs_truncated,
                'context_sources':contexts,'context_sources_truncated':items_truncated,
                'context_input_organs':organs,'context_source_validation':'STORE_READ_SOURCE_ALL_UNIQUE_REFS'}
    def select(self,e,*,route,direct,resource_state,coalition=(),view=None,age=None,predicted=False,effort=None,gain_action=None,tool=None,clarify=None,direct_action='SOURCE_COPY'):
        if direct_action not in {'SOURCE_COPY','LOCAL_EXACT_ARITHMETIC'} or (not direct and direct_action!='SOURCE_COPY'):
'''
    focal = _replace(focal, anchor, helper, "ActionGate source-context insertion")

    setup_old = (
        b"        age=age or {'tools':False};g_act=BOOT['gain_action'] if gain_action is None else BOOT['gain_action']*clip(gain_action)/ATT_BASE['action'];coalition=list(coalition);cands=self.candidates(route,direct,coalition,view,age,tool,direct_action);suppressed=[]  # WP-N5: caution lowers action coupling\n"
    )
    setup_new = (
        b"        age=age or {'tools':False};g_act=BOOT['gain_action'] if gain_action is None else BOOT['gain_action']*clip(gain_action)/ATT_BASE['action'];coalition=list(coalition);source_context=self._context_source_receipt(e,coalition);cands=self.candidates(route,direct,coalition,view,age,tool,direct_action);suppressed=[]  # WP-N5: caution lowers action coupling\n"
    )
    focal = _replace(focal, setup_old, setup_new, "ActionGate source-context consumer")

    packet_old = (
        b"        p=packet('ActionSelection','C5_ACTION_GATE',e['event_id'],e['brain_generation_id'],[e['source_ref']],selected={k:chosen[k] for k in ('action_id','action_type','score','permission_class','focal_support')},\n"
        b"                 candidates=[{k:c[k] for k in ('action_id','action_type','score','expected_utility','expected_cost','focal_support','permission_class')} for c in cands],\n"
        b"                 suppressed=[{'action_id':c['action_id'],'reason':c['suppressed']} for c in suppressed],permission_class=chosen['permission_class'],\n"
        b"                 alternates=alternates,route_prior=self.PRIOR.get(route),stage='PREDICTION' if predicted else 'COMMIT',parameter_status='BOOT_REPRODUCES_ROUTE_TABLE',learning=learning,route_hint=route,action_gain=round(g_act,6),clarify=clarify)\n"
        b"        self.s.add_packet('ActionSelection',p)\n"
        b"        return {'role':chosen['action_id'],'packet_id':p['packet_id'],'alternates':alternates,'suppressed':p['suppressed']}\n"
    )
    packet_new = (
        b"        p=packet('ActionSelection','C5_ACTION_GATE',e['event_id'],e['brain_generation_id'],source_context['source_refs'],selected={k:chosen[k] for k in ('action_id','action_type','score','permission_class','focal_support')},\n"
        b"                 candidates=[{k:c[k] for k in ('action_id','action_type','score','expected_utility','expected_cost','focal_support','permission_class')} for c in cands],\n"
        b"                 suppressed=[{'action_id':c['action_id'],'reason':c['suppressed']} for c in suppressed],permission_class=chosen['permission_class'],\n"
        b"                 alternates=alternates,route_prior=self.PRIOR.get(route),stage='PREDICTION' if predicted else 'COMMIT',parameter_status='BOOT_REPRODUCES_ROUTE_TABLE',learning=learning,route_hint=route,action_gain=round(g_act,6),clarify=clarify,\n"
        b"                 source_refs=source_context['source_refs'],source_ref_count=source_context['source_ref_count'],source_refs_truncated=source_context['source_refs_truncated'],\n"
        b"                 context_sources=source_context['context_sources'],context_sources_truncated=source_context['context_sources_truncated'],\n"
        b"                 context_input_organs=source_context['context_input_organs'],context_source_validation=source_context['context_source_validation'])\n"
        b"        self.s.add_packet('ActionSelection',p)\n"
        b"        return {'role':chosen['action_id'],'packet_id':p['packet_id'],'alternates':alternates,'suppressed':p['suppressed'],\n"
        b"                'source_refs':source_context['source_refs'],'context_input_organs':source_context['context_input_organs']}\n"
    )
    focal = _replace(focal, packet_old, packet_new, "ActionSelection source-bound packet")

    focal = _replace(
        focal,
        b"        for m in memories:\\n",
        b"""        # Preserve every source that actually fed a B1/B2 offer into C4/C5.
        for candidate in cands:
            if candidate.get('source_kind') in BODY:
                row=self.s.one("SELECT payload FROM packets WHERE id=? AND kind='OfferPacket'",
                               (candidate['payload_ref'],))
                if row is None:
                    raise ValueError('ActionSelection body offer source packet missing')
                offer=json.loads(row['payload'])
                if (offer.get('event_id') != e['event_id']
                        or offer.get('brain_generation_id') != e['brain_generation_id']
                        or offer.get('based_on_state_version') != version
                        or offer.get('role') != candidate['source_kind']):
                    raise ValueError('ActionSelection body offer source packet is stale')
                refs=list(candidate.get('source_refs') or [])
                seen={dumps(ref) for ref in refs}
                layers={}
                for field in ('provenance','context_source_refs','enlightened_source_refs'):
                    values=offer.get(field,[])
                    if values is None:values=[]
                    if not isinstance(values,list):
                        raise ValueError('ActionSelection body offer source layer must be a list')
                    local=[];local_seen=set()
                    for ref in values:
                        if type(ref) is not dict:
                            raise ValueError('ActionSelection body offer source ref must be an object')
                        self.s.read_source(ref)
                        key=dumps(ref)
                        if key not in seen:
                            refs.append(dict(ref));seen.add(key)
                        if key not in local_seen:
                            local.append(dict(ref));local_seen.add(key)
                    layers[field]=local
                for ref in refs:self.s.read_source(ref)
                candidate['source_refs']=refs
                candidate['source_layers']={
                    'offer_provenance':layers['provenance'],
                    'context_source_refs':layers['context_source_refs'],
                    'enlightened_source_refs':layers['enlightened_source_refs'],
                }
                candidate['bounds']=boundary(self.s,refs)
        for m in memories:
""",
        "FocalLoop body offer prompt provenance"
    )

    compile(focal, "v13/focal.py", "exec")
    result["v13/focal.py"] = focal
    return result
