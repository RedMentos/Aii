"""B1/B2 AG6 integration tests: exact pins, role separation, real trainer builder.

Heavy HF/PEFT training is deliberately NOT launched in CI. This checks that
the executable BodyJepaTrainer path is reachable only for explicit B1/B2
selection with the expected full model/role/evaluator contracts.
"""
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
import json

import pytest

from v13.agi import trainers, body_trainers
from v13.agi.weights import NullTrainer
from v13.common import file_hash


class Store:
    def __init__(self):
        self.values={}
    def state(self,key,default=None):
        entry=self.values.get(key)
        if entry is None:return deepcopy(default),None
        return deepcopy(entry[0]),entry[1]
    def set_state(self,key,value,expected=None):
        prior=self.values.get(key)
        if (prior[1] if prior else None)!=expected:raise ValueError("CAS conflict")
        self.values[key]=(deepcopy(value),(prior[1]+1 if prior else 1))


class Models:
    def __init__(self):
        self.calls=[]
    def path_for(self,role):
        self.calls.append(role)
        raise RuntimeError("no real GGUF installed in CI")


def runtime(tmp_path):
    return SimpleNamespace(home=tmp_path,store=Store(),models=Models(),cfg={"threads":2})


def master(tmp_path,name):
    path=tmp_path/name
    path.mkdir()
    (path/"model.safetensors").write_bytes(b"fake master; not trained")
    (path/"config.json").write_text(json.dumps({"hidden_size":4,"num_hidden_layers":2}))
    return path


@pytest.mark.parametrize("kind,role",[
    ("body_b1","B1_DETAIL"),("body_b2","B2_GIST")
])
def test_unpinned_body_master_never_creates_training_workspace(tmp_path,kind,role):
    r=runtime(tmp_path)
    ready=trainers.training_readiness(r,kind)
    assert ready["role"]==role and not ready["ready"]
    assert "MASTER_WEIGHTS_MISSING" in ready["reasons"]
    assert "MASTER_HASH_NOT_PINNED" in ready["reasons"]
    t,info=trainers.build(r,kind)
    assert isinstance(t,NullTrainer) and info["active"]=="none"
    assert r.models.calls==[role,role]
    assert not (tmp_path/"training").exists()


def test_explicit_pin_is_separate_for_three_models(tmp_path):
    r=runtime(tmp_path)
    old=master(tmp_path,"c3-old")
    b1=master(tmp_path,"detail-master")
    b2=master(tmp_path,"gist-master")
    old_sha=file_hash(old/"model.safetensors")
    st=trainer_state={"kind":"lora","master":str(old),"master_sha256":old_sha}
    r.store.set_state(trainers.KEY,st|{"revision":trainers.REVISION})
    g=SimpleNamespace(weights=SimpleNamespace(trainer=None),trainer_info=None)
    trainers.choose(g,r,"body_b1",str(b1))
    trainers.choose(g,r,"body_b2",str(b2))
    current=trainers._box(r.store).load()[0]
    assert current["kind"]=="body_b2"
    assert current["master"]==str(old)
    assert current["master_sha256"]==old_sha
    assert current["body_masters"]["body_b1"]["sha256"]==file_hash(b1/"model.safetensors")
    assert current["body_masters"]["body_b2"]["sha256"]==file_hash(b2/"model.safetensors")
    assert current["body_masters"]["body_b1"]["path"]==str(b1)
    assert isinstance(g.weights.trainer,NullTrainer)
    assert not (tmp_path/"training").exists()


def test_changed_body_master_hash_stays_blocked(tmp_path):
    r=runtime(tmp_path)
    b1=master(tmp_path,"detail")
    st={"kind":"body_b1","body_masters":{"body_b1":
         {"path":str(b1),"sha256":file_hash(b1/"model.safetensors")}}}
    r.store.set_state(trainers.KEY,st|{"revision":trainers.REVISION})
    (b1/"model.safetensors").write_bytes(b"tampered source")
    rep=trainers.training_readiness(r,"body_b1")
    assert "MASTER_HASH_CHANGED" in rep["reasons"] and not rep["ready"]
    assert isinstance(trainers.build(r,"body_b1")[0],NullTrainer)


@pytest.mark.parametrize("kind,role,targets",[
    ("body_b1","B1_DETAIL",("w1","w2","w3")),
    ("body_b2","B2_GIST",("q_proj","v_proj"))
])
def test_real_body_jepa_trainer_wired_to_correct_role_on_ready_inputs(
        monkeypatch,tmp_path,kind,role,targets):
    r=runtime(tmp_path)
    fake={"role":role,"kind":kind,"ready":True,"reasons":[],
          "requirements":{"master":str(tmp_path/"fake-master"),
                          "master_sha256":"a"*64,
                          "gguf":str(tmp_path/"fake.gguf"),
                          "runner":str(tmp_path/"llama-server")}}
    monkeypatch.setattr(body_trainers,"readiness",lambda *_:fake)
    t,info=trainers.build(r,kind)
    from v13.body_jepa import BodyJepaTrainer
    assert isinstance(t,BodyJepaTrainer)
    assert t.role==role and t.master_sha=="a"*64
    assert t.cfg["base_gguf"]==fake["requirements"]["gguf"]
    assert tuple(t.cfg["targets"])==targets
    assert callable(t.evaluator) and info["served_live"]
    assert info["approval"]=="HUMAN_REQUIRED_BY_EXISTING_AG6_GATE"
    assert "trained" not in str(info).lower()
    assert (tmp_path/"training"/"ag6"/kind).is_dir()


def test_body_specific_knobs_cannot_replace_c3_lora_knobs(monkeypatch,tmp_path):
    r=runtime(tmp_path)
    g=SimpleNamespace(weights=SimpleNamespace(trainer=None),trainer_info=None)
    monkeypatch.setattr(trainers,"install",lambda *_:{"stub":"only storage"})
    r.store.set_state(trainers.KEY,
        {"revision":trainers.REVISION,"kind":"body_b1",
         "lora_cfg":{"lr":.0001}})
    trainers.set_lora_cfg(g,r,{"jepa_weight":.25,"lr":.0002})
    state=trainers._box(r.store).load()[0]
    assert state["lora_cfg"]=={"lr":.0001}
    assert state["body_lora_cfg"]["body_b1"]=={"jepa_weight":.25,"lr":.0002}
    with pytest.raises(ValueError,match="LoRA"):
        trainers.set_lora_cfg(g,r,{"shell_command":123})
    assert state["body_lora_cfg"]["body_b1"]["jepa_weight"]==.25


def test_auto_kind_remains_c3_only_and_is_never_auto_body(tmp_path,monkeypatch):
    r=runtime(tmp_path)
    monkeypatch.setattr(trainers,"requirements",lambda *_:{"master_ok":False})
    monkeypatch.setattr(trainers,"training_readiness",
                        lambda _r,_kind:{"ready":False,"reasons":["MASTER_MISSING"]})
    t,info=trainers.build(r,"auto")
    assert isinstance(t,NullTrainer) and info["active"]=="none"
    assert info["choice"]=="auto"
