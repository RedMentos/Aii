"""C3 LoRA resume metadata: no native weights or model download required."""
from v13.lora_trainer import _valid_lora_resume


def _checkpoint():
    return {'dataset_hash':'bound','step':2,
            'hist':[{'step':1,'ce':1.0,'anchor_kl':0.0},
                    {'step':2,'ce':0.5,'anchor_kl':0.01}],
            'lora':{'adapter.weight':object()},'opt':{'state':{},'param_groups':[]}}


def test_valid_checkpoint_metadata():
    assert _valid_lora_resume(_checkpoint(),'bound',4)
    assert not _valid_lora_resume(_checkpoint(),'other',4)


def test_reject_corrupted_resume_counters_and_histories():
    for bad in (True,-1,5,1.5,'2'):
        st=_checkpoint();st['step']=bad
        assert not _valid_lora_resume(st,'bound',4)
    for hist in ([],[{'step':2,'ce':0.2,'anchor_kl':0.0}],None):
        st=_checkpoint();st['hist']=hist
        assert not _valid_lora_resume(st,'bound',4)
    st=_checkpoint();st['hist'][1]['ce']=float('nan')
    assert not _valid_lora_resume(st,'bound',4)
    st=_checkpoint();st['lora']={}
    assert not _valid_lora_resume(st,'bound',4)
    st=_checkpoint();st['opt']=None
    assert not _valid_lora_resume(st,'bound',4)


def test_reject_foreign_or_invalid_payload():
    assert not _valid_lora_resume([], 'bound',4)
    assert not _valid_lora_resume({'dataset_hash':'bound'},'bound',4)
