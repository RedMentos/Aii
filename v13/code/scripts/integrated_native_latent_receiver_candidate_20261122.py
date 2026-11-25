"""Apply the reviewed native input-embedding receiver after the complete staged composer.

The probe is explicit, one-shot and non-authoritative. It does not enable B3
production routing, learned alignment, weight updates or model swaps.
"""
import hashlib
from pathlib import Path

BASE_PINS = {
    "v13/cognition.py": "8b82b989c1d5a973e8b0b5aa9b24b610bb233e69fc9f063f1f7f9f17c94c215f",
    "v13/callosum.py": "7563a15339f86af31ed5e33418a78a718a17cb0793c585c7655fe5e619e9bc81",
    "v13/runners.py": "227661e0fdf7d03cf7b18731d3c476bfa07076de41f82310a8b8ea4039a22610",
    "v13/models.py": "290ad845add126c7ada4da864bc3d0c112d9fe814279dfbb2a32a5a2dff740b8",
    "v13/contracts.py": "25466e9f938251db981256e8cbf7313c414aeddb4d7c9b880598fe61d92765b1",
    "v13/operator.py": "b81aa415acd3c2e6fe4c63de538719872976e4cff6dc532d434918a0fac57186"
}
NATIVE_FILES = {
    "v13/native_latent_receiver.py": "d9c11bbaba05f9d436223022e39ea112164f3317a044724f2f636de43d1665f8",
    "v13/native/latent_receiver/CMakeLists.txt": "265cbba812499257fe559c761ca0e9410f2049fdc4a3fe30359a148c765dc30a",
    "v13/native/latent_receiver/native_latent_receiver.cpp": "62fd7e9e9b5315d3d10326925dde0410a941aef787a5ed50c86a8750beba827f",
    "v13/native/latent_receiver/README.md": "18da3596d6f9da5f932fe7aa7cfde2d14b40ee5a04fce18a1514f993868644f0",
    "v13/latent_adapter.py": "1113950f6382adcdda4741f53bec135fd6bca6acbc358a6b15bff9163edcaf33"
}

