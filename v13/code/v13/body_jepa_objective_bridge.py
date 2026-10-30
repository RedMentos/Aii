"""IH-H25: explicitly constructed Body-JEPA ObjectiveAdapter for offline research.

This bridges the actual differentiable two-view JEPA loss to the central
objective interface. Importing it does NOT register a plugin, enable training,
grant Age authority or change the unavailable live B_local_JEPA gate.
"""
from .body_jepa import OBJECTIVE as BJ_OBJECTIVE, jepa_loss
from .objectives import ObjectiveAdapter

REQUIRED = (
    "torch", "model", "predictor", "context_view_ids", "target_view_ids",
    "target_latents", "target_mode", "eligibility", "source_ids",
    "target_source_ids", "path", "authority",
)
PATHS = ("B1_DETAIL", "B2_GIST")
AUTHORITY = "SHADOW_NO_AGE_ACTION"


def research_loss(batch):
    """Return differentiable scalar JEPA-only loss; caller never receives authority.

    Source IDs describe the same experiences before an explicitly deranged
    shuffled-target control. The EMA target must be built before a student
    autograd graph; jepa_loss detaches it again for stop-gradient.
    """
    if type(batch) is not dict:
        raise ValueError("Objective batch must be a dict")
    if any(key not in batch for key in REQUIRED):
        raise ValueError("Missing typed Body-JEPA objective input")
    if batch["path"] not in PATHS or batch["authority"] != AUTHORITY:
        raise ValueError("Unregistered path or forbidden objective authority")
    sources = batch["source_ids"]
    targets = batch["target_source_ids"]
    if (type(sources) not in (list, tuple) or type(targets) not in (list, tuple)
            or len(sources) < 2 or len(sources) != len(set(sources))
            or any(type(v) is not str or not v for v in sources)
            or list(sources) != list(targets)):
        raise ValueError("Body-JEPA source alignment invalid")
    torch = batch["torch"]
    ctx, tgt = batch["context_view_ids"], batch["target_view_ids"]
    if (not isinstance(ctx, (list, tuple)) or not isinstance(tgt, (list, tuple))
            or len(ctx) != 2 or len(tgt) != 2
            or ctx[0].shape[0] != len(sources)
            or tgt[0].shape[0] != len(sources)):
        raise ValueError("Body-JEPA batch/source row count invalid")
    weights = torch.as_tensor(batch["eligibility"], dtype=torch.float32)
    if (weights.ndim != 1 or len(weights) != len(sources)
            or not bool(torch.isfinite(weights).all())
            or bool((weights < 0).any()) or bool((weights > 1).any())
            or not bool(weights.sum() > 0)):
        raise ValueError("Body-JEPA eligibility outside [0,1] or empty")
    mode = batch["target_mode"]
    if mode not in ("ema", "base", "shuffled"):
        raise ValueError("Unknown Body-JEPA target mode")
    perm = batch.get("perm")
    if mode != "shuffled" and perm is not None:
        raise ValueError("Permutation only belongs to shuffled control")
    loss, _ = jepa_loss(
        torch, batch["model"], batch["predictor"], ctx, tgt, mode,
        base_targets=batch["target_latents"], perm=perm, weights=weights)
    if loss.ndim != 0 or not bool(torch.isfinite(loss.detach())):
        raise ValueError("Body-JEPA objective did not return finite scalar")
    return loss


def research_adapter():
    """No global register() call: PARTIAL never changes B_local_JEPA authority."""
    adapter = ObjectiveAdapter(
        objective_id=BJ_OBJECTIVE.objective_id + "_RESEARCH_ONLY",
        applicable_components=BJ_OBJECTIVE.applicable_components,
        required_inputs=REQUIRED,
        target_builder=BJ_OBJECTIVE.target_builder,
        stop_gradient_policy=BJ_OBJECTIVE.stop_gradient_policy,
        ema_policy=BJ_OBJECTIVE.ema_policy,
        loss_terms=("JEPA_COSINE_ONLY",),
        credit_mapper=BJ_OBJECTIVE.credit_mapper,
        update_scope=BJ_OBJECTIVE.update_scope,
        eval_metrics=BJ_OBJECTIVE.eval_metrics,
        status="PARTIAL",
        reason="Offline Torch two-view gradient only; no native 1.2B TrainRunnerProof, heldout utility, Redmi or Age authority",
        implementation_files=("v13/body_jepa.py", "v13/body_jepa_objective_bridge.py"),
        loss=research_loss,
    )
    adapter.validate()
    return adapter
