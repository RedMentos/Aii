"""Capability admission schema. This module does not implement model inference.

Even a conforming declaration is not a runtime proof: a real integration must
generate independent loader, tensor-hook and regression test reports.
"""
from dataclasses import dataclass
from typing import Tuple
from .contracts import nonempty

@dataclass(frozen=True)
class ModelDeclaration:
    model_id: str
    revision: str
    family: str
    architecture: str
    pretrained: bool
    backend: str
    expert_count: int = 0
    native_top_k: int = 0
    hidden_export: bool = False
    latent_injection: bool = False
    local_backward: bool = False
    route_telemetry: bool = False
    evidence_refs: Tuple[str, ...] = ()

def admission_problems(gist: ModelDeclaration, detail: ModelDeclaration,
                       judge: ModelDeclaration) -> Tuple[str, ...]:
    problems = []
    if gist.model_id == detail.model_id or gist.family == detail.family:
        problems.append('Gist and Detail must be different pretrained model families')
    for role, body in [('gist', gist), ('detail', detail), ('judge', judge)]:
        for field in ('model_id', 'revision', 'family', 'backend'):
            try: nonempty(getattr(body, field), field)
            except ValueError: problems.append(role + ': missing ' + field)
        if body.backend.lower() in ('unknown', 'mock', 'echo', 'none', 'unverified'):
            problems.append(role + ': backend has no verified integration')
        if not body.pretrained: problems.append(role + ': requires pretrained weights')
        if not body.evidence_refs: problems.append(role + ': missing runtime test evidence references')
        for cap in ('hidden_export', 'latent_injection', 'local_backward'):
            if getattr(body, cap) is not True: problems.append(role + ': missing ' + cap)
        if role in ('gist', 'detail'):
            if body.architecture != 'moe' or body.expert_count < 2:
                problems.append(role + ': requires genuine MoE experts')
            if not 1 <= body.native_top_k <= body.expert_count:
                problems.append(role + ': invalid native Top-k')
            if body.route_telemetry is not True: problems.append(role + ': missing route telemetry')
        elif body.architecture != 'dense':
            problems.append('judge: requires dense FFN core (hybrid attention is allowed)')
    if gist.native_top_k <= detail.native_top_k:
        problems.append('Gist native Top-k must exceed Detail native Top-k in this candidate profile')
    return tuple(problems)

