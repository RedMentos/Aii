"""WP-AG0 model slots and body swap: every model is replaceable, learned state survives the swap.

Blueprint §19 (BodyPort + capability profile), gate G11 (shadow, alignment, parity, gradual
traffic shift, rollback), §24.9 (no loss of memory/skills/rules/identity), IH-H21 (bridges are
valid only for exact revisions; after a swap their authority drops to SHADOW and they recalibrate).

A slot (B1_DETAIL, B2_GIST, C3_LANGUAGE, C2_CONTROL, TEACHER, EMBEDDER, WORLD, or a new one)
holds one ACTIVE model and at most one candidate. Learned assets are registered with the
revision they were trained on. On a swap each asset is classified:
  PORTABLE   model-independent (memories, skills, rules, goals, user model, eval history): carried as is
  REFIT      small heads/calibrators on the slot's outputs: refit from stored labels before authority
  REDISTILL  revision-bound weights (LoRA/adapters, merged knowledge): retrain on the new model from
             stored datasets (AG1 teacher traces, AG6 batches, replay) — never applied to the new revision
  SHADOW     bridges/latent paths (IH-H21): authority 0, fallback SOURCE/EXACT, recalibrate
Swap lifecycle: CANDIDATE → SHADOW → PARITY_PASS|PARITY_FAIL → RAMP (share 0.1→0.5→1.0) → ACTIVE,
ROLLBACK from any stage keeps the old model. A user swap is the user's decision; V13 may only
propose one with Age right body_swap (Age 5, structural, unlocked by the user).
Runners ask route(slot, key) which revision serves this turn. No model files are touched here.
Save/export: export_bundle() writes a self-describing slot checkpoint (§21.1); import_bundle() re-merges it
only through the swap gates; manifest_fields() is the slot part of the BrainGenerationManifest (IH-H17), so
separately exportable slots still form one versioned whole.
"""
import time
from ..common import digest,dumps,atomic_write
from .base import StateBox,age_allows

KEY='AG0_MODEL_SLOTS';REVISION='ag0-slots-v1'
SLOTS=('B1_DETAIL','B2_GIST','C3_LANGUAGE','C2_CONTROL','TEACHER','EMBEDDER','WORLD')
CAPABILITIES=('CAN_NATIVE_DECODE','CAN_LAYER_TAP','CAN_LATENT_INJECT','CAN_PREFIX_CONDITION','CAN_TRAIN_ADAPTER','CAN_TRAIN_SELECTED_WEIGHTS',
              'CAN_VISION_ENCODE','CAN_AUDIO_ENCODE','CAN_STREAMING_OUTPUT','CAN_EMBED','SOURCE_CHANNEL_ONLY','EXACT_CHANNEL_SUPPORTED')
ASSET_KINDS={'memory':'PORTABLE','skill':'PORTABLE','rule':'PORTABLE','goal':'PORTABLE','user_model':'PORTABLE','eval_history':'PORTABLE',
             'readout_head':'REFIT','calibrator':'REFIT','route_head':'REFIT','embedding_index':'REFIT',
             'adapter':'REDISTILL','lora':'REDISTILL','merged_weights':'REDISTILL','output_adapter':'REDISTILL',
             'bridge':'SHADOW','latent_path':'SHADOW'}
RAMP=(.1,.5,1.)
BUNDLE_SCHEMA='V13_SLOT_BUNDLE_V1'
PARITY_DELTA=.02  # BOOT: candidate may be at most this much worse on any AG12 axis