NATIVE_RECEIVE = r'''    def native_receive(self,sender_role,receiver_role,e,source_ref,deadline):
        """Opt-in native llama_batch.embd receiver probe; never production B3 or learning."""
        from .models import model_key
        from .common import file_hash
        from .native_latent_receiver import POSITION_MODE, probe as native_probe, register_packet_contract, validate_packet
        register_packet_contract()
        if sender_role not in {"B1_DETAIL","B2_GIST"} or receiver_role not in {"B1_DETAIL","B2_GIST","C3_LANGUAGE"} or sender_role==receiver_role:
            raise ValueError("Native receiver roles must be distinct B1/B2 -> B1/B2/C3")
        if (not isinstance(source_ref,dict) or not isinstance(e,dict)
                or not isinstance(e.get("source_ref"),dict)
                or source_ref.get("source_id")!=e["source_ref"].get("source_id")):
            raise ValueError("Native receiver source must belong to this event")

        tap=self.tap(sender_role,e,source_ref,deadline)
        if (tap.get("role")!=sender_role or tap.get("event_id")!=e.get("event_id")
                or tap.get("brain_generation_id")!=e.get("brain_generation_id")
                or tap.get("source_ref")!=source_ref):
            raise ValueError("Sender tap identity/source differs from this event")
        # The tap runner is exclusive. Reap it before loading the receiver model
        # so the probe never intentionally holds two dense model copies at once.
        self.r.pool.unload()
        data=self.read_tap(tap)
        token_ids=data.get("token_ids")
        vectors=data.get("vectors")
        metrics=tap.get("metrics")
        if (type(token_ids) is not list or not 1<=len(token_ids)<=64
                or any(type(token_id) is not int or token_id<0 for token_id in token_ids)
                or type(vectors) is not list or len(vectors)!=len(token_ids)
                or type(metrics) is not dict
                or metrics.get("whole_sequence_prefill") is not True
                or metrics.get("pooling")!="none"
                or metrics.get("prompt_tokens")!=len(token_ids)):
            raise ValueError("Sender tap lacks a verified whole-sequence position map")
        # LlamaRunner.tap sends this exact token list to a fresh /embeddings
        # prefill with pooling=none. Its positions are therefore 0..N-1; derive
        # them only after checking the persisted token/vector count and runner receipt.
        position_ids=list(range(len(token_ids)))
        sender_key=model_key(sender_role,self.r.models.b2_control)
        sender_installed=self.r.models.installed.get(sender_key)
        if (not sender_installed or sender_installed.get("download_complete") is not True
                or tap.get("model_revision")!=sender_installed.get("exact_revision")):
            raise ValueError("Sender model revision is not the installed pinned tap model")
        sender_main=sender_installed.get("files",{}).get(sender_installed.get("main_file"))
        if not isinstance(sender_main,dict):
            raise ValueError("Sender model manifest hash is missing")
        sender_model_sha256=sender_main.get("sha256")
        if (not isinstance(sender_model_sha256,str) or len(sender_model_sha256)!=64
                or any(ch not in "0123456789abcdef" for ch in sender_model_sha256)):
            raise ValueError("Sender model manifest hash is invalid")
        sender_model_path=self.r.models.path_for(sender_role)
        if sender_model_path.is_symlink():
            raise ValueError("Sender model symlink refused")
        sender_model_path=sender_model_path.resolve(strict=True)
        sender_models_root=(self.r.home/"models").resolve()
        if not sender_model_path.is_relative_to(sender_models_root) or not sender_model_path.is_file():
            raise ValueError("Sender model must be an installed file under home/models")
        if file_hash(sender_model_path)!=sender_model_sha256:
            raise ValueError("Sender model hash differs from the pinned tap model")
        key=model_key(receiver_role,self.r.models.b2_control)
        installed=self.r.models.installed.get(key)
        if not installed or installed.get("download_complete") is not True:
            raise ValueError("Receiver model is not installed: "+receiver_role)
        if self.r.models.revision(receiver_role)!=installed.get("exact_revision"):
            raise ValueError("Receiver model revision is routed/swapped; probe requires the installed pinned revision")
        model_path=self.r.models.path_for(receiver_role)
        main=installed.get("files",{}).get(installed.get("main_file"))
        if not isinstance(main,dict) or not isinstance(main.get("sha256"),str):
            raise ValueError("Receiver model manifest hash is missing")
        receipt=native_probe(
            home=self.r.home,model_path=model_path,expected_model_sha256=main["sha256"],
            sender_role=sender_role,receiver_role=receiver_role,
            sender_tap_id=tap["tap_id"],sender_model_revision=tap["model_revision"],
            sender_model_sha256=sender_model_sha256,tokenizer_revision=tap.get("tokenizer_revision"),
            receiver_model_revision=installed["exact_revision"],
            source_id=source_ref["source_id"],generation_id=e["brain_generation_id"],
            vectors=vectors,position_ids=position_ids,position_mode=POSITION_MODE,
            deadline=deadline,threads=min(2,max(1,int(self.r.cfg.get("threads",1)))),
            cancel_event=self.r.cancel_event,
        )
        p=packet("LatentReceiverPacket","B3_NATIVE_RECEIVER_PROBE",e["event_id"],e["brain_generation_id"],[source_ref],
                 source_ref=source_ref,sender_tap_packet_id=tap["packet_id"],
                 production_route=False,semantic_use_proven=False,training_authority=0,native_receiver_authority=0,
                 **receipt)
        validate_packet(p)
        self.s.add_packet("LatentReceiverPacket",p)
        self.s.log("native_latent_receiver_probe",e["event_id"],{
            "sender_role":sender_role,"receiver_role":receiver_role,"status":p["status"],
            "input_rows":p["input_rows"],"input_dim":p["input_dim"],
            "receiver_input_dim":p["receiver_input_dim"],"output_dim":p["output_dim"],
            "decode_status":p["decode_status"],"native_input_consumed":p["native_input_consumed"],
            "input_effect_detected":p["input_effect_detected"],"production_route":False,
            "semantic_use_proven":False,"training_authority":0,"native_receiver_authority":0,
        })
        return p'''
