"""C3 source/learn consent and actual tiny direct/SDFT training in the stage."""
import copy
import json

import pytest

from v13.agi.weights import WeightConsolidation
from v13.runtime import Runtime
from c3_resume_disposable_cases_20261110 import TinyLora


class Spy:
    method = 'SYNTHETIC_CONSENT_TEST'
    role = 'C3_LANGUAGE'
    self_teaches = True
    cfg = {'anchor_weight':0.}
    def __init__(self):self.calls=[]
    def fit(self, items, base_generation, *args):
        self.calls.append(copy.deepcopy(items))
        return {'artifact':None,'method':self.method,'metrics':{}}


@pytest.fixture
def live(tmp_path):
    r=Runtime(tmp_path)
    r.sleep.cycle.set_policy('enabled','off')
    r.cfg['learning_mode']='SHADOW_UPDATE'
    try:yield r
    finally:r.close()


def feedback(r, permission='learn', prompt='What is Cedar color?', value='Blue'):
    event=r.store.event(r.session,prompt)
    mid=r.memory.feedback(event['event_id'],'fact',value,permission=permission)
    return event,mid


def weights(r, trainer=None):
    return WeightConsolidation(r.store,r.cfg,trainer=trainer or Spy())


def test_record_feedback_stays_retrievable_and_is_not_a_learning_candidate(live):
    r=live
    _,mid=feedback(r,'record')
    candidate=r.memory.candidate(mid,r.session)
    assert r.store.read_source(candidate['source_ref'])=='Blue'
    w=weights(r)
    assert w.candidates(False)==[] and w.sdft_candidates()==[]
    assert w.stage('USER',require_replay_pass=False,include_sdft=True)['status']=='NOTHING_TO_STAGE'
    assert w.trainer.calls==[]


def test_learn_feedback_preserves_input_source_and_canonical_sdft_spans(live):
    r=live
    event,mid=feedback(r)
    w=weights(r)
    direct=w.candidates(False)
    assert len(direct)==1 and direct[0]['memory_id']==mid
    assert direct[0]['source_dependencies']==[event['source_ref']]
    w._check_item_sources(direct[0])
    sdft=w.sdft_candidates()
    assert len(sdft)==1 and sdft[0]['target'] is None
    assert sdft[0]['source_dependencies']==[event['source_ref']]
    assert r.store.read_source(sdft[0]['source_ref'])=='Blue'
    assert sdft[0]['source_ref']['char_end']==4
    w._check_item_sources(sdft[0])


@pytest.mark.parametrize('change',['permission','key','target','input_source','decision_packet'])
def test_direct_batch_rechecks_learn_and_exact_provenance_before_fit(live,change):
    r=live
    event,mid=feedback(r)
    w=weights(r)
    staged=w.stage('USER',require_replay_pass=False)
    with r.store.tx() as db:
        if change=='permission':db.execute("UPDATE feedback SET permission='record' WHERE event_id=?",(event['event_id'],))
        elif change=='key':db.execute("UPDATE memories SET key_text='Forged question' WHERE id=?",(mid,))
        elif change=='target':db.execute("UPDATE memories SET value='Forged answer' WHERE id=?",(mid,))
        elif change=='input_source':db.execute('UPDATE sources SET deleted=1 WHERE id=?',(event['source_ref']['source_id'],))
        else:db.execute("DELETE FROM packets WHERE event_id=? AND kind='HumanDecision'",(event['event_id'],))
    out=w.train(staged['batch_id'])
    assert out['status']=='SOURCE_INVALID' and w.trainer.calls==[]


@pytest.mark.parametrize('field',['teacher_prompt','prompt','learning_permission'])
def test_self_distillation_batch_cannot_change_its_human_correction_or_prompt(live,field):
    r=live
    feedback(r)
    w=weights(r)
    staged=w.stage('USER',require_replay_pass=False,include_sdft=True)
    def alter(state):
        for item in state['batches'][staged['batch_id']]['items']:
            if item['kind']=='sdft':item[field]='forged'
    w.box.mutate(alter)
    assert w.train(staged['batch_id'])['status']=='SOURCE_INVALID'
    assert w.trainer.calls==[]


def test_real_tiny_c3_direct_and_self_teacher_route_train_without_activation(live,tmp_path):
    r=live
    feedback(r)
    cfg={'rank':2,'targets':('c_attn',),'locality_swaps':0,'anchor_weight':0.,'jepa_weight':0.,
         'max_steps':1,'min_steps':1,'target_loss':-1.,'ckpt_every':1,'threads':1,'seed':9,'max_tokens':80}
    trainer=TinyLora('/tmp/synthetic-master',tmp_path/'tiny-c3',master_sha256='a'*64,cfg=cfg)
    trainer.role='C3_LANGUAGE'
    w=weights(r,trainer)
    staged=w.stage('USER',require_replay_pass=False,include_sdft=True)
    batch=w.batch(staged['batch_id'])
    assert {i['kind'] for i in batch['items']}=={'fact','sdft'}
    trained=w.train(staged['batch_id'])
    assert trained['status']=='TRAINED' and trained['trainer']['metrics']['steps']==1
    assert trainer.saved_adapter
    assert not (r.home/'config/lora-active.json').exists()


def test_permissions_revoked_after_training_cannot_be_approved(live):
    r=live
    event,_=feedback(r)
    class Candidate(Spy):
        def fit(self,*args):
            return {'artifact':'/synthetic-consent-test-not-serving.gguf','hash':'synthetic',
                    'method':self.method,'metrics':{'kl_to_base':0.}}
    w=weights(r,Candidate())
    staged=w.stage('USER',require_replay_pass=False)
    w.train(staged['batch_id'])
    w.gate(staged['batch_id'],{'overall':1.},{'overall':1.},learned_recall=1.)
    with r.store.tx() as db:
        db.execute("UPDATE feedback SET permission='record' WHERE event_id=?",(event['event_id'],))
    with pytest.raises(ValueError,match='Quelle'):
        w.approve(staged['batch_id'])


def test_revocation_after_actual_c3_optimizer_step_prevents_publication(live,tmp_path,monkeypatch):
    import torch
    r=live
    event,_=feedback(r)
    cfg={'rank':2,'targets':('c_attn',),'locality_swaps':0,'anchor_weight':0.,'jepa_weight':0.,
         'max_steps':1,'min_steps':1,'target_loss':-1.,'ckpt_every':1,'threads':1,'seed':9,'max_tokens':80}
    trainer=TinyLora('/tmp/synthetic-master',tmp_path/'revoked-c3',master_sha256='a'*64,cfg=cfg)
    trainer.role='C3_LANGUAGE'
    w=weights(r,trainer)
    staged=w.stage('USER',require_replay_pass=False)
    step=torch.optim.AdamW.step
    called=[]
    def revoke(opt,*args,**kwargs):
        result=step(opt,*args,**kwargs)
        called.append(True)
        with r.store.tx() as db:db.execute("UPDATE feedback SET permission='record' WHERE event_id=?",(event['event_id'],))
        return result
    monkeypatch.setattr(torch.optim.AdamW,'step',revoke)
    with pytest.raises(ValueError,match='consent changed'):
        w.train(staged['batch_id'])
    assert called==[True]
    batch=w.batch(staged['batch_id'])
    assert batch['status']=='STAGED' and batch['trainer'] is None
    assert not (r.home/'config/lora-active.json').exists()
