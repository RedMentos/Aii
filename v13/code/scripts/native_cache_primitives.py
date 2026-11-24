#!/usr/bin/env python3
"""WP-N7 rest (§8.5, §8.6, G6B): native cache/attention capability manifest and selection policy.

Isolated candidate. Nothing in the frozen runtime (`v13/*.py`) imports this module; it is wired in only after the
SourceHandoff cohort releases the runtime sources. It contains no model code and runs without llama.cpp.

What it does
- `parse_server_log` reads the llama.cpp b10964 server log (``-lv 4``) and extracts what the body *natively* has:
  architecture, attention KV cache (cells, layers, MiB), recurrent state (layers, MiB), SWA, context checkpoints.
- `build_manifest` turns that log evidence plus measured experiment results (scripts/native_cache_bench.py) into a
  BodyPort-style capability manifest. Each capability carries a status and the evidence it was derived from:
  SUPPORTED_EXACT / SUPPORTED_APPROX / UNSUPPORTED / ABSENT_IN_ARCHITECTURE / UNMEASURED.
  The §8.6.1/8.6.3/8.6.5 primitives (encoder/decoder split, shared/pooled indexers, block-sparse attention) are
  declared ABSENT unless the architecture really has them: G6B forbids faking them with a generic wrapper.
- `select_mechanism` is the G6B Context-Policy choice: given a manifest and a situation it picks a native mechanism
  or the full re-prefill baseline. Exact-restore requests only accept SUPPORTED_EXACT mechanisms; full re-prefill
  from exact source is always the fallback and never removed.
- `runner_flags` proposes llama-server flags for a RAM budget (cache-ram, ctx checkpoints) from measured sizes.
  Proposal only; the runtime keeps its current flags until a user-approved integration.
"""
import json
import re

EXACT, APPROX, UNSUPPORTED, ABSENT, UNMEASURED = 'SUPPORTED_EXACT', 'SUPPORTED_APPROX', 'UNSUPPORTED', 'ABSENT_IN_ARCHITECTURE', 'UNMEASURED'
USABLE = (EXACT, APPROX)

# §8.6 primitives that need a dedicated architecture component. Keyed by capability -> component description.
ARCH_ONLY = {
    'CAN_CONTEXT_ENCODE_DECODE_SPLIT': 'separate causal encoder/decoder stacks (§8.6.1)',
    'CAN_PROJECT_GLOBAL_CONTEXT_STATE': 'decoder KV projected from encoder hidden states (§8.6.1)',
    'CAN_SHARED_ATTN_INDEX': 'KV/indexer shared across layers (§8.6.3)',
    'CAN_HIERARCHICAL_INDEX_CANDIDATES': 'sparse indexer restricted to earlier-stage candidates (§8.6.3)',
    'CAN_POOLED_INDEX_STATE': 'pooled indexer state (§8.6.3)',
    'CAN_BLOCK_SPARSE_RETRIEVAL': 'index branch + block-sparse attention (§8.6.5)',
}
# Architectures known (from llama.cpp source/model cards) to carry one of the ARCH_ONLY components. Empty on purpose:
# none of the pinned bodies has them, and a name match alone would not be evidence. Extend only with a primary source.
ARCH_COMPONENTS = {}

# Measured (runtime) capabilities and the bench experiment that decides each one.
MEASURED = {
    'CAN_PREFIX_CACHE_REUSE': 'prefix',          # same slot, growing conversation: cache_n > 0, exact continuation
    'CAN_BOUNDED_CACHE_REPLAY': 'edit_replay',   # §8.6.2: restore a checkpoint before an edit and replay a bounded window
    'CAN_HOST_PROMPT_CACHE': 'switch',           # A -> B -> A on one slot: A comes back from host RAM
    'CAN_SLOT_PERSIST_RESTORE': 'persist',       # save slot state to disk, erase, restore, continue exactly
    'CAN_KV_SHIFT_REUSE': 'shift',               # --cache-reuse: reuse KV chunks after a removed middle chunk
    'CAN_KV_QUANT_Q8': 'kvquant',                # q8_0 K/V cache vs f16: size and drift
}


def _f(x):
    return float(x) if x is not None else None


