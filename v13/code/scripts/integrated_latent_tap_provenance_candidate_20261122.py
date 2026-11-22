"""Bind every native LatentTapPacket to the exact installed sender model.

The tap remains read-only. This overlay adds model-file identity and rejects
consumption after a model revision/hash change; it does not enable B3 routing,
receiver injection, or learning authority.
"""
import hashlib
from pathlib import Path

BASE_PINS = {
    "v13/cognition.py": "06de0acf2c6d30d50301d5073f5569822edff813",
    "v13/contracts.py": "7b21d9c5076015716851b5d432a5730e4e17da92",
    "v13/models.py": "bd035cf8029850cce00b179edf533e53bf24358a",
    "v13/runners.py": "2346d2b2fa88afbaf2b1b9b6f57b1bb111b6ed02",
}


def _git_blob_sha1(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def _replace(raw: bytes, old: bytes, new: bytes, label: str) -> bytes:
    count = raw.count(old)
    if count != 1:
        raise ValueError("latent tap provenance anchor mismatch: " + label + " count=" + str(count))
    return raw.replace(old, new, 1)


TAP_IDENTITY = r'''        from .models import model_key
        installed_key=model_key(role,self.r.models.b2_control)
        installed=self.r.models.installed.get(installed_key)
        if not isinstance(installed,dict) or installed.get('download_complete') is not True:
            raise ValueError('Tap model is not installed in the local manifest')
        main_file=installed.get('main_file')
        files=installed.get('files')
        main=files.get(main_file) if isinstance(files,dict) else None
        sender_model_sha256=main.get('sha256') if isinstance(main,dict) else None
        if (not isinstance(sender_model_sha256,str) or len(sender_model_sha256)!=64
                or any(ch not in '0123456789abcdef' for ch in sender_model_sha256.lower())):
            raise ValueError('Tap sender model manifest hash missing or malformed')
        sender_model_revision=self.r.models.revision(role)
        if (not isinstance(sender_model_revision,str) or not sender_model_revision
                or sender_model_revision!=installed.get('exact_revision')):
            raise ValueError('Tap sender model revision differs from installed manifest')
        sender_model_path=Path(self.r.models.path_for(role))
        if (sender_model_path.is_symlink() or not sender_model_path.is_file()
                or file_hash(sender_model_path)!=sender_model_sha256):
            raise ValueError('Tap sender model file differs from installed manifest')
        tokenizer_revision=installed.get('tokenizer_revision')
        if tokenizer_revision is not None and (not isinstance(tokenizer_revision,str) or not tokenizer_revision):
            raise ValueError('Tap tokenizer revision malformed')
        text=self.s.read_source(source_ref);tap_runner=self.r.pool.get_tap(role);native=tap_runner.tap(text,self.r.cancel_event,deadline)
        if (self.r.models.revision(role)!=sender_model_revision
                or file_hash(Path(self.r.models.path_for(role)))!=sender_model_sha256):
            raise ValueError('Tap sender model changed during native observation')
'''


READ_IDENTITY = r'''        from .models import model_key
        installed=self.r.models.installed.get(model_key(p['role'],self.r.models.b2_control))
        if not isinstance(installed,dict) or installed.get('download_complete') is not True:
            raise ValueError('Tap sender model is no longer installed')
        main=installed.get('files',{}).get(installed.get('main_file'))
        expected=main.get('sha256') if isinstance(main,dict) else None
        if (installed.get('exact_revision')!=p.get('model_revision')
                or self.r.models.revision(p['role'])!=p.get('model_revision')
                or expected!=p.get('sender_model_sha256')
                or installed.get('tokenizer_revision')!=p.get('tokenizer_revision')):
            raise ValueError('Tap sender model provenance is stale')
        current_path=Path(self.r.models.path_for(p['role']))
        if (current_path.is_symlink() or not current_path.is_file()
                or file_hash(current_path)!=p.get('sender_model_sha256')):
            raise ValueError('Tap sender model file differs from stored provenance')
'''


def apply_sources(code_dir, sources):
    code_dir = Path(code_dir).resolve(strict=True)
    for relative, expected in BASE_PINS.items():
        path = code_dir / relative
        if path.is_symlink() or not path.is_file():
            raise ValueError("latent tap provenance source missing or unsafe: " + relative)
        if _git_blob_sha1(path.read_bytes()) != expected:
            raise ValueError("latent tap provenance source changed: " + relative)

    result = dict(sources)
    cognition = result.get("v13/cognition.py", (code_dir / "v13/cognition.py").read_bytes())
    if not isinstance(cognition, bytes) or b"sender_model_sha256" in cognition:
        raise ValueError("latent tap provenance already applied or Cognition unavailable")

    cognition = _replace(
        cognition,
        b"        text=self.s.read_source(source_ref);tap_runner=self.r.pool.get_tap(role);native=tap_runner.tap(text,self.r.cancel_event,deadline)\n",
        TAP_IDENTITY.encode("utf-8"),
        "Cognition.tap sender identity",
    )
    cognition = _replace(
        cognition,
        b"                 tap_id=bound_tap_id,model_revision=self.r.models.revision(role),runner_revision='b10964',\n",
        b"                 tap_id=bound_tap_id,model_revision=sender_model_revision,sender_model_sha256=sender_model_sha256,tokenizer_revision=tokenizer_revision,runner_revision='b10964',\n",
        "LatentTapPacket model identity",
    )
    cognition = _replace(
        cognition,
        b"        if not row or json.loads(row['payload'])!=p:raise ValueError('Tap packet is not the stored observation')\n",
        b"        if not row or json.loads(row['payload'])!=p:raise ValueError('Tap packet is not the stored observation')\n" + READ_IDENTITY.encode("utf-8"),
        "Cognition.read_tap current model identity",
    )
    compile(cognition, "v13/cognition.py", "exec")

    contracts = result.get("v13/contracts.py", (code_dir / "v13/contracts.py").read_bytes())
    old_schema = b'"LatentTapPacket":{"role":str,"source_ref":dict,"tap_id":str,"model_revision":str,"token_ids":list,"feature_path":str,"feature_sha256":str,"shape":list},'
    new_schema = b'"LatentTapPacket":{"role":str,"source_ref":dict,"tap_id":str,"model_revision":str,"sender_model_sha256":str,"tokenizer_revision":(str,type(None)),"token_ids":list,"feature_path":str,"feature_sha256":str,"shape":list},'
    contracts = _replace(contracts, old_schema, new_schema, "LatentTapPacket schema")
    compile(contracts, "v13/contracts.py", "exec")

    result["v13/cognition.py"] = cognition
    result["v13/contracts.py"] = contracts
    return result
