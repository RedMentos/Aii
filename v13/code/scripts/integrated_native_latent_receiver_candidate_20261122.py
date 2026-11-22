"""Apply the reviewed native input-embedding receiver after the complete staged composer.

The probe is explicit, one-shot and non-authoritative. It does not enable B3
production routing, learned alignment, weight updates or model swaps.
"""
import hashlib
from pathlib import Path

BASE_PINS = {
    "v13/cognition.py": "6d7940b118f099c930ee94c5b00a117af60b759dc03d8113aa6e1350a9a5a04b",
    "v13/callosum.py": "de55ba637b9e0c0fe6ea12f74385b0f9f782735cc2f52098f5b227a52902d5fc",
    "v13/runners.py": "f6adaa47ac8cb5d8aa27e0556ea35cfa16da13155834bbe20e58375b9cc669ab",
    "v13/models.py": "290ad845add126c7ada4da864bc3d0c112d9fe814279dfbb2a32a5a2dff740b8",
    "v13/contracts.py": "25466e9f938251db981256e8cbf7313c414aeddb4d7c9b880598fe61d92765b1",
    "v13/operator.py": "b81aa415acd3c2e6fe4c63de538719872976e4cff6dc532d434918a0fac57186"
}
NATIVE_FILES = {
    "v13/native_latent_receiver.py": "2bb2cfc5baa4b02ec2989bd403dc45390a0c402325082230c5340d02038a1d15",
    "v13/native/latent_receiver/CMakeLists.txt": "265cbba812499257fe559c761ca0e9410f2049fdc4a3fe30359a148c765dc30a",
    "v13/native/latent_receiver/native_latent_receiver.cpp": "3a78fc92fd74be85e0b91859fad23f5917a633f4e233376226e1082f80aed344",
    "v13/native/latent_receiver/README.md": "568757eed361977c60e18764476c1687b1584a8ce001e7847176f92cd84eee08"
}

NATIVE_RECEIVE = r'''    def native_receive(self,sender_role,receiver_role,e,source_ref,deadline):
        """Opt-in native llama_batch.embd receiver probe; never production B3 or learning."""
        from .models import model_key
        from .common import file_hash
        from .native_latent_receiver import POSITION_MODE, probe as native_probe, register_packet_contract, validate_packet
        from .native_probe_approval import require_consumed as require_native_approval
        register_packet_contract()
        if sender_role not in {"B1_DETAIL","B2_GIST"} or receiver_role not in {"B1_DETAIL","B2_GIST","C3_LANGUAGE"} or sender_role==receiver_role:
            raise ValueError("Native receiver roles must be distinct B1/B2 -> B1/B2/C3")
        if (not isinstance(source_ref,dict) or not isinstance(e,dict)
                or not isinstance(e.get("source_ref"),dict)
                or source_ref.get("source_id")!=e["source_ref"].get("source_id")):
            raise ValueError("Native receiver source must belong to this event")
        # The receiver boundary independently enforces the already-consumed
        # local TTY arm; direct Python calls cannot bypass the operator gate.
        approved_models=require_native_approval(self.r,sender_role,receiver_role,e,source_ref)

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
        if (sender_model_sha256!=approved_models[sender_role]["sha256"]
                or tap.get("model_revision")!=approved_models[sender_role]["revision"]):
            raise ValueError("Sender model differs from consumed local approval")
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
        if (installed.get("exact_revision")!=approved_models[receiver_role]["revision"]
                or main["sha256"]!=approved_models[receiver_role]["sha256"]):
            raise ValueError("Receiver model differs from consumed local approval")
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
NATIVE_PROBE_METHOD = r'''    def native_receiver_probe(self):
        row=self.s.one("SELECT payload FROM packets WHERE kind='LatentReceiverPacket' ORDER BY rowid DESC LIMIT 1")
        if not row:return None
        try:
            from .native_latent_receiver import validate_packet
            q=validate_packet(json.loads(row['payload']))
            return {k:q.get(k) for k in ('sender_role','receiver_role','sender_model_sha256',
                'tokenizer_revision','receiver_model_revision','receiver_model_sha256','status',
                'input_rows','input_dim','position_ids','position_mode','receiver_input_dim',
                'output_dim','decode_status','row_shuffle_control_applicable',
                'row_shuffle_control_cosine','native_input_consumed','input_effect_detected')} | {
                'production_route':False,'semantic_use_proven':False,
                'training_authority':0,'native_receiver_authority':0}
        except (ValueError,TypeError,KeyError,RuntimeError):
            return {'status':'INVALID_STORED_RECEIPT'}

