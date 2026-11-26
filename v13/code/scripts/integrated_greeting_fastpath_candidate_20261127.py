"""Post-composer, source-pinned greeting/acknowledgment reflex integration."""
from __future__ import annotations

import hashlib
from pathlib import Path

SOURCE_RUNTIME_SHA256 = "b6ad48830d62db307d4d4ac6e9a62a4fbd43fb52b5493a5839be7997c1be6c50"
GREETING_MODULE_GIT_BLOB_SHA1 = "a96e613e6852df241f047705e09a2c652e86c3fa"

OLD = (
    b"            from .output_policy import match\n"
    b"            mark('policy_check');fixed_policy=match(self.store,text)\n"
    b"            mark('perception_and_state')\n"
)
NEW = (
    b"            from .output_policy import match\n"
    b"            mark('policy_check');fixed_policy=match(self.store,text)\n"
    b"            if fixed_policy is None:\n"
    b"                try:  # exact whole-text greeting/ack reflex only; questions and mixed modalities keep the multi-organ path\n"
    b"                    from .greeting_fastpath import match as greeting_match\n"
    b"                    greeting=greeting_match(text,event=e)\n"
    b"                    if greeting is not None:\n"
    b"                        answer_ref=self.store.source(greeting['reply'],'BUILTIN_GREETING_REFLEX')\n"
    b"                        fixed_policy={'kind':'FIXED_EXACT','rule_id':greeting['rule_id'],'rule_version':'builtin-v1',\n"
    b"                                      'query_ref':e['source_ref'],'answer_ref':answer_ref,'answer':greeting['reply']}\n"
    b"                        meta['greeting_fastpath']={k:greeting[k] for k in ('rule_id','language','scope','input_sha256','response_sha256')}|{'answer_ref':answer_ref,'native_models_invoked':False}\n"
    b"                        self.store.log('greeting_fastpath',eid,{'rule_id':greeting['rule_id'],'scope':greeting['scope'],'exact':True})\n"
    b"                except Exception as exc:self.store.log('greeting_fastpath_unavailable',eid,{'error':type(exc).__name__})\n"
    b"            mark('perception_and_state')\n"
)


def _git_blob_sha1(raw: bytes) -> str:
    header = b"blob " + str(len(raw)).encode("ascii") + bytes((0,))
    return hashlib.sha1(header + raw).hexdigest()


def apply_sources(code_dir: Path, result: dict) -> dict:
    code_dir = Path(code_dir).resolve(strict=True)
    module_path = code_dir / "v13/greeting_fastpath.py"
    if module_path.is_symlink() or not module_path.is_file():
        raise ValueError("Core greeting/ack module missing or unsafe")
    module_raw = module_path.read_bytes()
    if _git_blob_sha1(module_raw) != GREETING_MODULE_GIT_BLOB_SHA1:
        raise ValueError("Core greeting/ack module Git blob changed")

    runtime = result.get("v13/runtime.py")
    if not isinstance(runtime, bytes):
        raise ValueError("composed Runtime source missing before greeting/ack overlay")
    actual_sha = hashlib.sha256(runtime).hexdigest()
    if actual_sha != SOURCE_RUNTIME_SHA256:
        raise ValueError("composed Runtime source changed before greeting/ack overlay: " + actual_sha)
    if runtime.count(OLD) != 1 or NEW in runtime:
        raise ValueError("greeting/ack Runtime insertion anchor changed or is ambiguous")

    updated = dict(result)
    updated["v13/runtime.py"] = runtime.replace(OLD, NEW, 1)
    return updated
