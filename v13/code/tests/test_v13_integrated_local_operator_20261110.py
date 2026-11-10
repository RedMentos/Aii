"""One real Runtime and one local Operator exercise three connected V13 organs.

Runs without downloads or pretrained weights: compiled procedural output,
JEF think/speak schedule, and B1/B2 AG6 fail-closed readiness. This checks the
user-facing assembly on a shared SQLite/home, not isolated module demos.
"""
import hashlib
import json
from pathlib import Path

from v13.runtime import Runtime
from v13.operator import Operator


def ask(op,text):
    result=op.run(text)
    return json.loads(result)


def test_one_operator_uses_fast_cerebellum_turnflow_and_body_trainer(tmp_path):
    runtime=Runtime(tmp_path)
    runtime.sleep.cycle.set_policy("enabled","off")
    try:
        op=Operator(runtime)
        body=ask(op,":growth trainready body_b1")
        assert body["role"]=="B1_DETAIL" and not body["ready"]
        assert "MASTER_WEIGHTS_MISSING" in body["reasons"]
        assert not (tmp_path/"training").exists()

        plan=ask(op,':fastbatch propose repeat_v13 "Output {i}: {value}"')
        assert plan["stage"]=="CANDIDATE"
        assert plan["model_calls"]==0
        active=ask(op,":fastbatch activate repeat_v13 "+plan["sha256"][:12])
        assert active["stage"]=="ACTIVE"
        out=ask(op,':fastbatch run repeat_v13 30000 "ok" --rows=10000')
        assert out["status"]=="PAUSED" and out["rows"]==10000
        resumed=ask(op,':fastbatch run repeat_v13 30000 "ok"')
        assert resumed["status"]=="DONE" and resumed["rows"]==30000
        data=Path(resumed["output_path"]).read_bytes()
        assert data.count(b"\n")==30000
        assert hashlib.sha256(data).hexdigest()==resumed["sha256"]
        assert resumed["model_calls"]==0

        f=ask(op,":turnflow status")
        assert f["mode"]=="measure"
        assert "feedback_patterns" in f
        f=ask(op,":turnflow active")
        assert f["mode"]=="active"
        # Active turnflow does not automatically train a body or grant tools.
        assert not (tmp_path/"training").exists()
        assert ask(op,":turnflow status")["mode"]=="active"

        selection=ask(op,":growth trainer body_b1")
        assert selection["active"]=="none"
        assert "MASTER_HASH_NOT_PINNED" in selection["missing"]
        assert selection["role"]=="B1_DETAIL"
        assert not (tmp_path/"training").exists()
        # A symbolic knob is entered through the actual Termux operator,
        # persisted separately from C3 and never starts body training.
        setting=ask(op,":growth trainer cfg anchor_reference_mode=stream")
        assert setting["active"]=="none"
        from v13.agi import trainers
        state=trainers._box(runtime.store).load()[0]
        assert state["body_lora_cfg"]["body_b1"]["anchor_reference_mode"]=="stream"
        assert "body_b1" in state["body_lora_cfg"]
        assert not (tmp_path/"training").exists()
    finally:
        runtime.close()