NATIVE_PREFIX_RECEIVE = r'''    def native_receive_prefix(self,sender_role,receiver_role,e,source_ref,adapter_name,deadline):
        """Consume one source-bound event-pooled adapter through LATENT_PREFIX_V1."""
        from pathlib import Path
        import math
        from .models import model_key
        from .common import file_hash
        from .latent_adapter import load_adapter, project_event
        from .native_latent_receiver import LATENT_PREFIX_MODE, probe as native_probe, validate_packet
        from .native_probe_approval import (
            KEY, SCHEMA as APPROVAL_SCHEMA, _adapter_binding, _model_binding, _runtime_nonce,
        )
        if (sender_role not in {"B1_DETAIL","B2_GIST"}
                or receiver_role not in {"B1_DETAIL","B2_GIST","C3_LANGUAGE"}
                or sender_role==receiver_role):
            raise ValueError("Latent-prefix roles must be distinct B1/B2 -> B1/B2/C3")
        if not isinstance(e,dict) or not isinstance(source_ref,dict) or source_ref!=e.get("source_ref"):
            raise ValueError("Latent-prefix source must exactly match this event")
        if (not getattr(self.r,"_native_probe_active",False) or self.r.current!="probe"
                or getattr(self.r,"_native_probe_lease_nonce",None) is None):
            raise PermissionError("Latent-prefix receiver requires its exclusive approved Runtime lease")
        approval,_=self.s.state(KEY,None)
        if (not isinstance(approval,dict) or approval.get("schema")!=APPROVAL_SCHEMA
                or approval.get("status")!="CONSUMED"
                or approval.get("runtime_nonce")!=_runtime_nonce(self.r)
                or approval.get("input_mode")!="LATENT_PREFIX_V1"
                or approval.get("adapter_name")!=adapter_name
                or approval.get("session_id")!=self.r.session
                or approval.get("event_id")!=e.get("event_id")
                or approval.get("brain_generation_id")!=e.get("brain_generation_id")
                or approval.get("source_ref")!=source_ref
                or approval.get("sender_role")!=sender_role
                or approval.get("receiver_role")!=receiver_role):
            raise PermissionError("Latent-prefix receiver lacks the consumed source-bound approval")
        models={
            sender_role:_model_binding(self.r,sender_role),
            receiver_role:_model_binding(self.r,receiver_role),
        }
        if approval.get("models")!=models:
            raise PermissionError("Latent-prefix model binding changed after approval")
        binding=_adapter_binding(self.r,adapter_name,sender_role,receiver_role,models)
        if approval.get("adapter")!=binding:
            raise PermissionError("Latent-prefix adapter changed after approval")
        adapter_path=Path(self.r.home)/"data"/"latent_adapters"/adapter_name
        adapter=load_adapter(adapter_path)
        if adapter.get("adapter_sha256")!=binding["sha256"]:
            raise ValueError("Latent-prefix adapter digest differs from approval")
        tap=self.tap(sender_role,e,source_ref,deadline)
        if (tap.get("role")!=sender_role or tap.get("event_id")!=e.get("event_id")
                or tap.get("brain_generation_id")!=e.get("brain_generation_id")
                or tap.get("source_ref")!=source_ref
                or tap.get("tap_id")!=adapter.get("sender_tap_id")
                or tap.get("model_revision")!=adapter.get("sender_model_revision")):
            raise ValueError("Sender tap identity/source/model differs from latent adapter")
        # Reap the sender runner before loading the receiver model.
        self.r.pool.unload()
        data=self.read_tap(tap)
        token_ids=data.get("token_ids")
        vectors=data.get("vectors")
        metrics=tap.get("metrics")
        if (type(token_ids) is not list or not 2<=len(token_ids)<=64
                or any(type(token_id) is not int or token_id<0 for token_id in token_ids)
                or type(vectors) is not list or len(vectors)!=len(token_ids)
                or type(metrics) is not dict
                or metrics.get("whole_sequence_prefill") is not True
                or metrics.get("pooling")!="none"
                or metrics.get("prompt_tokens")!=len(token_ids)):
            raise ValueError("Sender tap lacks a verified whole-sequence event-pooling source")
        rows=vectors[1:]  # exact same non-position-zero mean used by persisted tap fitting
        if not rows or not isinstance(rows[0],(list,tuple)) or not rows[0]:
            raise ValueError("Sender tap has no non-position-zero activation rows")
        dim=len(rows[0])
        if not 1<=dim<=8192 or any(not isinstance(row,(list,tuple)) or len(row)!=dim for row in rows):
            raise ValueError("Sender event-pooling geometry is invalid")
        pooled=[]
        for column in range(dim):
            values=[row[column] for row in rows]
            if any(type(value) not in (int,float) or not math.isfinite(float(value)) for value in values):
                raise ValueError("Sender event-pooling vector contains non-finite values")
            pooled.append(sum(float(value) for value in values)/len(values))
        sender_installed=self.r.models.installed.get(model_key(sender_role,self.r.models.b2_control))
        receiver_installed=self.r.models.installed.get(model_key(receiver_role,self.r.models.b2_control))
        if (not isinstance(sender_installed,dict) or not isinstance(receiver_installed,dict)
                or sender_installed.get("exact_revision")!=adapter.get("sender_model_revision")
                or receiver_installed.get("exact_revision")!=adapter.get("receiver_model_revision")):
            raise ValueError("Latent adapter revisions differ from installed model manifests")
        sender_path=Path(models[sender_role]["canonical_path"])
        receiver_path=Path(models[receiver_role]["canonical_path"])
        if file_hash(sender_path)!=models[sender_role]["sha256"] or file_hash(receiver_path)!=models[receiver_role]["sha256"]:
            raise ValueError("Sender or receiver model changed after latent-prefix approval")
        expected_input_tap={
            "B1_DETAIL":"b1.input-embedding.v1",
            "B2_GIST":"b2.input-embedding.v1",
            "C3_LANGUAGE":"c3.input-embedding.v1",
        }[receiver_role]
        if adapter.get("receiver_tap_id")!=expected_input_tap:
            raise ValueError("Latent adapter is not trained against the receiver input-embedding space")
        projected=project_event(
            adapter,pooled,
            sender_model_sha256=models[sender_role]["sha256"],
            receiver_model_sha256=models[receiver_role]["sha256"],
            sender_tap_id=tap["tap_id"],
            receiver_tap_id=adapter["receiver_tap_id"],
        )
        receipt=native_probe(
            home=self.r.home,model_path=receiver_path,
            expected_model_sha256=models[receiver_role]["sha256"],
            sender_role=sender_role,receiver_role=receiver_role,
            sender_tap_id=tap["tap_id"],sender_model_revision=adapter["sender_model_revision"],
            sender_model_sha256=models[sender_role]["sha256"],tokenizer_revision=None,
            receiver_model_revision=adapter["receiver_model_revision"],
            source_id=source_ref["source_id"],generation_id=e["brain_generation_id"],
            vectors=[projected],position_ids=[0],position_mode=LATENT_PREFIX_MODE,
            deadline=deadline,threads=min(2,max(1,int(self.r.cfg.get("threads",1)))),
            cancel_event=self.r.cancel_event,
        )
        p=packet("LatentReceiverPacket","B3_NATIVE_LATENT_PREFIX_PROBE",e["event_id"],e["brain_generation_id"],[source_ref],
                 source_ref=source_ref,sender_tap_packet_id=tap["packet_id"],
                 adapter_sha256=adapter["adapter_sha256"],adapter_status=adapter["status"],
                 projection_scope=adapter["projection_scope"],input_semantics="SINGLE_EVENT_PREFIX",
                 production_route=False,semantic_use_proven=False,training_authority=0,native_receiver_authority=0,
                 **receipt)
        validate_packet(p)
        self.s.add_packet("LatentReceiverPacket",p)
        self.s.log("native_latent_prefix_receiver_probe",e["event_id"],{
            "sender_role":sender_role,"receiver_role":receiver_role,"status":p["status"],
            "adapter_sha256":adapter["adapter_sha256"],"projection_scope":adapter["projection_scope"],
            "input_rows":p["input_rows"],"input_dim":p["input_dim"],
            "receiver_input_dim":p["receiver_input_dim"],"decode_status":p["decode_status"],
            "native_input_consumed":p["native_input_consumed"],"input_effect_detected":p["input_effect_detected"],
            "production_route":False,"semantic_use_proven":False,
            "training_authority":0,"native_receiver_authority":0,
        })
        return p
'''
NATIVE_PROBE_METHOD = r'''    def native_receiver_probe(self):
        row=self.s.one("SELECT payload FROM packets WHERE kind='LatentReceiverPacket' ORDER BY rowid DESC LIMIT 1")
        if not row:return None
        try:
            from .native_latent_receiver import validate_packet
            q=validate_packet(json.loads(row['payload']))
            return {k:q.get(k) for k in ('sender_role','receiver_role','sender_tap_packet_id','sender_tap_id',
                'sender_model_revision','sender_model_sha256','tokenizer_revision',
                'receiver_model_revision','receiver_model_sha256','runner_revision','llama_version',
                'status','input_rows','input_dim','input_sha256','position_ids','position_mode',
                'adapter_sha256','adapter_status','projection_scope','input_semantics',
                'receiver_input_dim','output_dim','receiver_vocab_size','decode_status',
                'receiver_next_token_id','zero_control_next_token_id','shuffle_control_next_token_id',
                'row_shuffle_control_next_token_id','repeat_next_token_id','receiver_next_token_margin',
                'logit_effect_rms','logit_cosine','next_token_effect_detected',
                'next_token_changed_vs_zero','next_token_changed_vs_shuffle',
                'next_token_changed_vs_row_shuffle','repeat_next_token_stable',
                'row_shuffle_control_applicable','row_shuffle_control_cosine',
                'native_input_consumed','input_effect_detected')} | {
                'production_route':False,'semantic_use_proven':False,
                'training_authority':0,'native_receiver_authority':0}
        except (ValueError,TypeError,KeyError,RuntimeError):
            return {'status':'INVALID_STORED_RECEIPT'}

'''
REPORT_PROBE_OLD = """        return {'revision':REVISION,'mode':st['mode'],'proposal_agreement':round(p['same']/p['n'],3) if p['n'] else None,'directions':self.doctor(cfg),\n"""
REPORT_PROBE_NEW = """        return {'revision':REVISION,'mode':st['mode'],'proposal_agreement':round(p['same']/p['n'],3) if p['n'] else None,'directions':self.doctor(cfg),'native_receiver_probe':self.native_receiver_probe(),\n"""
def _sha256(raw):
    return hashlib.sha256(raw).hexdigest()
