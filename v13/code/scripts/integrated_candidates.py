"""Reviewed changes integrated into the live runtime, as one ordered chain.

After the SourceHandoff cohort closed (2026-10-12), the merged approval-reader
+ native firing candidate was written into the live sources byte-exactly.
Later reviewed runtime changes to the same files are appended to `_later`.
Candidate regressions stay runnable: a candidate loader accepts live sources
only when they are the exact frozen baseline, its own complete candidate, or
this exact integrated chain. Anything else still fails shut.
"""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIRING_SNAPSHOT = 'docs/proofs/continuation-20261011/native-firing-runtime-baseline'
NAMES = ('v13/runners.py', 'v13/memory_server.py', 'v13/runtime.py', 'v13/store.py')
INTEGRATED = ('approval_reader_runtime_candidate', 'native_firing_runtime_candidate', 'native_cache_bounds', 'b2_offer')

NATIVE_CACHE_ARGS = '''def native_cache_args(cfg):
    # b10964 defaults (--cache-ram 8192 MiB host prompt cache, 32 context
    # checkpoints per slot) assume a desktop. Qwen3.5 checkpoints are ~19 MiB
    # each (docs/NATIVE_CACHE.md), so a 6 GB phone needs explicit bounds.
    from .config import DEFAULTS
    ram=cfg.get('native_cache_ram_mb',DEFAULTS['native_cache_ram_mb'])
    checkpoints=cfg.get('native_ctx_checkpoints',DEFAULTS['native_ctx_checkpoints'])
    return ['--cache-ram',str(ram),'--ctx-checkpoints',str(checkpoints)]
'''


def _replace(text, old, new):
    if text.count(old) != 1:
        raise ValueError('Integrated anchor changed: '+old[:80])
    return text.replace(old, new, 1)


def native_cache_bounds(sources):
    """2026-10-12 thread G: bound host prompt cache and context checkpoints."""
    out = dict(sources)
    t = out['v13/runners.py']
    t = _replace(t, 'def rotate_log(path,cap=3*1024*1024):', NATIVE_CACHE_ARGS+'def rotate_log(path,cap=3*1024*1024):')
    t = _replace(t, '"-ngl","0","--no-warmup","--no-webui","--log-disable"]\n',
                 '"-ngl","0","--no-warmup","--no-webui","--log-disable"]\n        cmd += native_cache_args(self.cfg)\n')
    out['v13/runners.py'] = t
    return out


B2_OFFER_PATCH = 'docs/proofs/continuation-20261013/b2-offer-candidate/cognition.patch'


def b2_offer(text):
    """2026-10-13 thread O, integrated by thread G: two cfg switches for B2 offers, both off = previous behaviour.
    b2_offer_body_state=False leaves body_state out of B2 offers; offer_quote_min_chars=N lengthens quotes within
    the same budget. Same edits as the archived, preregistered candidate patch (B2_OFFER_PATCH), except that the
    offer call passes quote_min_chars only when it is set: with the switch off the call is byte-for-byte the old one,
    so closed harnesses that wrap offer_schema(tokens) (rule_transport_ablation) keep running unchanged."""
    t = _replace(text, 'def offer_schema(tokens):\n', 'def offer_schema(tokens,quote_min_chars=0):\n')
    t = _replace(t, '    uncertainty 15 % of what is left after ~30 tokens of JSON syntax. BOOT estimate, not tuned."""\n',
                 '    uncertainty 15 % of what is left after ~30 tokens of JSON syntax. BOOT estimate, not tuned.\n'
                 '    quote_min_chars (cfg offer_quote_min_chars, 0 = off) raises the quote cap so one whole source sentence fits."""\n')
    t = _replace(t, "    pr['quotes']['maxItems']=2;pr['quotes']['items']['maxLength']=max(24,int(chars*.2))\n    return s\n",
                 "    pr['quotes']['maxItems']=2;pr['quotes']['items']['maxLength']=max(24,int(chars*.2))\n"
                 "    if quote_min_chars>pr['quotes']['items']['maxLength']:\n"
                 "        # Thread O STEP2 producer ablation: 57-char quotes cut every earlier rule sentence (~80 chars) before its last\n"
                 "        # rule (\"... Local-\"). A longer quote takes its room from the summary, so the worst case stays within budget.\n"
                 "        q=min(int(quote_min_chars),(chars-48-pr['uncertainty']['maxLength'])//2)  # never beyond the budget\n"
                 "        if q>pr['quotes']['items']['maxLength']:\n"
                 "            pr['quotes']['items']['maxLength']=q;pr['summary']['maxLength']=chars-2*q-pr['uncertainty']['maxLength']\n"
                 "    return s\n")
    t = _replace(t, "            bs=bodyview.body_state(self.r,e,role,text)\n",
                 "            # Thread O STEP2 producer ablation: body_state hijacked 41/50 B2 offers; cfg b2_offer_body_state=False leaves it out for B2.\n"
                 "            bs=None if policy=='B2_GIST' and not self.r.cfg.get('b2_offer_body_state',True) else bodyview.body_state(self.r,e,role,text)\n")
    t = _replace(t, "offer_schema(self.r.cfg['observer_tokens'])));attempt_status='FINAL'",
                 "offer_schema(self.r.cfg['observer_tokens'],**({'quote_min_chars':q} if (q:=self.r.cfg.get('offer_quote_min_chars',0)) else {}))));attempt_status='FINAL'")
    return t


def _later(sources):
    return native_cache_bounds(sources)


def _baseline(root):
    folder = root/FIRING_SNAPSHOT
    manifest = json.loads((folder/'manifest.json').read_text())
    if manifest.get('schema') != 'NATIVE_FIRING_RUNTIME_BASELINE_V1' or set(manifest['files']) != set(NAMES):
        raise ValueError('Integrated baseline manifest changed')
    original = {}
    for name, expected in manifest['files'].items():
        data = (folder/Path(name).name).read_bytes()
        if hashlib.sha256(data).hexdigest() != expected:
            raise ValueError('Integrated baseline digest changed: '+name)
        original[name] = data.decode()
    return original


def _chain(full):
    from scripts import approval_reader_runtime_candidate as reader
    from scripts import native_firing_runtime_candidate as firing
    full = dict(full)
    full.update(reader.transform({k: full[k] for k in reader.NAMES}))
    return _later(firing.transform(full))


def integrated_sources(root=ROOT):
    """Frozen baseline -> approval reader -> native firing -> later changes."""
    return _chain(_baseline(root))


def overlay(original, root=ROOT):
    """Baseline files with the integrated files replaced, if live equals that."""
    expected = integrated_sources(root)
    view = {name: expected.get(name, text) for name, text in original.items()}
    actual = {name: (root/name).read_text() for name in original}
    return view if actual == view else None


def rebase(texts, root=ROOT):
    """Apply the same integrated chain to another candidate's view.

    Files of `texts` outside the integrated set are returned unchanged; the
    remaining integrated files come from the digest-bound baseline.
    """
    full = _baseline(root)
    full.update({k: v for k, v in texts.items() if k in NAMES})
    out = _chain(full)
    out = {k: (out[k] if k in NAMES else v) for k, v in texts.items()}
    if 'v13/cognition.py' in out:  # cognition.py is bound exactly by source_handoff_candidate, not by NAMES
        out['v13/cognition.py'] = b2_offer(out['v13/cognition.py'])
    return out


def write_live(root=ROOT):
    """Write the integrated chain to the live files (used once per change)."""
    for name, text in integrated_sources(root).items():
        (root/name).write_text(text)
