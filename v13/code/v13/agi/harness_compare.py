"""WP-HX2 lab-only same-task harness comparison without gold answers.

Reference and allow-listed candidate use identical held-out tasks and seeds.
A blind judge chooses between anonymous outputs twice in reversed order.
This measures preference, NOT factual accuracy or an AG8 approval. No live
consumer, model download, tool execution, learning or Age promotion.
"""
import copy
import hashlib
import json
import math

from . import harness
from .blind_select import blind_select, verify as verify_blind

REVISION = "hx2-blind-harness-lab-v2"
MAX_TASKS = 512
MAX_OUTPUT = 8192
MIN_PAIRED = 30
ALPHA = 0.05


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False)


def _hash(value):
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _validate(tasks, diff, seed):
    if not isinstance(tasks, (list, tuple)) or not 1 <= len(tasks) <= MAX_TASKS:
        raise ValueError("HX2_TASK_COUNT_INVALID")
    if type(seed) is not int or not 0 <= seed < 2**31:
        raise ValueError("HX2_SEED_INVALID")
    checked = harness.candidate(diff)
    if len(checked) != 1:
        raise ValueError("HX2_ONE_TARGET_PER_COMPARISON")
    seen = set()
    clean = []
    for t in tasks:
        if not isinstance(t, dict) or set(t) != {"id", "task_type", "question", "split"}:
            raise ValueError("HX2_TASK_SCHEMA_INVALID")
        key = t["id"]
        if not isinstance(key, str) or not key or len(key.encode()) > 128 or key in seen:
            raise ValueError("HX2_TASK_ID_INVALID_OR_DUPLICATE")
        if t["split"] != "holdout":
            raise ValueError("HX2_HOLDOUT_ONLY")
        if not isinstance(t["task_type"], str) or not t["task_type"]:
            raise ValueError("HX2_TASK_TYPE_INVALID")
        if not isinstance(t["question"], str) or not t["question"].strip() or len(t["question"]) > 4096:
            raise ValueError("HX2_QUESTION_INVALID")
        seen.add(key)
        clean.append(dict(t))
    return clean, checked


def _provenance(tasks, excluded_ids, solver_revision, judge_revision):
    if not isinstance(excluded_ids, (list, tuple)) or len(excluded_ids) > 100000:
        raise ValueError("HX2_EXCLUSION_REGISTRY_INVALID")
    if any(not isinstance(x, str) or not x or len(x.encode()) > 128
           for x in excluded_ids) or len(set(excluded_ids)) != len(excluded_ids):
        raise ValueError("HX2_EXCLUSION_REGISTRY_INVALID")
    if set(t["id"] for t in tasks) & set(excluded_ids):
        raise ValueError("HX2_TRAIN_HOLDOUT_OVERLAP")
    for revision in (solver_revision, judge_revision):
        if not isinstance(revision, str) or not 1 <= len(revision) <= 128:
            raise ValueError("HX2_REVISION_INVALID")
    return {"excluded_id_hashes_sha256": _hash(sorted(excluded_ids)),
            "excluded_count": len(excluded_ids),
            "solver_revision": solver_revision,
            "judge_revision": judge_revision}


def _baseline(baseline):
    """Validate and snapshot every reference target before sealing inputs."""
    if baseline is None:
        values = {name: harness.default(name) for name in harness.TARGETS}
    elif isinstance(baseline, dict) and set(baseline) == set(harness.TARGETS):
        values = baseline
    else:
        raise ValueError("HX2_BASELINE_INVALID")
    return copy.deepcopy(harness.candidate(values))


def preregister(tasks, diff, seed, *, excluded_ids=(),
                solver_revision="UNPINNED", judge_revision="UNPINNED",
                baseline=None):
    """Immutable comparison input commitment; a hash is not an approval."""
    clean, checked = _validate(tasks, diff, seed)
    provenance = _provenance(clean, excluded_ids, solver_revision, judge_revision)
    base = _baseline(baseline)
    baseline_sha256 = _hash(base)
    data = {"revision": REVISION, "tasks": clean, "diff": checked,
            "seed": seed, "provenance": provenance,
            "baseline_sha256": baseline_sha256}
    return {"revision": REVISION, "input_sha256": _hash(data),
            "baseline_sha256": baseline_sha256,
            "task_ids_sha256": _hash([t["id"] for t in clean]),
            **provenance,
            "target": next(iter(checked)), "task_count": len(clean),
            "authority": "LAB_ONLY", "live_consumers": 0,
            "approval_allowed": False, "age_promotion": False}