'''
REPORT_PROBE_OLD = """        return {'revision':REVISION,'mode':st['mode'],'proposal_agreement':round(p['same']/p['n'],3) if p['n'] else None,'directions':self.doctor(cfg),\n"""
REPORT_PROBE_NEW = """        return {'revision':REVISION,'mode':st['mode'],'proposal_agreement':round(p['same']/p['n'],3) if p['n'] else None,'directions':self.doctor(cfg),'native_receiver_probe':self.native_receiver_probe(),\n"""
REPORT_GATE_OLD = """                'gate':'G-CALLOSUM-UTILITY-002: LATENT blocked (no native L1 receiver path yet)','claim_limit':'Channel choice among exact/control/symbolic baselines; no latent exchange'}\n"""
REPORT_GATE_NEW = """                'gate':'G-CALLOSUM-UTILITY-002: LATENT blocked for production; native probe is separate-context and non-authoritative','claim_limit':'Native input effect is not trained cross-model alignment, semantic utility or production latent exchange'}\n"""
OPERATOR_HELP_OLD = '''    """:callosum [status|shadow|active|degrade|promote <direction>]"""\n'''
OPERATOR_HELP_NEW = '''    """:callosum [status|shadow|active|degrade|promote <direction>|native-probe <B1_DETAIL|B2_GIST> <B1_DETAIL|B2_GIST|C3_LANGUAGE> --last-source --confirm]"""\n'''
OPERATOR_PREFIX_NEW = r"""    c=controller(r)
    if len(args)==5 and args[0]=='native-probe' and args[3]=='--last-source' and args[4]=='--confirm':
        sender,receiver=args[1],args[2]
        if sender not in {'B1_DETAIL','B2_GIST'} or receiver not in {'B1_DETAIL','B2_GIST','C3_LANGUAGE'} or sender==receiver:
            raise ValueError('Native probe requires distinct B1/B2 sender and B1/B2/C3 receiver')
        r.require_idle()
        last=r.last_answer()
        if not last:raise ValueError('Erst eine abgeschlossene Eingabe erzeugen')
        row=r.store.one('SELECT packet FROM events WHERE id=?',(last['event_id'],))
        if not row:raise ValueError('Letztes Ereignis fehlt')
        event=json.loads(row['packet'])
        ref=event.get('source_ref')
        if not isinstance(ref,dict) or not ref.get('source_id'):raise ValueError('Letzte Eingabe hat keine gültige SourceRef')
        r.models.path_for(receiver)
        deadline=time.monotonic()+max(120,r.cfg['observer_seconds'])
        try:
            packet=r.cognition.native_receive(sender,receiver,event,ref,deadline)
        finally:
            r.pool.unload()
        return dumps({**packet,'queued':False,'completed':True,
                      'sender_role':sender,'receiver_role':receiver,
                      'requires_explicit_confirmation':True,'production_route':False,
                      'semantic_use_proven':False,'training_authority':0,'native_receiver_authority':0,
                      'notice':'Synchronous, user-initiated probe; existing model only, no weight or routing change'})
"""

OPERATOR_ERROR_OLD = """    raise ValueError(':callosum [status|shadow|active|degrade|promote B1_TO_B2|B2_TO_B1]')\n"""
OPERATOR_ERROR_NEW = """    raise ValueError(':callosum [status|shadow|active|degrade|promote B1_TO_B2|B2_TO_B1|native-probe <sender> <receiver> --last-source --confirm]')\n"""

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
    cognition=_replace(cognition,b"    def body_context(self,role,e):\n",NATIVE_RECEIVE.encode("utf-8")+b"\n    def body_context(self,role,e):\n","Cognition.native_receive")
    compile(cognition,"v13/cognition.py","exec")
    callosum=result.get("v13/callosum.py",(code_dir/"v13/callosum.py").read_bytes())
    if not isinstance(callosum,bytes) or b"def native_receiver_probe(" in callosum:
        raise ValueError("native receiver Callosum already patched or unavailable")
    callosum=_replace(callosum,b"import re\n",b"import re\nimport time\n","Callosum time import")
    callosum=_replace(callosum,b"    def report(self,cfg):\n",NATIVE_PROBE_METHOD.encode("utf-8")+b"    def report(self,cfg):\n","Callosum.native_receiver_probe")
    callosum=_replace(callosum,REPORT_PROBE_OLD.encode("utf-8"),REPORT_PROBE_NEW.encode("utf-8"),"Callosum report probe")
    callosum=_replace(callosum,REPORT_GATE_OLD.encode("utf-8"),REPORT_GATE_NEW.encode("utf-8"),"Callosum report gate")
    callosum=_replace(callosum,OPERATOR_HELP_OLD.encode("utf-8"),OPERATOR_HELP_NEW.encode("utf-8"),"Callosum operator help")
    callosum=_replace(callosum,b"    c=controller(r)\n",OPERATOR_PREFIX_NEW.encode("utf-8"),"Callosum operator prefix")
    callosum=_replace(callosum,OPERATOR_ERROR_OLD.encode("utf-8"),OPERATOR_ERROR_NEW.encode("utf-8"),"Callosum operator error help")
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