class ModelSlots:
    def __init__(self,store,age=None,clock=time.time):
        self.s=store;self.age=age;self.clock=clock
        self.box=StateBox(store,KEY,REVISION,lambda:{'slots':{},'assets':{},'history':[]})
    @staticmethod
    def spec(model_id,revision,capabilities=(),dims=None,tokenizer=None,license_id=None,path=None):
        bad=set(capabilities)-set(CAPABILITIES)
        if bad:raise ValueError('Unbekannte Fähigkeit: '+', '.join(sorted(bad)))
        return {'model_id':str(model_id),'revision':str(revision),'capabilities':sorted(capabilities),'dims':dims,'tokenizer':tokenizer,
                'license_id':license_id,'path':path}
    @staticmethod
    def from_installed(installed_entry):
        """Adapter for ModelManager.installed[key] so existing downloads become slot specs."""
        e=installed_entry
        return ModelSlots.spec(e['model_id'],e['exact_revision'],('CAN_NATIVE_DECODE',),license_id=e.get('license_id'),path=e['files'][e['main_file']]['path'])
    def _log(self,st,kind,slot,detail):
        st['history']=(st['history']+[{'kind':kind,'slot':slot,'detail':detail,'at':self.clock()}])[-128:]
    def install(self,slot,spec):
        """First model of a slot (or a new slot type). No swap logic needed when nothing is learned yet."""
        def f(st):
            if slot in st['slots'] and st['slots'][slot]['active']:raise ValueError('Slot belegt; swap verwenden')
            st['slots'][slot]={'active':spec,'candidate':None,'stage':'ACTIVE','share':0.,'parity':None,'plan':None}
            self._log(st,'INSTALL',slot,spec['revision'])
        self.box.mutate(f)
    def register_asset(self,slot,name,kind,revision=None,dataset_ref=None):
        """Learned state tied to a slot. dataset_ref = where the training data lives, so it can be redistilled."""
        if kind not in ASSET_KINDS:raise ValueError('Asset-Art: '+', '.join(sorted(ASSET_KINDS)))
        def f(st):
            rev=revision or (st['slots'].get(slot) or {}).get('active',{}).get('revision')
            st['assets'][slot+':'+name]={'slot':slot,'name':name,'kind':kind,'revision':rev,'dataset_ref':dataset_ref,'authority':'ACTIVE'}
        self.box.mutate(f)
    def propose_swap(self,slot,spec,origin='USER'):
        if origin!='USER' and not age_allows(self.age,'body_swap',origin):raise PermissionError('Eigener Modelltausch erst mit Age-Recht body_swap')
        def f(st):
            sl=st['slots'].get(slot)
            if not sl or not sl['active']:raise ValueError('Slot leer; install verwenden')
            if sl['candidate']:raise ValueError('Tausch läuft schon')
            if spec['revision']==sl['active']['revision']:raise ValueError('Gleiche Revision')
            old=sl['active'];plan=[]
            for k,a in st['assets'].items():
                if a['slot']!=slot:continue
                action=ASSET_KINDS[a['kind']]
                if action=='REFIT' and old.get('dims') and spec.get('dims')==old.get('dims') and spec.get('tokenizer')==old.get('tokenizer'):action='REFIT_SAME_SHAPE'
                if action=='REDISTILL' and not a['dataset_ref']:action='REDISTILL_NO_DATA'
                plan.append({'asset':k,'kind':a['kind'],'action':action,'from_revision':a['revision']})
            lost=sorted(set(c for c in old['capabilities'] if c not in spec['capabilities']))
            sl.update(candidate=spec|{'origin':origin},stage='CANDIDATE',share=0.,parity=None,plan={'assets':plan,'lost_capabilities':lost})
            self._log(st,'PROPOSE',slot,spec['revision']);return sl['plan']
        return self.box.mutate(f)
    def start_shadow(self,slot):
        """Candidate runs alongside, never answers. Revision-bound bridges drop to SHADOW now (IH-H21)."""
        def f(st):
            sl=self._need(st,slot,'CANDIDATE');sl['stage']='SHADOW'
            for a in st['assets'].values():
                if a['slot']==slot and ASSET_KINDS[a['kind']]=='SHADOW':a['authority']='SHADOW'
            self._log(st,'SHADOW',slot,sl['candidate']['revision'])
        self.box.mutate(f)
    def parity(self,slot,old_eval,new_eval,skills_parity=None,provenance_ok=True):
        """G11 parity: AG12 summaries old vs new on every axis, plus skill/provenance parity."""
        axes={}
        for a in ('overall','seen','unseen'):
            o,n=old_eval.get(a),new_eval.get(a);axes[a]=None if o is None or n is None else round(n-o,4)
        ok=all(d is None or d>=-PARITY_DELTA for d in axes.values()) and any(d is not None for d in axes.values())
        ok=ok and provenance_ok and (skills_parity is None or skills_parity>=.95)
        def f(st):
            sl=self._need(st,slot,'SHADOW');sl['parity']={'axes':axes,'skills_parity':skills_parity,'provenance_ok':provenance_ok,'passed':ok}
            sl['stage']='PARITY_PASS' if ok else 'PARITY_FAIL';self._log(st,sl['stage'],slot,axes);return dict(sl)
        return self.box.mutate(f)
    def ramp(self,slot):
        """Gradual traffic shift; the last step makes the candidate ACTIVE and marks revision-bound assets for redistill."""
        def f(st):
            sl=st['slots'][slot]
            if sl['stage'] not in {'PARITY_PASS','RAMP'}:raise ValueError('Ramp erst nach PARITY_PASS')
            nxt=next((r for r in RAMP if r>sl['share']),1.);sl['share']=nxt;sl['stage']='RAMP'
            if nxt>=1.:
                new=sl['candidate'];sl['previous']=sl['active'];sl['active']={k:v for k,v in new.items() if k!='origin'};sl['candidate']=None;sl['stage']='ACTIVE';sl['share']=0.
                for p in sl['plan']['assets']:
                    a=st['assets'][p['asset']]
                    if p['action'].startswith('REDISTILL'):a['authority']='NEEDS_REDISTILL'
                    elif p['action'].startswith('REFIT'):a['authority']='NEEDS_REFIT'
                    elif p['action']=='SHADOW':a['authority']='SHADOW_RECALIBRATE'
                    else:a['revision']=new['revision']
            self._log(st,'RAMP',slot,nxt);return dict(sl)
        return self.box.mutate(f)
    def rollback(self,slot):
        def f(st):
            sl=st['slots'][slot]
            if sl['candidate']:sl['candidate']=None
            elif sl.get('previous'):sl['active'],sl['previous']=sl['previous'],None
            else:raise ValueError('Nichts zurückzurollen')
            sl['stage']='ACTIVE';sl['share']=0.;sl['parity']=None
            for a in st['assets'].values():
                if a['slot']==slot and a['revision']==sl['active']['revision']:a['authority']='ACTIVE'
            self._log(st,'ROLLBACK',slot,sl['active']['revision'])
        self.box.mutate(f)
    def mark_relearned(self,slot,name,revision):
        """After refit/redistill/recalibration on the new model: the asset regains authority for that revision."""
        def f(st):
            a=st['assets'][slot+':'+name];a['revision']=revision;a['authority']='ACTIVE'
        self.box.mutate(f)
    def route(self,slot,key):
        """Which revision serves this turn. During RAMP a stable hash of key picks the candidate for `share` of turns."""
        sl=self.box.load()[0]['slots'].get(slot)
        if not sl or not sl['active']:return None
        if sl['stage']=='RAMP' and sl['candidate'] and int(digest(str(key))[:8],16)/0xFFFFFFFF<sl['share']:return sl['candidate']['revision']
        return sl['active']['revision']
    def usable_assets(self,slot,revision):
        """Assets a runner may apply with this revision: only ACTIVE ones trained for it, plus PORTABLE ones."""
        return sorted(a['name'] for a in self.box.load()[0]['assets'].values() if a['slot']==slot and a['authority']=='ACTIVE'
                      and (ASSET_KINDS[a['kind']]=='PORTABLE' or a['revision']==revision))
    # -- save / export / re-merge (§21.1 modular checkpoints, IH-H16/H17, operator :export model/:backup) ------
    def manifest_fields(self):
        """Slot part of the BrainGenerationManifest (IH-H17): one hash binds all slots + learned assets into one whole."""
        st=self.box.load()[0];out={}
        for slot,sl in sorted(st['slots'].items()):
            out[slot+'_model_revision']=sl['active']['revision'] if sl['active'] else None
            out[slot+'_asset_revisions']={a['name']:[a['kind'],a['revision'],a['authority']] for a in st['assets'].values() if a['slot']==slot}
        out['slots_hash']=digest(dumps(out));return out
    def export_bundle(self,slot,destination=None,home=None):
        """Self-describing slot checkpoint (§21.1 'Checkpoints sind modular'). Model weights stay referenced by
        path+revision; copy them with the existing ':export model'. Learned assets carry revision and dataset_ref."""
        st=self.box.load()[0];sl=st['slots'].get(slot)
        if not sl or not sl['active']:raise ValueError('Slot leer')
        body={'schema':BUNDLE_SCHEMA,'slot':slot,'model':sl['active'],'generation':self.s.generation_id,'exported':self.clock(),
              'assets':[a for a in st['assets'].values() if a['slot']==slot],'manifest_slots_hash':self.manifest_fields()['slots_hash']}
        bundle=body|{'sha256':digest(dumps(body))}
        if destination or home:
            path=destination or (home/'exports'/f'slot-{slot}-{sl["active"]["revision"][:12]}.json');atomic_write(path,dumps(bundle));bundle['path']=str(path)
        return bundle
    def import_bundle(self,bundle,origin='USER'):
        """Re-merge an exported slot into this brain: never activated directly, it becomes a swap candidate and must pass
        shadow → parity → ramp. Its portable assets are re-registered; revision-bound ones keep their old revision
        and stay unusable until relearned on whatever model ends up active."""
        body={k:v for k,v in bundle.items() if k not in ('sha256','path')}
        if bundle.get('schema')!=BUNDLE_SCHEMA or digest(dumps(body))!=bundle.get('sha256'):raise ValueError('Slot-Bundle beschädigt oder fremdes Format')
        slot=bundle['slot'];st=self.box.load()[0]
        if slot not in st['slots'] or not st['slots'][slot]['active']:
            self.install(slot,bundle['model']);plan=None
        else:plan=self.propose_swap(slot,bundle['model'],origin)
        for a in bundle['assets']:
            key=slot+':'+a['name']
            if key not in self.box.load()[0]['assets']:
                def f(st,a=a,key=key):st['assets'][key]=dict(a,authority='ACTIVE' if ASSET_KINDS[a['kind']]=='PORTABLE' else 'IMPORTED_NEEDS_CHECK')
                self.box.mutate(f)
        return {'slot':slot,'plan':plan,'installed_directly':plan is None}
    def _need(self,st,slot,stage):
        sl=st['slots'].get(slot)
        if not sl or sl['stage']!=stage:raise ValueError(f'{slot}: erwartet {stage}')
        return sl
    def report(self):
        st=self.box.load()[0]
        return {'revision':REVISION,'slots':{k:{'active':v['active'] and v['active']['model_id']+'@'+v['active']['revision'][:12],
                'stage':v['stage'],'share':v['share'],'candidate':v['candidate'] and v['candidate']['model_id']} for k,v in st['slots'].items()},
                'assets_pending':{k:a['authority'] for k,a in st['assets'].items() if a['authority']!='ACTIVE'},
                'claim_limit':'Slot/asset bookkeeping and swap gates; runners still load via ModelManager until route() is wired in'}