def _output(value):
    if not isinstance(value, str) or not value.strip() or len(value) > MAX_OUTPUT:
        raise ValueError("HX2_SOLVER_OUTPUT_INVALID")
    if any(ord(c) < 32 and c not in "\n\t" for c in value):
        raise ValueError("HX2_SOLVER_CONTROL_CHARACTER")
    return value


def _one_sided_sign_p(wins, losses):
    n = wins + losses
    if not n:
        return None
    return sum(math.comb(n, k) for k in range(wins, n + 1)) / (2**n)


def compare(tasks, diff, seed, solver, judge, preregistration, baseline=None,
            *, excluded_ids=(), solver_revision="UNPINNED",
            judge_revision="UNPINNED"):
    """solver(task, overlay, seed) -> text; judge([{label,output}]) -> label.

    No model/tool is launched here. Callers supply a frozen, audited solver and
    independent judge. Every error and disagreement remains in the report.
    """
    clean, checked = _validate(tasks, diff, seed)
    base = _baseline(baseline)
    expected = preregister(clean, checked, seed, excluded_ids=excluded_ids,
                           solver_revision=solver_revision,
                           judge_revision=judge_revision, baseline=base)
    if not isinstance(preregistration, dict) or preregistration != expected:
        raise ValueError("HX2_PREREGISTRATION_MISMATCH")
    target = next(iter(checked))
    variant = dict(base)
    variant.update(checked)
    if variant[target] == base[target]:
        raise ValueError("HX2_CANDIDATE_EQUALS_REFERENCE")
    rows = []
    wins = losses = ties = inconsistent = no_pick = 0
    for index, task in enumerate(clean):
        task_seed = seed + index
        digests = {}
        try:
            reference = _output(solver(dict(task), copy.deepcopy(base), task_seed))
            digests["reference"] = hashlib.sha256(reference.encode()).hexdigest()
            changed = _output(solver(dict(task), copy.deepcopy(variant), task_seed))
            digests["candidate"] = hashlib.sha256(changed.encode()).hexdigest()
            if reference == changed:
                outcome, selection, commitment = "TIE", None, None
                ties += 1
            else:
                judge_views = []
                def blind_judge(items):
                    judge_views.append(copy.deepcopy(items))
                    return judge(items)
                decision = blind_select(
                    [{"origin": "reference", "output": reference},
                     {"origin": "candidate", "output": changed}],
                    blind_judge, seed=task_seed, rounds=2)
                if not verify_blind(decision):
                    raise ValueError("HX2_BLIND_COMMITMENT_INVALID")
                outcome = decision["status"]
                selection = decision["pick_origin"]
                commitment = decision["commitment"]
                digests["judge_view_sha256"] = _hash(judge_views)
                if outcome == "PICKED":
                    if selection == "candidate":
                        wins += 1
                    elif selection == "reference":
                        losses += 1
                    else:
                        raise ValueError("HX2_UNKNOWN_BLIND_ORIGIN")
                elif outcome == "INCONSISTENT":
                    inconsistent += 1
                else:
                    no_pick += 1
        except Exception as exc:
            outcome, selection, commitment = "NO_PICK", None, None
            no_pick += 1
            error = type(exc).__name__
        else:
            error = None
        rows.append({"task_id_hash": hashlib.sha256(task["id"].encode()).hexdigest(),
                     "seed": task_seed, "status": outcome, "pick_origin": selection,
                     "blind_commitment": commitment, "output_sha256": digests,
                     "error_type": error})
    p = _one_sided_sign_p(wins, losses)
    status = ("PREFERENCE_SIGNAL_ONLY" if wins + losses >= MIN_PAIRED
              and wins > losses and p is not None and p <= ALPHA
              and not inconsistent and not no_pick
              and expected["excluded_count"] > 0
              and expected["solver_revision"] != "UNPINNED"
              and expected["judge_revision"] != "UNPINNED"
              else "NOT_SUPPORTED")
    return {"revision": REVISION, "status": status,
            "input_sha256": expected["input_sha256"],
            "baseline_sha256": expected["baseline_sha256"],
            "excluded_id_hashes_sha256": expected["excluded_id_hashes_sha256"],
            "excluded_count": expected["excluded_count"],
            "solver_revision": expected["solver_revision"],
            "judge_revision": expected["judge_revision"],
            "target": target, "n_tasks": len(clean), "paired": wins + losses,
            "candidate_wins": wins, "reference_wins": losses, "ties": ties,
            "inconsistent": inconsistent, "no_pick": no_pick,
            "one_sided_sign_p": p, "rows": rows,
            "claim_limit": "Blind preference only, not factual correctness, utility or AG8 approval",
            "authority": "LAB_ONLY", "live_consumers": 0,
            "external_action_executed": False, "model_downloaded": False,
            "approval_allowed": False, "age_promotion": False,
            "learning_permission": "NONE"}
