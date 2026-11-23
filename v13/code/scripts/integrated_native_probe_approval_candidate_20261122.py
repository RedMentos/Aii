"""Local one-shot approval overlay for the staged native receiver probe.

This is a review-only stage overlay. It deliberately does not alter the shared
production recovery/stage/deployer pin chain.
"""
import hashlib
import json
import os
from pathlib import Path

APPROVAL_MODULE_SHA256 = "f149145fbb2a63385554a33550cd55a1dfef847df72fe38d78a328cfb6860939"

OPERATOR_PREFIX_OLD = r"""    c=controller(r)
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

OPERATOR_PREFIX_NEW = r"""    c=controller(r)
    if len(args)==5 and args[0]=='arm-probe' and args[3]=='--last-source' and args[4]=='--confirm':
        from .native_probe_approval import arm as arm_native_probe
        return dumps(arm_native_probe(r,args[1],args[2]))
    if args==['revoke-probe']:
        from .native_probe_approval import revoke as revoke_native_probe
        return dumps(revoke_native_probe(r))
    if len(args)==5 and args[0]=='native-probe' and args[3]=='--last-source' and args[4]=='--confirm':
        sender,receiver=args[1],args[2]
        if sender not in {'B1_DETAIL','B2_GIST'} or receiver not in {'B1_DETAIL','B2_GIST','C3_LANGUAGE'} or sender==receiver:
            raise ValueError('Native probe requires distinct B1/B2 sender and B1/B2/C3 receiver')
        r.require_idle()
        last=r.last_answer()
        if not last or last.get('status')!='FINAL':raise ValueError('Native probe requires a completed FINAL answer')
        row=r.store.one('SELECT packet,session_id FROM events WHERE id=?',(last['event_id'],))
        if not row or row['session_id']!=r.session:raise ValueError('Last source is not in the active session')
        event=json.loads(row['packet'])
        ref=event.get('source_ref')
        if not isinstance(ref,dict) or not ref.get('source_id'):raise ValueError('Last event has no valid SourceRef')
        from .native_probe_approval import consume as consume_native_probe
        approval=consume_native_probe(r,sender,receiver,event,ref)
        r.models.path_for(receiver)
        deadline=time.monotonic()+120.0
        try:
            packet=r.cognition.native_receive(sender,receiver,event,ref,deadline,approval_token=approval["approval_token"])
        finally:
            r.pool.unload()
        return dumps({**packet,'queued':False,'completed':True,
                      'sender_role':sender,'receiver_role':receiver,
                      'approval_id':approval['approval_id'],'local_approval_consumed':True,
                      'requires_explicit_confirmation':False,'production_route':False,
                      'semantic_use_proven':False,'training_authority':0,'native_receiver_authority':0,
                      'notice':'Synchronous probe after one-shot local TTY approval; existing models only, no weight or routing change'})
