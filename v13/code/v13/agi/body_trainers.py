"""Body-JEPA AG6 integration: opt-in real B1/B2 adapter training, not C3.

Preserves Growth's single installed trainer contract while role-specific master
pins, training workdirs and deployed evaluations prevent C3/B1/B2 cross-binding.
A missing master/compatible GGUF/runner/dependencies yields an honest NO_TRAINER
without creating a workspace. No automatic native training and no promotion.
"""
import json
import os
import re
import math
from pathlib import Path

from ..common import file_hash

KINDS = {"body_b1": "B1_DETAIL", "body_b2": "B2_GIST"}
SHA = re.compile(r"[0-9a-f]{64}\Z")


def role_for(kind):
    try:
        return KINDS[kind]
    except KeyError as exc:
        raise ValueError("Body trainer kind must be body_b1|body_b2") from exc


def readiness(runtime,kind,state):
    """Read-only, hash-bound body master preflight; Android proof stays separate."""
    role=role_for(kind)
    entry=(state.get("body_masters") or {}).get(kind) or {}
    home=Path(runtime.home)
    master=Path(entry.get("path") or home/"models"/"master"/role)
    pinned=entry.get("sha256")
    gguf=None
    try:
        gguf=Path(runtime.models.path_for(role))
    except (ValueError,KeyError,OSError):
        pass
    except Exception:
        pass
    server=Path(os.environ.get("V13_LLAMA_SERVER",str(home/"bin"/"llama-server")))
    reasons=[]
    if role=="B2_GIST" and getattr(runtime.models,"b2_control","two_body")!="two_body":
        reasons.append("B2_DISTINCT_BODY_REQUIRED")
    weight=master/"model.safetensors"
    if not weight.is_file():
        reasons.append("MASTER_WEIGHTS_MISSING")
    if not (master/"config.json").is_file():
        reasons.append("MASTER_CONFIG_MISSING")
    else:
        try:
            config=json.loads((master/"config.json").read_text())
            if (not isinstance(config,dict)
                    or type(config.get("hidden_size")) is not int
                    or type(config.get("num_hidden_layers")) is not int
                    or config["hidden_size"]<=0 or config["num_hidden_layers"]<=0):
                reasons.append("MASTER_CONFIG_INVALID")
        except (OSError,ValueError,UnicodeError):
            reasons.append("MASTER_CONFIG_INVALID")
    if type(pinned) is not str or not SHA.fullmatch(pinned):
        reasons.append("MASTER_HASH_NOT_PINNED")
    elif weight.is_file() and file_hash(weight)!=pinned:
        reasons.append("MASTER_HASH_CHANGED")
    if gguf is None or not gguf.is_file():
        reasons.append("DEPLOYED_BODY_MISSING")
    arch=None
    if weight.is_file() and gguf is not None and gguf.is_file() and (master/"config.json").is_file():
        from .trainers import arch_match
        arch=arch_match(master,gguf)
        if arch is False:
            reasons.append("MASTER_GGUF_ARCH_MISMATCH")
        elif arch is None:
            reasons.append("MASTER_GGUF_ARCH_UNVERIFIED")
    from .trainers import _torch, probes
    if not _torch("lora"):
        reasons.append("TRAINER_DEPENDENCIES_MISSING")
    if not server.is_file():
        reasons.append("DEPLOYED_EVALUATOR_MISSING")
    try:
        anchors,heldout=probes()
        if not anchors or not heldout:
            reasons.append("RETENTION_PROBES_EMPTY")
    except (OSError,ValueError,KeyError,TypeError):
        reasons.append("RETENTION_PROBES_UNAVAILABLE")
    return {
        "role":role,"kind":kind,"ready":not reasons,"reasons":reasons,
        "requirements":{
            "master":str(master),"master_sha256":pinned,"gguf":str(gguf) if gguf else None,
            "runner":str(server),"arch_match":arch,
            "native_redmi_validated":False,"learning_quality_measured":False,
            "scope":"Explicit body adapter training candidate; no automatic deployment"
        }
    }


def build(runtime,kind,state):
    """Construct an actual BodyJepaTrainer only after role-specific readiness."""
    from .weights import NullTrainer
    report=readiness(runtime,kind,state)
    info={"choice":kind,"active":kind,"readiness":report,
          "role":report["role"],"served_live":False,
          "approval":"HUMAN_REQUIRED_BY_EXISTING_AG6_GATE"}
    if not report["ready"]:
        info["active"]="none"
        info["missing"]=report["reasons"]
        return NullTrainer(),info
    from .trainers import probes, LiveNearMissEvaluator
    from ..body_jepa import BodyJepaTrainer,DEFAULTS
    from ..lora_trainer import LlamaCppEvaluator
    role=report["role"]
    settings=report["requirements"]
    anchors,heldout=probes()
    user_cfg=((state.get("body_lora_cfg") or {}).get(kind) or {})
    invalid=(not isinstance(user_cfg,dict) or any(
        key not in DEFAULTS or key in ("threads","base_gguf") for key in user_cfg
    ))
    if not invalid:
        targets_override=user_cfg.get("targets")
        if targets_override is not None:
            invalid=(not isinstance(targets_override,(list,tuple))
                     or not 1<=len(targets_override)<=32
                     or any(type(x) is not str or not re.fullmatch(r"[A-Za-z0-9_.]{1,80}",x)
                            or "__" in x for x in targets_override))
        for numeric,lo,hi in (("jepa_weight",0.,10.),("lr",0.,.01),("anchor_weight",0.,100.)):
            v=user_cfg.get(numeric)
            if v is not None and (type(v) not in (float,int) or not math.isfinite(v)
                                  or v<lo or v>hi or numeric=="lr" and v==0):
                invalid=True
    if not invalid and user_cfg.get("anchor_reference_mode","stream") not in ("cached","stream"):
        invalid=True
    if invalid:
        info.update(active="none",served_live=False,missing=["BODY_CFG_INVALID"])
        return NullTrainer(),info
    # B1 (LFM) and B2 (Qwen) have different target-module names. These
    # defaults are hypotheses until a pinned full-master training run passes.
    targets=("w1","w2","w3") if role=="B1_DETAIL" else ("q_proj","v_proj")
    cfg=dict(DEFAULTS)
    cfg.update(targets=targets,threads=int(runtime.cfg.get("threads",4)),
               base_gguf=settings["gguf"],checkpoint_resume=True,
               heldout_probe_cap=8,anchor_reference_mode="stream")
    cfg.update(user_cfg)
    work=Path(runtime.home)/"training"/"ag6"/kind
    work.mkdir(parents=True,exist_ok=True)
    def factory(adapter_path):
        inner=LlamaCppEvaluator(settings["runner"],settings["gguf"],adapter_path,
                                threads=cfg["threads"],
                                log=str(Path(runtime.home)/"logs"/f"ag6-{kind}-eval.log"))
        # Current WP-S5 drift probes are pinned to C3; do not claim they
        # measure either body. The normal AG6/AG12 gate still applies.
        return LiveNearMissEvaluator(inner,drift=None)
    trainer=BodyJepaTrainer(settings["master"],work,
                            master_sha256=settings["master_sha256"],
                            anchors=anchors,probes=heldout,cfg=cfg,evaluator=factory)
    trainer.role=role
    info.update(served_live=True,
                cfg={k:v for k,v in cfg.items() if k not in ("base_gguf",)},
                claim_limit="Real code path ready, not executed on pinned Body master/Redmi")
    return trainer,info