def parse_server_log(text):
    """Extract native cache facts from a llama-server -lv 4 log. Missing facts stay None (never guessed)."""
    g = lambda pat, conv=str: (lambda m: conv(m.group(1)) if m else None)(re.search(pat, text, re.M))
    kv = re.search(r'llama_kv_cache: size =\s*([\d.]+) MiB \(\s*(\d+) cells,\s*(\d+) layers', text)
    kv_swa = re.search(r'llama_kv_cache_iswa|llama_kv_cache: .*SWA', text)
    rs = re.search(r'llama_memory_recurrent: size =\s*([\d.]+) MiB \(\s*(\d+) cells,\s*(\d+) layers', text)
    ck = [{'pos_max': int(m.group(1)), 'n_tokens': int(m.group(2)), 'mib': float(m.group(3))}
          for m in re.finditer(r'created context checkpoint \d+ of \d+ \(pos_min = \d+, pos_max = (\d+), n_tokens = (\d+), size = ([\d.]+) MiB\)', text)]
    restored = len(re.findall(r'restored context checkpoint', text))
    return {
        'arch': g(r'print_info: arch\s+=\s*(\S+)'),
        'n_layer': g(r'print_info: n_layer\s+=\s*(\d+)', int),
        'n_swa': g(r'print_info: n_swa\s+=\s*(\d+)', int),
        'model_file_mib': g(r'print_info: file size\s+=\s*([\d.]+) MiB', float),
        'kv_mib': float(kv.group(1)) if kv else None, 'kv_cells': int(kv.group(2)) if kv else None,
        'kv_layers': int(kv.group(3)) if kv else None, 'kv_swa': bool(kv_swa),
        'kv_types': g(r'llama_kv_cache: size = .*K \((\w+)\)'),
        'recurrent_mib': float(rs.group(1)) if rs else None, 'recurrent_layers': int(rs.group(3)) if rs else None,
        'checkpoints_enabled': g(r'context checkpoints enabled, max = (\d+)', int),
        'checkpoint_min_spacing': g(r'context checkpoints enabled, max = \d+, min spacing = (\d+)', int),
        'prompt_cache_limit_mib': g(r'prompt cache is enabled, size limit: (\d+) MiB', int),
        'checkpoints_created': ck, 'checkpoints_restored': restored,
        'checkpoint_mib': max((c['mib'] for c in ck), default=None),
    }


def classify_exactness(cold, warm, tol_exact=1e-3, tol_close=5e-2):
    """Compare two greedy continuations: {'tokens':[ids], 'logprobs':[chosen-token logprob]}.

    EXACT: identical token ids and chosen-token logprobs within tol_exact.
    NUMERIC_CLOSE: identical token ids, logprobs within tol_close (different batch splits change float order).
    DIVERGENT: token ids differ or drift above tol_close. Thresholds are preregistered constants, not tuned."""
    if not cold or not warm or not cold.get('tokens'):
        return {'class': 'UNMEASURED', 'max_abs_dlogp': None, 'same_tokens': None}
    same = cold['tokens'] == warm['tokens']
    n = min(len(cold.get('logprobs') or []), len(warm.get('logprobs') or []))
    d = max((abs(a - b) for a, b in zip(cold['logprobs'][:n], warm['logprobs'][:n])), default=0.0)
    cls = 'EXACT' if same and d <= tol_exact else 'NUMERIC_CLOSE' if same and d <= tol_close else 'DIVERGENT'
    return {'class': cls, 'max_abs_dlogp': round(d, 6), 'same_tokens': same}


def _measured_status(exp):
    """exp: one bench experiment result with keys usable(bool), exactness{class}. Missing -> UNMEASURED."""
    if not exp or exp.get('status') == 'ERROR':
        return UNMEASURED
    if not exp.get('usable'):
        return UNSUPPORTED
    cls = (exp.get('exactness') or {}).get('class')
    return EXACT if cls == 'EXACT' else APPROX if cls == 'NUMERIC_CLOSE' else UNSUPPORTED if cls == 'DIVERGENT' else UNMEASURED


def build_manifest(role, model, log_facts, experiments):
    """BodyPort-style declaration. Every entry: status + evidence. No capability is asserted without evidence."""
    caps = {}
    comps = ARCH_COMPONENTS.get(log_facts.get('arch'), ())
    for cap, comp in ARCH_ONLY.items():
        caps[cap] = {'status': EXACT if cap in comps else ABSENT,
                     'evidence': f"arch={log_facts.get('arch')}: {'has' if cap in comps else 'no'} {comp}"}
    for cap, exp_name in MEASURED.items():
        exp = experiments.get(exp_name)
        caps[cap] = {'status': _measured_status(exp), 'evidence': {k: exp.get(k) for k in ('summary', 'exactness', 'cost') if exp and k in exp} or None,
                     'experiment': exp_name}
    rl, kl, n = log_facts.get('recurrent_layers'), log_facts.get('kv_layers'), log_facts.get('n_layer')
    hybrid = bool(rl and kl)
    # §8.6.4: compact recurrent state + *sparse* global attention. Full attention layers are not sparse.
    caps['HYBRID_COMPACT_STATE_PLUS_GLOBAL_ATTENTION'] = {
        'status': EXACT if hybrid else ABSENT,
        'evidence': {'recurrent_layers': rl, 'attention_kv_layers': kl, 'n_layer': n, 'global_attention': 'full (dense), not sparse' if kl else None}}
    caps['CAN_PARTIAL_ROLLBACK_WITHOUT_CHECKPOINT'] = {
        'status': UNSUPPORTED if log_facts.get('recurrent_mib') else UNMEASURED,
        'evidence': 'recurrent state cannot be truncated to an earlier position; rollback needs a stored checkpoint or full re-prefill'
                    if log_facts.get('recurrent_mib') else None}
    return {'schema': 'v13.native_cache_manifest.v1', 'role': role, 'model': model, 'facts': log_facts, 'capabilities': caps,
            'baseline': 'FULL_REPREFILL_FROM_EXACT_SOURCE'}


