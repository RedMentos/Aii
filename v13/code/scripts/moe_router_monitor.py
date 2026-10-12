#!/usr/bin/env python3
"""WP-N11 isolated candidate: MoE router-stability gate and shared pre-router monitor.

Canon: B3-H6 (router-stability gate for sparse MoE bodies), §16.2.1 / §24.19
(shared pre-router interference monitor / forgetting), §91 (MoE learning
hardening: update phase order, monitor fields, no "hit expert = update" rule).

NumPy only, so the same code can run on the phone. It reads router captures
(logits, router inputs, residual stream) produced by a body runner; it never
loads or changes model weights itself and grants no runtime rights. Not wired
into the frozen runtime (SourceHandoff cohort); integration is a later step.

Thresholds are never universal constants (B3-H6): `calibrate` derives them from
receiver-native baseline variation on the real body/runner/dataset; without a
calibration the gate reports UNCALIBRATED and never PASS.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass, field

import numpy as np

SCHEMA = 'v13-moe-router-capture-v1'
EPS = 1e-12

# B3-H6 knob name -> metric key in the aggregated comparison.
GATE_KNOBS = {
    'B3.max_router_kl': 'router_kl',
    'B3.max_expert_flip_rate': 'topk_flip_rate',
    'B3.max_router_input_shift': 'router_input_norm_shift',
    'B3.max_residual_norm_shift': 'residual_norm_shift',
}
# Reported next to the gate (B3-H6 "minimum metrics"), not separately thresholded
# by the canon knob list; calibrated the same way so they can be audited.
EXTRA_METRICS = ('expert_hist_shift', 'shared_drift', 'router_input_drift')


# ---------------------------------------------------------------- captures

@dataclass
class LayerCapture:
    """One MoE layer for T tokens: router logits [T,E], router input [T,D],
    residual stream entering the block [T,D] (shared pre-router state)."""
    logits: np.ndarray
    router_input: np.ndarray
    residual: np.ndarray | None = None

    def __post_init__(self):
        self.logits = np.asarray(self.logits, dtype=np.float64)
        self.router_input = np.asarray(self.router_input, dtype=np.float64)
        if self.residual is not None:
            self.residual = np.asarray(self.residual, dtype=np.float64)
        if self.logits.ndim != 2 or self.router_input.ndim != 2:
            raise ValueError('logits and router_input must be [T,E] and [T,D]')
        if self.logits.shape[0] != self.router_input.shape[0]:
            raise ValueError('token count differs between logits and router_input')
        if self.residual is not None and self.residual.shape[0] != self.logits.shape[0]:
            raise ValueError('token count differs between logits and residual')


@dataclass
class Capture:
    """Router capture of one body run: layers by index, top-k of the body."""
    layers: dict
    top_k: int
    meta: dict = field(default_factory=dict)

    def __post_init__(self):
        if not self.layers:
            raise ValueError('capture without layers')
        if self.top_k < 1:
            raise ValueError('top_k must be >= 1')
        E = {lc.logits.shape[1] for lc in self.layers.values()}
        if len(E) != 1 or self.top_k > E.pop():
            raise ValueError('inconsistent expert count or top_k > experts')

    @property
    def n_experts(self):
        return next(iter(self.layers.values())).logits.shape[1]

    def tail(self, n):
        """Last n tokens of every layer (align identical text after different prefixes)."""
        return Capture({i: LayerCapture(l.logits[-n:], l.router_input[-n:],
                                        None if l.residual is None else l.residual[-n:])
                        for i, l in self.layers.items()}, self.top_k, dict(self.meta))

    def to_npz(self, path):
        arrays = {}
        for i, l in self.layers.items():
            arrays[f'L{i}_logits'] = l.logits.astype(np.float32)
            arrays[f'L{i}_router_input'] = l.router_input.astype(np.float32)
            if l.residual is not None:
                arrays[f'L{i}_residual'] = l.residual.astype(np.float32)
        meta = dict(self.meta, schema=SCHEMA, top_k=self.top_k)
        arrays['meta'] = np.frombuffer(json.dumps(meta, sort_keys=True).encode(), dtype=np.uint8)
        np.savez_compressed(path, **arrays)

    @classmethod
    def from_npz(cls, path):
        z = np.load(path)
        meta = json.loads(bytes(z['meta']).decode())
        if meta.get('schema') != SCHEMA:
            raise ValueError('capture schema mismatch')
        idx = sorted({int(k[1:].split('_')[0]) for k in z.files if k.startswith('L')})
        layers = {i: LayerCapture(z[f'L{i}_logits'], z[f'L{i}_router_input'],
                                  z[f'L{i}_residual'] if f'L{i}_residual' in z.files else None)
                  for i in idx}
        return cls(layers, int(meta['top_k']), meta)


def load_native_tap(out_dir, row, top_k, meta=None):
    """Capture from scripts/native_moe_router_tap.cpp output (llama.cpp runner).

    Router logits = ffn_moe_logits-il, router input = ffn_norm-il; the shared
    pre-router state is attn_norm-il (the *normed* block input, so its norm
    shift is not the raw residual norm shift; cosine drift is comparable).
    """
    from pathlib import Path
    out_dir = Path(out_dir)
    rows = [json.loads(l) for l in (out_dir / 'index.jsonl').read_text().splitlines() if l.strip()]
    info = next(r for r in rows if r['row'] == row)
    n = int(info['n_tokens'])

    def read(name):
        w = info['tensors'].get(name)
        if w is None:
            return None
        a = np.fromfile(out_dir / f'{row}.{name}.f32', dtype=np.float32)
        return a.reshape(-1, w)[:n]

    layers = {}
    for name in info['tensors']:
        if name.startswith('ffn_moe_logits-'):
            il = int(name.rsplit('-', 1)[1])
            layers[il] = LayerCapture(read(name), read(f'ffn_norm-{il}'), read(f'attn_norm-{il}'))
    return Capture(layers, top_k, dict(meta or {}, runner='llama.cpp', row=row))


# ---------------------------------------------------------------- primitives

def softmax(x):
    x = np.asarray(x, dtype=np.float64)
    z = np.exp(x - x.max(axis=-1, keepdims=True))
    return z / z.sum(axis=-1, keepdims=True)


def topk_sets(logits, k):
    """[T,k] expert indices, sorted per row (order-free set comparison)."""
    idx = np.argpartition(-np.asarray(logits), k - 1, axis=-1)[:, :k]
    return np.sort(idx, axis=-1)


def kl(p, q):
    """Mean over tokens of KL(p || q) for rows of probabilities."""
    p = np.clip(p, EPS, 1.0)
    q = np.clip(q, EPS, 1.0)
    return float(np.mean(np.sum(p * (np.log(p) - np.log(q)), axis=-1)))


def js(p, q):
    """Jensen-Shannon divergence (nats) of two distributions."""
    p = np.asarray(p, dtype=np.float64)
    q = np.asarray(q, dtype=np.float64)
    m = 0.5 * (p + q)
    return 0.5 * kl(p[None], m[None]) + 0.5 * kl(q[None], m[None])


def topk_flip_rate(a, b, k):
    """Fraction of top-k slots whose expert changed (0 = same set, 1 = disjoint)."""
    sa, sb = topk_sets(a, k), topk_sets(b, k)
    inter = np.array([len(np.intersect1d(x, y, assume_unique=True)) for x, y in zip(sa, sb)])
    return float(np.mean(1.0 - inter / k))


def expert_usage(logits, k):
    """Expert-use histogram: share of top-k assignments per expert."""
    E = np.asarray(logits).shape[1]
    counts = np.bincount(topk_sets(logits, k).ravel(), minlength=E).astype(np.float64)
    return counts / max(counts.sum(), 1.0)


def route_entropy(logits):
    """Mean per-token router entropy, normalised to [0,1] by log(E)."""
    p = np.clip(softmax(logits), EPS, 1.0)
    return float(np.mean(-np.sum(p * np.log(p), axis=-1)) / math.log(p.shape[1]))


def usage_entropy(usage):
    u = np.clip(np.asarray(usage, dtype=np.float64), EPS, 1.0)
    return float(-np.sum(u * np.log(u)) / math.log(len(u)))


def route_collision(logits, k):
    """Probability that two random tokens share their exact top-k expert set
    (composition statistic; 1/C(E,k) floor for uniform random routing)."""
    sets = topk_sets(logits, k)
    _, counts = np.unique(sets, axis=0, return_counts=True)
    share = counts / counts.sum()
    return float(np.sum(share ** 2))


def norm_shift(a, b):
    """Relative change of the mean row norm."""
    na = float(np.mean(np.linalg.norm(a, axis=-1)))
    nb = float(np.mean(np.linalg.norm(b, axis=-1)))
    return abs(nb - na) / max(na, EPS)


def cosine_drift(a, b):
    """1 - mean per-token cosine similarity (0 = unchanged direction)."""
    na = np.linalg.norm(a, axis=-1)
    nb = np.linalg.norm(b, axis=-1)
    cos = np.sum(a * b, axis=-1) / np.maximum(na * nb, EPS)
    return float(1.0 - np.mean(cos))


def linear_cka(a, b):
    """Linear CKA over tokens (1 = same representation geometry)."""
    a = a - a.mean(axis=0)
    b = b - b.mean(axis=0)
    hsic = np.linalg.norm(a.T @ b) ** 2
    den = np.linalg.norm(a.T @ a) * np.linalg.norm(b.T @ b)
    return float(hsic / max(den, EPS))


# ---------------------------------------------------------------- comparison

def compare_layer(base: LayerCapture, new: LayerCapture, k: int) -> dict:
    if base.logits.shape != new.logits.shape:
        raise ValueError('layer shapes differ; align tokens first (Capture.tail)')
    pb, pn = softmax(base.logits), softmax(new.logits)
    ub, un = expert_usage(base.logits, k), expert_usage(new.logits, k)
    out = {
        'router_kl': kl(pb, pn),
        'topk_flip_rate': topk_flip_rate(base.logits, new.logits, k),
        'expert_hist_shift': js(ub, un),
        'router_input_norm_shift': norm_shift(base.router_input, new.router_input),
        'router_input_drift': cosine_drift(base.router_input, new.router_input),
        'route_entropy_base': route_entropy(base.logits),
        'route_entropy_new': route_entropy(new.logits),
        'usage_entropy_base': usage_entropy(ub),
        'usage_entropy_new': usage_entropy(un),
        'route_collision_base': route_collision(base.logits, k),
        'route_collision_new': route_collision(new.logits, k),
    }
    if base.residual is not None and new.residual is not None:
        out['residual_norm_shift'] = norm_shift(base.residual, new.residual)
        out['shared_drift'] = cosine_drift(base.residual, new.residual)
        out['shared_cka'] = linear_cka(base.residual, new.residual) if base.residual.shape[0] > 2 else None
    return out


def compare(base: Capture, new: Capture, layers=None) -> dict:
    """Per-layer metrics plus aggregate (max over compared layers for the gate)."""
    if base.top_k != new.top_k:
        raise ValueError('top_k differs between captures')
    keys = sorted(set(base.layers) & set(new.layers)) if layers is None else list(layers)
    if not keys:
        raise ValueError('no common layers')
    per = {i: compare_layer(base.layers[i], new.layers[i], base.top_k) for i in keys}
    agg = {}
    for m in list(GATE_KNOBS.values()) + list(EXTRA_METRICS):
        vals = [per[i][m] for i in keys if per[i].get(m) is not None]
        if vals:
            agg[m] = float(max(vals))
            agg[m + '_mean'] = float(np.mean(vals))
    return {'layers': keys, 'per_layer': per, 'aggregate': agg}


# ---------------------------------------------------------------- calibration + gate

def calibrate(variation: list, quantile=0.95, margin=1.0, min_samples=8, source=''):
    """Thresholds from receiver-native baseline variation (B3-H6).

    `variation` holds aggregate dicts of comparisons between runs that should
    count as "the same" for this receiver (e.g. neutral prefix, numeric dtype).
    Threshold = margin * quantile of that variation. Fewer than `min_samples`
    comparisons -> no threshold (status UNCALIBRATED).
    """
    n = len(variation)
    th = {}
    for knob, metric in list(GATE_KNOBS.items()) + [(f'report.{m}', m) for m in EXTRA_METRICS]:
        vals = [v[metric] for v in variation if v.get(metric) is not None]
        if len(vals) >= min_samples:
            th[knob] = float(margin * np.quantile(vals, quantile))
    status = 'TUNE_CALIBRATED' if all(k in th for k in GATE_KNOBS) else 'UNCALIBRATED'
    return {'status': status, 'n': n, 'quantile': quantile, 'margin': margin,
            'min_samples': min_samples, 'source': source, 'thresholds': th}


def router_stability_gate(agg: dict, calibration: dict, old_task_loss_delta=None,
                          max_old_task_loss_delta=None, utility_gain=None,
                          min_downstream_utility_gain=None) -> dict:
    """B3-H6 verdict for one latent-message (or update) condition.

    PASS only if calibrated, every router metric is within its threshold, the
    old-task loss delta is within the user/TUNE limit (when given) and the
    downstream utility gain reaches its minimum (when given). Missing utility
    evidence never counts as gain.
    """
    reasons = []
    if calibration.get('status') != 'TUNE_CALIBRATED':
        return {'verdict': 'UNCALIBRATED', 'reasons': ['no receiver-native baseline calibration']}
    th = calibration['thresholds']
    checks = {}
    for knob, metric in GATE_KNOBS.items():
        val = agg.get(metric)
        if val is None:
            reasons.append(f'{metric} not measured')
            checks[knob] = None
            continue
        ok = val <= th[knob]
        checks[knob] = {'value': val, 'limit': th[knob], 'ok': bool(ok)}
        if not ok:
            reasons.append(f'{metric} {val:.4g} > {th[knob]:.4g}')
    if max_old_task_loss_delta is not None:
        if old_task_loss_delta is None:
            reasons.append('old-task loss delta not measured')
        elif old_task_loss_delta > max_old_task_loss_delta:
            reasons.append(f'old-task loss delta {old_task_loss_delta:.4g} > {max_old_task_loss_delta:.4g}')
        checks['B3.max_old_task_loss_delta'] = {'value': old_task_loss_delta, 'limit': max_old_task_loss_delta}
    if min_downstream_utility_gain is not None:
        if utility_gain is None:
            reasons.append('downstream utility not measured')
        elif utility_gain < min_downstream_utility_gain:
            reasons.append(f'utility gain {utility_gain:.4g} < {min_downstream_utility_gain:.4g}')
        checks['B3.min_downstream_utility_gain'] = {'value': utility_gain, 'limit': min_downstream_utility_gain}
    return {'verdict': 'PASS' if not reasons else 'FAIL', 'reasons': reasons, 'checks': checks}


# ---------------------------------------------------------------- §16.2.1 interference monitor

def counterfactual_route_shift(x_old, x_new, w_old, w_new, k):
    """Split a route change into its router-input part and its router-weight part.

    logits = x @ W.T. input part: same old router on old vs new inputs;
    router part: old inputs through old vs new router. Needs the router weights
    of both generations (only available where the runner exposes them)."""
    base = np.asarray(x_old) @ np.asarray(w_old).T
    by_input = np.asarray(x_new) @ np.asarray(w_old).T
    by_router = np.asarray(x_old) @ np.asarray(w_new).T
    return {
        'input_kl': kl(softmax(base), softmax(by_input)),
        'input_flip': topk_flip_rate(base, by_input, k),
        'router_kl': kl(softmax(base), softmax(by_router)),
        'router_flip': topk_flip_rate(base, by_router, k),
    }


def interference_report(old_before: Capture, old_after: Capture, loss_before: float,
                        loss_after: float, restore_losses: dict | None = None,
                        delta_norms: dict | None = None, calibration: dict | None = None,
                        min_forgetting: float = 0.0, route=None) -> dict:
    """§16.2.1 / §24.19 / §91 monitor after a continual update.

    old_before/old_after: captures of the *old* task before and after the update.
    restore_losses: old-task loss measured with one component group put back to
    its pre-update weights (e.g. {'shared': .., 'router': .., 'experts': ..}).
    This restoration ablation is the causal attribution; drift numbers alone are
    only correlational. Verdict PRE_ROUTER_BOTTLENECK requires restoring the
    shared (pre-router) group to recover most of the forgetting.
    """
    cmp = compare(old_before, old_after)
    agg = cmp['aggregate']
    forgetting = float(loss_after - loss_before)
    rep = {
        'old_task_loss_before': float(loss_before),
        'old_task_loss_after': float(loss_after),
        'old_task_loss_delta': forgetting,
        'pre_router_drift': agg.get('shared_drift'),
        'router_input_drift': agg.get('router_input_drift'),
        'router_input_norm_shift': agg.get('router_input_norm_shift'),
        'old_task_route_shift': agg.get('router_kl'),
        'old_task_topk_flip': agg.get('topk_flip_rate'),
        'expert_hist_shift': agg.get('expert_hist_shift'),
        'per_layer': cmp['per_layer'],
    }
    usage = [expert_usage(l.logits, old_after.top_k) for l in old_after.layers.values()]
    rep['expert_usage_entropy'] = float(np.mean([usage_entropy(u) for u in usage]))
    rep['route_entropy'] = float(np.mean([route_entropy(l.logits) for l in old_after.layers.values()]))
    rep['route_collision'] = float(np.mean([route_collision(l.logits, old_after.top_k)
                                            for l in old_after.layers.values()]))
    if delta_norms:
        rep['delta_norms'] = {k: float(v) for k, v in delta_norms.items()}
    if route:
        rep['counterfactual_route'] = route
    th = (calibration or {}).get('thresholds', {})
    drift_flag = None
    if 'report.shared_drift' in th and rep['pre_router_drift'] is not None:
        drift_flag = rep['pre_router_drift'] > th['report.shared_drift']
    rep['pre_router_drift_above_baseline'] = drift_flag
    attribution = {}
    if restore_losses and forgetting > 0:
        for group, loss in restore_losses.items():
            attribution[group] = float((loss_after - loss) / forgetting)
    rep['restoration_recovery'] = attribution
    if forgetting <= min_forgetting:
        verdict = 'NO_FORGETTING'
    elif not attribution:
        verdict = 'UNATTRIBUTED'
    else:
        best = max(attribution, key=attribution.get)
        if best == 'shared' and attribution['shared'] >= 0.5:
            verdict = 'PRE_ROUTER_BOTTLENECK'
        elif best in ('experts', 'router') and attribution[best] >= 0.5:
            verdict = 'EXPERT_OR_ROUTER'
        else:
            verdict = 'MIXED'
    rep['verdict'] = verdict
    # §16.2.1: never "repair" only experts/router when forgetting starts before the router.
    rep['allowed_repair'] = {
        'PRE_ROUTER_BOTTLENECK': 'shared-component protection (anchor/rollback of shared group)',
        'EXPERT_OR_ROUTER': 'expert/router rollback or delta anchoring',
        'MIXED': 'roll back all touched groups; no single-group repair',
        'UNATTRIBUTED': 'measure restoration ablation before any repair',
        'NO_FORGETTING': 'none',
    }[verdict]
    return rep


# ---------------------------------------------------------------- §91 update order

PHASES = ('A', 'B', 'C', 'D')
PHASE_SCOPE = {
    'A': 'router frozen, shared trunk frozen; small predictor/projector/delta only',
    'B': 'active-expert delta in SHADOW with route-distribution monitor and old-task retention',
    'C': 'selected router adaptation in SHADOW; only with missed-routing evidence',
    'D': 'selected shared component update; rare; only with proven pre-router bottleneck',
}


def phase_allowed(phase: str, evidence: dict) -> dict:
    """§91 mandatory order. evidence keys (all default False/None):
    phase_a_retention_ok, route_monitor_active, retention_ok, missed_routing,
    pre_router_bottleneck (an interference_report verdict == PRE_ROUTER_BOTTLENECK).
    """
    if phase not in PHASES:
        raise ValueError(phase)
    need = []
    if phase in ('B', 'C', 'D'):
        if not evidence.get('phase_a_retention_ok'):
            need.append('phase A retention evidence')
        if not evidence.get('route_monitor_active'):
            need.append('route-distribution monitor')
        if not evidence.get('retention_ok'):
            need.append('old-task retention')
    if phase == 'C' and not evidence.get('missed_routing'):
        need.append('missed-routing evidence')
    if phase == 'D' and evidence.get('pre_router_bottleneck') != 'PRE_ROUTER_BOTTLENECK':
        need.append('proven pre-router bottleneck')
    return {'phase': phase, 'allowed': not need, 'missing': need, 'scope': PHASE_SCOPE[phase],
            'mode': 'ACTIVE_SCOPE' if phase == 'A' else 'SHADOW'}


def expert_commit_allowed(eligible: bool, error: float | None, modulator: str | None,
                          permission: bool, retention_ok: bool) -> dict:
    """§91: an expert being hit only creates eligibility. A weight commit needs
    error + typed modulator + permission + retention; activation alone never commits."""
    missing = []
    if not eligible:
        missing.append('eligibility')
    if error is None or error <= 0:
        missing.append('error signal')
    if not modulator:
        missing.append('typed modulator')
    if not permission:
        missing.append('permission')
    if not retention_ok:
        missing.append('retention')
    return {'commit': not missing, 'missing': missing}