def _replace(raw,old,new,label):
    count=raw.count(old)
    if count!=1: raise ValueError("native receiver overlay anchor mismatch: "+label+" count="+str(count))
    return raw.replace(old,new,1)
def apply_sources(code_dir,sources):
    code_dir=Path(code_dir).resolve(strict=True)
    for relative,expected in BASE_PINS.items():
        path=code_dir/relative
        if path.is_symlink() or not path.is_file() or _sha256(path.read_bytes())!=expected:
            raise ValueError("native receiver base source changed: "+relative)
    result=dict(sources)
    cognition=result.get("v13/cognition.py",(code_dir/"v13/cognition.py").read_bytes())
    if not isinstance(cognition,bytes) or b"def native_receive(" in cognition:
        raise ValueError("native receiver Cognition already patched or unavailable")
    cognition=_replace(cognition,b"    def body_context(self,role,e):\n",NATIVE_RECEIVE.encode("utf-8")+b"\n"+NATIVE_PREFIX_RECEIVE.encode("utf-8")+b"\n    def body_context(self,role,e):\n","Cognition.native_receive")
    compile(cognition,"v13/cognition.py","exec")
    callosum=result.get("v13/callosum.py",(code_dir/"v13/callosum.py").read_bytes())
    if not isinstance(callosum,bytes) or b"def native_receiver_probe(" in callosum:
        raise ValueError("native receiver Callosum already patched or unavailable")
    callosum=_replace(callosum,b"    def report(self,cfg):\n",NATIVE_PROBE_METHOD.encode("utf-8")+b"    def report(self,cfg):\n","Callosum.native_receiver_probe")
    callosum=_replace(callosum,REPORT_PROBE_OLD.encode("utf-8"),REPORT_PROBE_NEW.encode("utf-8"),"Callosum report probe")
    compile(callosum,"v13/callosum.py","exec")
    result["v13/cognition.py"]=cognition
    result["v13/callosum.py"]=callosum
    for relative,expected in NATIVE_FILES.items():
        path=code_dir/relative
        if path.is_symlink() or not path.is_file(): raise ValueError("native receiver source missing or unsafe: "+relative)
        raw=path.read_bytes()
        if _sha256(raw)!=expected: raise ValueError("native receiver source hash mismatch: "+relative)
        if relative.endswith(".py"): compile(raw,relative,"exec")
        result[relative]=raw
    return result