SITUATIONS = {
    # situation -> ordered mechanism preference (first usable wins); baseline is always appended.
    'continue_same_conversation': ['CAN_PREFIX_CACHE_REUSE'],
    'edit_earlier_turn': ['CAN_BOUNDED_CACHE_REPLAY', 'CAN_KV_SHIFT_REUSE'],
    'return_to_other_conversation': ['CAN_HOST_PROMPT_CACHE', 'CAN_SLOT_PERSIST_RESTORE'],
    'resume_after_restart': ['CAN_SLOT_PERSIST_RESTORE'],
    'drop_middle_chunk': ['CAN_KV_SHIFT_REUSE'],
    'shrink_kv_memory': ['CAN_KV_QUANT_Q8'],
}


def select_mechanism(manifest, situation, exact_required=True, prefer_cost=None):
    """G6B Context-Policy choice. Returns {'mechanism', 'status', 'reason', 'fallback'}.

    exact_required (Exact-Restore, numbers/code/quotes, §8.4): only SUPPORTED_EXACT qualifies.
    Otherwise SUPPORTED_APPROX is allowed too. prefer_cost (optional dict mechanism->measured ms) breaks ties by cost
    but never beats the exactness rule. Full re-prefill from the exact source stays the fallback in every case."""
    if situation not in SITUATIONS:
        raise ValueError(f'unknown situation {situation!r}')
    ok = (EXACT,) if exact_required else USABLE
    caps = manifest.get('capabilities', {})
    cands = [m for m in SITUATIONS[situation] if caps.get(m, {}).get('status') in ok]
    if prefer_cost:
        cands.sort(key=lambda m: prefer_cost.get(m, float('inf')))
    if situation == 'shrink_kv_memory' and exact_required:
        cands = []  # a quantised cache never counts as exact restore
    base = 'FULL_REPREFILL_FROM_EXACT_SOURCE'
    if not cands:
        why = {m: caps.get(m, {}).get('status', UNMEASURED) for m in SITUATIONS[situation]}
        return {'mechanism': base, 'status': 'BASELINE', 'reason': f'no qualifying native mechanism: {why}', 'fallback': base}
    m = cands[0]
    return {'mechanism': m, 'status': caps[m]['status'], 'reason': f'{situation}: first qualifying native mechanism', 'fallback': base}


def runner_flags(manifest, ram_budget_mib, min_checkpoints=2, max_checkpoints=8, checkpoint_spacing=None):
    """Proposed llama-server cache flags for one body under a per-body cache RAM budget (MiB).

    The b10964 defaults (--cache-ram 8192, 32 checkpoints) assume a desktop. On a 6 GB phone with three resident
    bodies the prompt cache and checkpoints must be bounded explicitly. Returns flags + the arithmetic behind them."""
    f = manifest.get('facts', {})
    ck = f.get('checkpoint_mib') or f.get('recurrent_mib') or 0.0
    kv = f.get('kv_mib') or 0.0
    out = {'inputs': {'ram_budget_mib': ram_budget_mib, 'checkpoint_mib': ck, 'kv_mib': kv}}
    if ck:
        n = int(max(0, min(max_checkpoints, (ram_budget_mib * 0.5) // ck)))
        n = n if n >= min_checkpoints else 0
    else:
        n = 0
    cache_ram = int(max(0, ram_budget_mib - n * ck))
    flags = ['--cache-ram', str(cache_ram), '--ctx-checkpoints', str(n)]
    if checkpoint_spacing and n:
        flags += ['--checkpoint-min-step', str(int(checkpoint_spacing))]
    out.update({'flags': flags, 'ctx_checkpoints': n, 'cache_ram_mib': cache_ram,
                'worst_case_extra_mib': round(cache_ram + n * ck, 1),
                'note': 'proposal only; runtime flags change after the frozen SourceHandoff cohort and user approval'})
    return out


if __name__ == '__main__':
    import sys
    if len(sys.argv) == 2:
        print(json.dumps(parse_server_log(open(sys.argv[1], errors='replace').read()), indent=1))