"""

OPERATOR_HELP_OLD = '''    """:callosum [status|shadow|active|degrade|promote <direction>|native-probe <B1_DETAIL|B2_GIST> <B1_DETAIL|B2_GIST|C3_LANGUAGE> --last-source --confirm]"""\n'''
OPERATOR_HELP_NEW = '''    """:callosum [status|shadow|active|degrade|promote <direction>|arm-probe <B1_DETAIL|B2_GIST> <B1_DETAIL|B2_GIST|C3_LANGUAGE> --last-source --confirm|native-probe <B1_DETAIL|B2_GIST> <B1_DETAIL|B2_GIST|C3_LANGUAGE> --last-source --confirm|revoke-probe]"""\n'''
OPERATOR_ERROR_OLD = """    raise ValueError(':callosum [status|shadow|active|degrade|promote B1_TO_B2|B2_TO_B1|native-probe <sender> <receiver> --last-source --confirm]')\n"""
OPERATOR_ERROR_NEW = """    raise ValueError(':callosum [status|shadow|active|degrade|promote B1_TO_B2|B2_TO_B1|arm-probe <sender> <receiver> --last-source --confirm|native-probe <sender> <receiver> --last-source --confirm|revoke-probe]')\n"""
HELP_OLD = ":callosum [status|shadow|active|degrade|promote <Richtung>]"
HELP_NEW = ":callosum [status|shadow|active|degrade|promote <Richtung>|arm-probe <sender> <receiver> --last-source --confirm|native-probe <sender> <receiver> --last-source --confirm|revoke-probe]"


def _replace(raw, old, new, label):
    count = raw.count(old)
    if count != 1:
        raise ValueError("native probe approval overlay anchor mismatch: " + label + " count=" + str(count))
    return raw.replace(old, new, 1)


def _safe_file(root: Path, relative: str, label: str) -> Path:
    root = Path(root).resolve(strict=True)
    rel = Path(relative)
    if rel.is_absolute() or not rel.parts or ".." in rel.parts:
        raise ValueError(label + " path is unsafe")
    current = root
    for part in rel.parts[:-1]:
        current = current / part
        if current.is_symlink():
            raise ValueError(label + " path contains a symlink")
        if not current.is_dir():
            raise ValueError(label + " parent directory is missing")
    path = current / rel.parts[-1]
    if path.is_symlink() or not path.is_file():
        raise ValueError(label + " file is missing or unsafe")
    resolved = path.resolve(strict=True)
    if not resolved.is_relative_to(root):
        raise ValueError(label + " path escaped its root")
    return path


def _atomic_write(path: Path, payload: bytes) -> None:
    temporary = path.with_name(path.name + ".native-probe.tmp")
    if temporary.exists() or temporary.is_symlink():
        raise ValueError("native probe overlay temporary path already exists")
    try:
        with temporary.open("xb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists() and not temporary.is_symlink():
            temporary.unlink()


def apply_sources(code_dir: Path, sources: dict) -> dict:
    """Compose local approval into the exact staged source map before publication."""
    code_dir = Path(code_dir).resolve(strict=True)
    result = dict(sources)
    approval_path = _safe_file(code_dir, "v13/native_probe_approval.py", "native probe approval source")
    approval = approval_path.read_bytes()
    if hashlib.sha256(approval).hexdigest() != APPROVAL_MODULE_SHA256:
        raise ValueError("native probe approval source hash mismatch")
    compile(approval, "v13/native_probe_approval.py", "exec")
    staged_approval = result.get("v13/native_probe_approval.py")
    if staged_approval is not None and staged_approval != approval:
        raise ValueError("staged native probe approval module differs from reviewed source")

    cognition = result.get("v13/cognition.py")
    callosum = result.get("v13/callosum.py")
    operator = result.get("v13/operator.py")
    if operator is None:
        operator = _safe_file(code_dir, "v13/operator.py", "staged Operator source").read_bytes()
    if not all(isinstance(raw, bytes) for raw in (cognition, callosum, operator)):
        raise ValueError("native probe approval requires the staged Cognition, Callosum and Operator sources")
    if b"approval_token" in cognition or b"arm-probe" in callosum or b"arm-probe" in operator:
        raise ValueError("native probe approval is already composed")

    cognition = _replace(
        cognition,
        b"    def native_receive(self,sender_role,receiver_role,e,source_ref,deadline):\n",
        b"    def native_receive(self,sender_role,receiver_role,e,source_ref,deadline,*,approval_token):\n",
        "Cognition native receiver approval signature",
    )
    cognition = _replace(
        cognition,
        b"        from .common import file_hash\n",
        b"        import os\n        from pathlib import Path\n",
        "Cognition native receiver identity imports",
    )
    identity_helper = (
        b"        def file_identity(path):\n"
        b"            st=os.stat(path,follow_symlinks=False)\n"
        b"            return [st.st_dev,st.st_ino,st.st_size,st.st_mtime_ns,st.st_ctime_ns]\n"
    )
    cognition = _replace(
        cognition,
        b"        register_packet_contract()\n",
        b"        register_packet_contract()\n"
        b"        from .native_probe_approval import require_consumed\n"
        b"        approval_record=require_consumed(self.r,sender_role,receiver_role,e,source_ref,approval_token)\n"
        b"        now=time.monotonic()\n"
        b"        if (isinstance(deadline,bool) or not isinstance(deadline,(int,float)) or not math.isfinite(deadline)\n"
        b"                or deadline<=now or deadline-now>120.0):\n"
        b"            raise ValueError(\"Native receiver deadline must be within 120 seconds\")\n"
        + identity_helper,
        "Cognition local approval consumer",
    )
    sender_old = (
        b"        if file_hash(sender_model_path)!=sender_model_sha256:\n"
        b"            raise ValueError(\"Sender model hash differs from the pinned tap model\")\n"
    )
    sender_new = (
        b"        sender_binding=approval_record[\"models\"][sender_role]\n"
        b"        if (str(sender_model_path)!=sender_binding[\"canonical_path\"]\n"
        b"                or sender_model_sha256!=sender_binding[\"sha256\"]\n"
        b"                or file_identity(sender_model_path)!=sender_binding[\"file_identity\"]):\n"
        b"            raise ValueError(\"Sender model path/identity differs from the locally approved tap model\")\n"
    )
    cognition = _replace(cognition, sender_old, sender_new, "Cognition sender approval binding")
    receiver_old = (
        b"        model_path=self.r.models.path_for(receiver_role)\n"
        b"        main=installed.get(\"files\",{}).get(installed.get(\"main_file\"))\n"
        b"        if not isinstance(main,dict) or not isinstance(main.get(\"sha256\"),str):\n"
        b"            raise ValueError(\"Receiver model manifest hash is missing\")\n"
    )
    receiver_new = (
        b"        receiver_binding=approval_record[\"models\"][receiver_role]\n"
        b"        model_path=Path(self.r.models.path_for(receiver_role))\n"
        b"        if model_path.is_symlink():\n"
        b"            raise ValueError(\"Receiver model symlink refused\")\n"
        b"        model_path=model_path.resolve(strict=True)\n"
        b"        receiver_models_root=(Path(self.r.home)/\"models\").resolve(strict=True)\n"
        b"        if not model_path.is_relative_to(receiver_models_root) or not model_path.is_file():\n"
        b"            raise ValueError(\"Receiver model must be an installed file under home/models\")\n"
        b"        if (str(model_path)!=receiver_binding[\"canonical_path\"]\n"
        b"                or file_identity(model_path)!=receiver_binding[\"file_identity\"]):\n"
        b"            raise ValueError(\"Receiver model path/identity differs from local approval\")\n"
        b"        main=installed.get(\"files\",{}).get(installed.get(\"main_file\"))\n"
        b"        if not isinstance(main,dict) or not isinstance(main.get(\"sha256\"),str):\n"
        b"            raise ValueError(\"Receiver model manifest hash is missing\")\n"
        b"        if (main[\"sha256\"]!=receiver_binding[\"sha256\"]\n"
        b"                or installed[\"exact_revision\"]!=receiver_binding[\"revision\"]):\n"
        b"            raise ValueError(\"Receiver model manifest differs from local approval\")\n"
    )
    cognition = _replace(cognition, receiver_old, receiver_new, "Cognition receiver approval binding")
    compile(cognition, "v13/cognition.py", "exec")

    callosum = _replace(callosum, OPERATOR_PREFIX_OLD.encode("utf-8"),
                        OPERATOR_PREFIX_NEW.encode("utf-8"), "Callosum local approval consumer")
    callosum = _replace(callosum, OPERATOR_HELP_OLD.encode("utf-8"),
                        OPERATOR_HELP_NEW.encode("utf-8"), "Callosum local approval help")
    callosum = _replace(callosum, OPERATOR_ERROR_OLD.encode("utf-8"),
                        OPERATOR_ERROR_NEW.encode("utf-8"), "Callosum local approval error")
    compile(callosum, "v13/callosum.py", "exec")

    operator = _replace(operator, HELP_OLD.encode("utf-8"), HELP_NEW.encode("utf-8"),
                        "Operator local approval help")
    compile(operator, "v13/operator.py", "exec")

    result["v13/cognition.py"] = cognition
    result["v13/callosum.py"] = callosum
    result["v13/operator.py"] = operator
    result["v13/native_probe_approval.py"] = approval
    return result


def apply_staged(code_dir: Path, staging_dir: Path) -> dict:
    code_dir = Path(code_dir).resolve(strict=True)
    if Path(staging_dir).is_symlink():
        raise ValueError("native probe approval stage cannot be a symlink")
    staging_dir = Path(staging_dir).resolve(strict=True)
    if (staging_dir == code_dir or staging_dir in code_dir.parents
            or code_dir in staging_dir.parents):
        raise ValueError("native probe approval staging directory must be separate from source tree")

    # Validate the stage identity and every pre-overlay byte before touching it.
    manifest_path = _safe_file(staging_dir, "INTEGRATION_STAGE.json", "staged Runtime manifest")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("status") != "SHADOW_REVIEW_ONLY":
        raise ValueError("native probe approval overlay only accepts a review-only staged Runtime")
    if Path(manifest.get("source", "")).resolve() != code_dir:
        raise ValueError("native probe approval source tree differs from staged manifest")
    file_hashes = manifest.get("files_sha256")
    if not isinstance(file_hashes, dict) or not file_hashes:
        raise ValueError("staged Runtime integrity manifest is missing")
    for relative, expected in sorted(file_hashes.items()):
        if not isinstance(relative, str) or not isinstance(expected, str) or len(expected) != 64:
            raise ValueError("staged Runtime integrity manifest is malformed")
        path = _safe_file(staging_dir, relative, "staged Runtime file")
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != expected:
            raise ValueError("staged Runtime integrity mismatch: " + relative)
    for path in staging_dir.rglob("*"):
        if path.is_symlink():
            raise ValueError("staged Runtime contains a symlink")

    callosum_path = _safe_file(staging_dir, "v13/callosum.py", "staged Callosum")
    operator_path = _safe_file(staging_dir, "v13/operator.py", "staged Operator")
    staged_approval = _safe_file(staging_dir, "v13/native_probe_approval.py", "staged approval module")
    approval_path = _safe_file(code_dir, "v13/native_probe_approval.py", "native probe approval source")
    approval = approval_path.read_bytes()
    if staged_approval.read_bytes() != approval:
        raise ValueError("staged approval module differs from the reviewed source")
    compile(approval, "v13/native_probe_approval.py", "exec")

    callosum = callosum_path.read_bytes()
    if b"arm-probe" in callosum or b"local_approval_consumed" in callosum:
        raise ValueError("native probe approval overlay is already applied")
    callosum = _replace(callosum, OPERATOR_PREFIX_OLD.encode("utf-8"),
                        OPERATOR_PREFIX_NEW.encode("utf-8"), "Callosum local approval consumer")
    callosum = _replace(callosum, OPERATOR_HELP_OLD.encode("utf-8"),
                        OPERATOR_HELP_NEW.encode("utf-8"), "Callosum help")
    callosum = _replace(callosum, OPERATOR_ERROR_OLD.encode("utf-8"),
                        OPERATOR_ERROR_NEW.encode("utf-8"), "Callosum error help")
    compile(callosum, "v13/callosum.py", "exec")

    operator = operator_path.read_bytes()
    if b"arm-probe" in operator:
        raise ValueError("Operator help overlay is already applied")
    operator = _replace(operator, HELP_OLD.encode("utf-8"), HELP_NEW.encode("utf-8"),
                        "local operator help")
    compile(operator, "v13/operator.py", "exec")

    changed = ["v13/callosum.py", "v13/operator.py", "v13/native_probe_approval.py"]
    manifest["native_probe_approval_overlay"] = {
        "status": "SHADOW_REVIEW_ONLY",
        "source": "scripts/integrated_native_probe_approval_candidate_20261122.py",
        "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "replaced_files": changed,
        "local_arm_command": ":callosum arm-probe <sender> <receiver> --last-source --confirm",
        "remote_consumer_command": ":callosum native-probe <sender> <receiver> --last-source --confirm",
        "ttl_seconds": 120,
        "native_probe_deadline_seconds": 120,
        "runtime_instance_scoped": True,
        "production_route": False,
        "training_authority": 0,
        "native_receiver_authority": 0,
    }
    manifest["replaced_files"] = sorted(set(manifest.get("replaced_files", [])) | set(changed))
    _atomic_write(callosum_path, callosum)
    _atomic_write(operator_path, operator)
    updated_hashes = {}
    for path in sorted(staging_dir.rglob("*")):
        if path.is_symlink():
            raise ValueError("staged Runtime contains a symlink")
        if path.is_file() and path != manifest_path:
            updated_hashes[str(path.relative_to(staging_dir))] = hashlib.sha256(path.read_bytes()).hexdigest()
    manifest["files_sha256"] = updated_hashes
    _atomic_write(manifest_path, (json.dumps(manifest, indent=2) + "\n").encode("utf-8"))
    return manifest
