"""C3 LoRA resume metadata: no native weights or model download required."""
from v13.lora_trainer import _valid_lora_resume, _resume_shuffle_rng, _valid_lora_tensors


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


class _FakeGenerator:
    def manual_seed(self,seed):
        self.value=seed
        return self

    def set_state(self,state):
        self.value=state

    def get_state(self):
        return self.value


class _FakeTorch:
    Generator=_FakeGenerator

    @staticmethod
    def randperm(n,generator):
        # Stateful stand-in to verify the same draw schedule without Torch/model files.
        generator.value=generator.value*31+n
        return list(range(n))


def test_resume_rng_matches_uninterrupted_and_legacy_checkpoint():
    t=_FakeTorch()
    g=t.Generator().manual_seed(13)
    for _ in range(3):
        t.randperm(7,generator=g)
        t.randperm(5,generator=g)
    stored=g.get_state()
    for state in (stored,None):
        resumed=_resume_shuffle_rng(t,13,3,state,7,5,1.)
        assert resumed.get_state()==stored
        assert t.randperm(7,generator=resumed)==t.randperm(7,generator=g)
        assert resumed.get_state()==g.get_state()
        # Reset reference for second branch.
        g.set_state(stored)


def test_resume_rng_without_anchors_replays_only_data_draws():
    t=_FakeTorch()
    g=t.Generator().manual_seed(7)
    for _ in range(4):
        t.randperm(3,generator=g)
    resumed=_resume_shuffle_rng(t,7,4,None,3,9,0.)
    assert resumed.get_state()==g.get_state()


class _FakeBool:
    def __init__(self,value):
        self.value=value

    def all(self):
        return self.value

    def __bool__(self):
        return self.value


class _FakeTensor:
    def __init__(self,shape=(2,3),dtype='float32',finite=True):
        self.shape=shape
        self.dtype=dtype
        self.finite=finite


class _FakeTensorTorch:
    @staticmethod
    def is_tensor(value):
        return isinstance(value,_FakeTensor)

    @staticmethod
    def isfinite(value):
        return _FakeBool(value.finite)


def test_resume_rejects_incompatible_adapter_tensors():
    t=_FakeTensorTorch()
    current={'layer.lora_A.weight':_FakeTensor(),'base.weight':_FakeTensor()}
    assert _valid_lora_tensors(t,{'layer.lora_A.weight':_FakeTensor()},current)
    for bad in (
        {},
        {'layer.lora_A.weight':_FakeTensor(),'unexpected.lora_B.weight':_FakeTensor()},
        {'layer.lora_A.weight':_FakeTensor(shape=(3,2))},
        {'layer.lora_A.weight':_FakeTensor(dtype='float16')},
        {'layer.lora_A.weight':_FakeTensor(finite=False)},
        {'layer.lora_A.weight':'not a tensor'},
    ):
        assert not _valid_lora_tensors(t,bad,current)
