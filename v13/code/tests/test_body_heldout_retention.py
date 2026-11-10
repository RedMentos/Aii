"""Bounded and prompt-disjoint B1/B2 retention, actual CPU tensors, no models."""
from contextlib import contextmanager
import pytest
import torch
from v13.body_jepa import heldout_retention_kl, select_heldout_prompts


class TwoModeBody(torch.nn.Module):
    """Minimal nn.Module/PEFT-like fixture exercising real module mode contracts."""
    def __init__(self, base, adapted):
        super().__init__()
        self.base=torch.tensor(base,dtype=torch.float32)
        self.adapted=torch.tensor(adapted,dtype=torch.float32)
        self.disabled=False
        self.calls=0

    @contextmanager
    def disable_adapter(self):
        before=self.disabled
        self.disabled=True
        try:
            yield
        finally:
            self.disabled=before

    def forward(self, input_ids):
        self.calls+=1
        source=self.base if self.disabled else self.adapted
        return type('Output',(),{'logits':source.unsqueeze(0)})()


def test_no_drift_and_finite_positive_drift_with_restored_adapter():
    unchanged=TwoModeBody([[2.,0.],[0.,2.]],[[2.,0.],[0.,2.]])
    values=heldout_retention_kl(torch,unchanged,[[1,2]])
    assert len(values)==1 and values[0]==pytest.approx(0.,abs=1e-6)
    assert unchanged.calls==2 and not unchanged.disabled
    changed=TwoModeBody([[3.,0.]],[[0.,3.]])
    values=heldout_retention_kl(torch,changed,[[1]])
    assert values[0]>2.0 and not changed.disabled


def test_invalid_probe_and_nonfinite_dist_are_rejected_without_adapter_left_disabled():
    changed=TwoModeBody([[1.,0.]],[[0.,1.]])
    for invalid in ([],[True],[-1],['1']):
        with pytest.raises(ValueError):
            heldout_retention_kl(torch,changed,[invalid])
        assert not changed.disabled
    invalid_model=TwoModeBody([[float('nan'),0.]],[[0.,1.]])
    with pytest.raises(ValueError,match='distribution'):
        heldout_retention_kl(torch,invalid_model,[[1]])
    assert not invalid_model.disabled
    with pytest.raises(ValueError,match='disable_adapter'):
        heldout_retention_kl(torch,object(),[[1]])


def test_prompt_disjoint_selection_and_mobile_cap():
    items=[{'prompt':'My Cat'}]
    anchors=['My Dog']
    probes=[{'prompt':' MY CAT '},{'prompt':'my DOG'}, {'prompt':'How are you?'},
            {'prompt':'how ARE you?'},{'prompt':'Different question'}]
    prompts,excluded=select_heldout_prompts(probes,items,anchors,1)
    assert prompts==['How are you?']
    assert excluded==3
    assert select_heldout_prompts(probes,items,anchors,0)==([],3)
    assert select_heldout_prompts(probes,items,anchors,2)[0]==['How are you?','Different question']


@pytest.mark.parametrize('cap',[-1,17,1.,True])
def test_invalid_cap_fails_closed(cap):
    with pytest.raises(ValueError,match='heldout_probe_cap'):
        select_heldout_prompts([],[],[],cap)


def test_invalid_probe_cannot_be_silently_skipped():
    with pytest.raises(ValueError,match='probe'):
        select_heldout_prompts([{'bad':'text'}],[],[],2)

from v13.body_jepa import BodyJepaTrainer
from v13.common import Unavailable

class FakeDeployedEvaluator:
    def __init__(self,receipt,throws=False):
        self.receipt=receipt;self.throws=throws;self.closed=False;self.seen=None
    def evaluate(self,items,probes,cancel=None,deadline=None):
        self.seen=(items,probes)
        if self.throws:raise RuntimeError('evaluation failed')
        return self.receipt
    def close(self):self.closed=True

def test_body_deployed_ag6_gate_contract_and_drift():
    proof={'base_eval':{'overall':.8},'candidate_eval':{'overall':.9},'learned_recall':.95,'kl_to_base':.02,'wp_s5_drift':{'passed':True}}
    ev=FakeDeployedEvaluator(proof)
    t=BodyJepaTrainer.__new__(BodyJepaTrainer);t.evaluator=lambda artifact:ev;t.probes=[{'prompt':'unseen'}]
    record={'artifact':'/test/adapter.gguf','metrics':{'heldout_kl_mean':.01}}
    result=t._deployed_eval(record,[{'prompt':'hello'}])
    assert ev.closed and ev.seen[1]==t.probes
    assert result['eval']['candidate_eval']['overall']==.9
    assert result['eval']['wp_s5_drift']==proof['wp_s5_drift']
    assert result['metrics']['kl_to_base']==.02
    assert result['metrics']['kl_source']=='deployed_llama_cpp_topk'
    assert result['metrics']['heldout_kl_mean']==.01

def test_body_without_evaluator_never_invents_deployed_gate():
    t=BodyJepaTrainer.__new__(BodyJepaTrainer);t.evaluator=None
    record={'artifact':'candidate','metrics':{}}
    assert t._deployed_eval(record,[]) is record
    assert 'eval' not in record

@pytest.mark.parametrize('throws',[False,True])
def test_body_deployed_eval_error_closes_resource_without_gate(throws):
    ev=FakeDeployedEvaluator({'base_eval':{}},throws)
    t=BodyJepaTrainer.__new__(BodyJepaTrainer);t.evaluator=lambda artifact:ev;t.probes=[]
    record={'artifact':'candidate','metrics':{}}
    with pytest.raises((RuntimeError,Unavailable)):t._deployed_eval(record,[])
    assert ev.closed and 'eval' not in record and 'kl_to_base' not in record['metrics']
