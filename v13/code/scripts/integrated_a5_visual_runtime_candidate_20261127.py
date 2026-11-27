"""Compose the lease-bound A5 visual consumer into the normal Runtime turn.

This is a source-pinned Runtime overlay. The Android companion remains OFF until
it registers an OS-receipt-backed provider; no screen capture or permission is
created by this builder. The visual lease stays open through C3 generation.
"""
import hashlib
from pathlib import Path


A5_RUNTIME_CONSUMER = "v13/a5_visual_runtime_consumer.py"
A5_RUNTIME_CONSUMER_BLOB_SHA1 = "3049b960ddbec0ddc6fe78236f1615ab2575212e"
A5_FRAME_ADAPTER = "v13/a5_visual_frame_bridge.py"
A5_FRAME_ADAPTER_BLOB_SHA1 = "c7a5c2a46f561fbf4453a555ace569a27a1ed978"
A4_VISUAL_SALIENCE = "v13/a4_visual_salience.py"
A4_VISUAL_SALIENCE_BLOB_SHA1 = "14eabe4bddd2b8f418c3a8edd839798c1bc4183d"


def _git_blob_sha1(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def _verify_blob(code_dir: Path, relative: str, expected: str) -> None:
    path = code_dir / relative
    if path.is_symlink() or not path.is_file():
        raise ValueError("A5 Runtime input missing or unsafe: " + relative)
    if _git_blob_sha1(path.read_bytes()) != expected:
        raise ValueError("A5 Runtime input changed: " + relative)


def _replace_once(raw: bytes, anchor: bytes, replacement: bytes, label: str) -> bytes:
    if not isinstance(raw, bytes) or raw.count(anchor) != 1:
        raise ValueError("A5 Runtime insertion anchor missing or ambiguous: " + label)
    return raw.replace(anchor, replacement, 1)


def apply_sources(code_dir: Path, sources: dict) -> dict:
    code_dir = Path(code_dir).resolve(strict=True)
    _verify_blob(code_dir, A5_RUNTIME_CONSUMER, A5_RUNTIME_CONSUMER_BLOB_SHA1)
    _verify_blob(code_dir, A5_FRAME_ADAPTER, A5_FRAME_ADAPTER_BLOB_SHA1)
    _verify_blob(code_dir, A4_VISUAL_SALIENCE, A4_VISUAL_SALIENCE_BLOB_SHA1)

    runtime = sources.get("v13/runtime.py")
    if not isinstance(runtime, bytes) or b"import contextlib" not in runtime:
        raise ValueError("A5 Runtime overlay requires the pinned contextlib Runtime")

    setter = (
        b"    def set_a5_visual_provider(self, provider):\n"
        b"        \"\"\"Register the companion's one-shot OS-consented visual provider.\n\n"
        b"        Registration is not permission proof; each frame still requires a\n"
        b"        current receipt, linearizable consent guard and revocation lease.\n"
        b"        \"\"\"\n"
        b"        from .a5_visual_runtime_consumer import set_provider\n"
        b"        return set_provider(self, provider)\n\n"
    )
    runtime = _replace_once(
        runtime,
        b"    def _turn(self,e):\n",
        setter + b"    def _turn(self,e):\n",
        "Runtime provider registration",
    )
    runtime = _replace_once(
        runtime,
        b"self.turn_event=e;self.bodies.begin_turn(eid)\n",
        b"self.turn_event=e;self.bodies.begin_turn(eid);a5_visual_stack=contextlib.ExitStack();a5_visual_context=None\n",
        "per-turn visual lease stack",
    )

    visual_ingress = (
        b"            if not fixed_policy and getattr(self,'_a5_visual_provider',None) is not None:\n"
        b"                from .a5_visual_runtime_consumer import consume_for_turn\n"
        b"                a5_visual_context=consume_for_turn(self,e,text,a5_visual_stack,deadline)\n"
        b"                if a5_visual_context:\n"
        b"                    meta['a5_visual']=a5_visual_context['audit']\n"
        b"                    meta['a5_visual_source_refs']=[a5_visual_context['source_ref']]\n"
    )
    runtime = _replace_once(
        runtime,
        b"            exec_state=self.executive.begin(e,self.session,self.cfg,resource,rmode);version=exec_state['state_version']\n",
        visual_ingress + b"            exec_state=self.executive.begin(e,self.session,self.cfg,resource,rmode);version=exec_state['state_version']\n",
        "normal-turn A5 ingress",
    )

    visual_context = (
        b"                if a5_visual_context:\n"
        b"                    volatile.append(('VISUAL_PERCEPTION','\\nVisual perception (source-bound; RAW-EYE is structural, not object recognition; student hypotheses are not facts):',a5_visual_context['prompt_context']))\n"
    )
    runtime = _replace_once(
        runtime,
        b"                executive_view=self.executive.view(self.session)\n",
        visual_context + b"                executive_view=self.executive.view(self.session)\n",
        "C3 visual context layer",
    )

    close_stack = (
        b"        finally:\n"
        b"            try:a5_visual_stack.close()\n"
        b"            except Exception as exc:self.store.log('a5_visual_unavailable',eid,{'stage':'lease_close','error':type(exc).__name__})\n"
        b"            meta['native_pressure']=monitor.stop()\n"
    )
    runtime = _replace_once(
        runtime,
        b"        finally:\n            meta['native_pressure']=monitor.stop()\n",
        close_stack,
        "turn-finally lease cleanup",
    )

    required = (
        b"def set_a5_visual_provider(",
        b"consume_for_turn(self,e,text,a5_visual_stack,deadline)",
        b"VISUAL_PERCEPTION",
        b"a5_visual_stack.close()",
    )
    if any(marker not in runtime for marker in required):
        raise ValueError("A5 Runtime composition did not retain every consumer path")
    if runtime.count(b"consume_for_turn(self,e,text,a5_visual_stack,deadline)") != 1:
        raise ValueError("A5 visual provider must be polled at most once per turn")

    result = dict(sources)
    result["v13/runtime.py"] = runtime
    return result
