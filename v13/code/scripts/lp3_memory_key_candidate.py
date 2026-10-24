#!/usr/bin/env python3
"""WP-LP3 isolated, OFF-by-default latent-key-to-answer experiment.

A frozen C3 state predicts an answer-memory key. Unlike LP2, that key is
actually consumed to select the answer text. No runtime changes or authority.
Native evidence requires a pinned local HF master; toy tests are software only.
"""
import argparse
import hashlib
import json
import math
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from lp2_assignment_objective import FACTS, HELDOUT, NEAR_MISS  # noqa: E402

SEEDS = (31, 37, 41, 43)
STEPS = 30
TEMP = 0.1
LR = 1e-3
# Pinned by the LP1/LP2 feasibility handoff; no alternate HF weight cohort.
PINNED_MASTER_SHA256 = "1c9c77a4471a7f590f85240f74ed1fc26df7fbde88c3006724e2f93ca993ea4e"
PINNED_HF_REVISION = "55e5a53e8637c4522a0577040fe68682db3fbbb6"
HF_ASSETS = ("model.safetensors", "config.json", "generation_config.json",
             "tokenizer.json", "tokenizer_config.json", "chat_template.jinja", "LICENSE")


def _sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def preflight_binding(master, expected_master_sha256, *, source_root=HERE):
    """Fail before creating evidence if exact cohort assets/sources are missing.

    File hashes bind local bytes; they do not independently authenticate the
    remaining snapshot assets against the upstream revision.
    """
    if expected_master_sha256 != PINNED_MASTER_SHA256:
        raise ValueError("master digest is not the preregistered LP1/LP2 master")
    master, source_root = Path(master), Path(source_root)
    hashes = {}
    for name in HF_ASSETS:
        path = master / name
        if not path.is_file() or path.stat().st_size == 0:
            raise ValueError(f"missing/empty HF snapshot asset: {name}")
        hashes[name] = _sha256_file(path)
    if hashes["model.safetensors"] != PINNED_MASTER_SHA256:
        raise ValueError("HF master weight bytes do not match pinned SHA256")
    for name in ("config.json", "generation_config.json", "tokenizer.json", "tokenizer_config.json"):
        try:
            with (master / name).open("r", encoding="utf-8") as f:
                if not isinstance(json.load(f), dict):
                    raise ValueError(f"HF snapshot JSON is not an object: {name}")
        except (UnicodeError, json.JSONDecodeError) as exc:
            raise ValueError(f"invalid HF snapshot JSON: {name}") from exc
    deps = {}
    for name in ("lp2_assignment_objective.py", "lora_bench.py"):
        path = source_root / name
        if not path.is_file() or path.stat().st_size == 0:
            raise ValueError(f"missing fixture dependency: {name}")
        deps[name] = _sha256_file(path)
    return {"repo": "LiquidAI/LFM2.5-350M", "revision": PINNED_HF_REVISION,
            "assets_sha256": hashes, "fixture_dependencies_sha256": deps,
            "upstream_nonweight_asset_identity": "NOT_INDEPENDENTLY_VERIFIED"}

# Separate, unseen questions; five historical LP2 failures already occur in HELDOUT.
HARDER = (
    (0, "I forgot what to call the feline I own. Remind me?"),
    (1, "If someone needs to find me at work, which shop is it?"),
    (2, "Remind me of my preferred shade."),
    (3, "Who is the sibling whose name I told you?"),
    (4, "What do I make music with?"),
    (5, "Name the handset model I mentioned owning."),
    (6, "How did I label the research effort I am building?"),
    (7, "Tell me the month and day I celebrate my birth."),
    (8, "The animal I ride has what name?"),
    (9, "Name my new hometown, not my former one."),
    (10, "Recall my maternal grandmother's given name."),
    (11, "Which name is painted on my vessel?"),
    (12, "What tongue am I currently studying?"),
    (13, "What digits identify the locker assigned to me?"),
    (14, "Remind me of the name of my music group."),
    (15, "What species did I put into the soil?"),
)


def normalized(x):
    import torch
    if x.ndim != 2 or not x.shape[0] or not x.shape[1]:
        raise ValueError("expected nonempty rank-2 state matrix")
    if not bool(torch.isfinite(x).all()):
        raise ValueError("nonfinite latent state")
    norms = x.float().norm(dim=-1, keepdim=True)
    if bool((norms <= 1e-12).any()):
        raise ValueError("zero latent state")
    return x.float() / norms


def retrieve(query, bank, values, *, min_similarity=0.35, min_margin=0.03):
    """Exact stored value only; invalid/ambiguous query abstains, never guesses.

    The bank is NOT changed when values are shifted for the negative control.
    Moving both bank and values would be an invalid (invariant) ablation.
    """
    import torch
    query = query.detach()  # retrieval is a read-only decision, never a gradient path
    if len(values) != bank.shape[0] or len(set(values)) != len(values):
        raise ValueError("bank/value mismatch or duplicate values")
    b = normalized(bank)
    if query.ndim != 2 or query.shape[1] != b.shape[1]:
        raise ValueError("query dimension mismatch")
    if not bool(torch.isfinite(query).all()):
        raise ValueError("nonfinite query")
    qnorm = query.float().norm(dim=-1)
    out = []
    for i, q in enumerate(query):
        if float(qnorm[i]) <= 1e-12:
            out.append(None)
            continue
        scores = b @ (q.float() / qnorm[i])
        best = torch.argsort(scores, descending=True, stable=True)
        first = int(best[0]); top = float(scores[first]); second = float(scores[int(best[1])]) if len(best) > 1 else -1.0
        out.append(values[first] if top >= min_similarity and top - second > min_margin else None)
    return out


def predictor(dim):
    import torch
    net = torch.nn.Sequential(torch.nn.LayerNorm(dim), torch.nn.Linear(dim, 256), torch.nn.GELU(), torch.nn.Linear(256, dim))
    torch.nn.init.zeros_(net[3].weight)
    torch.nn.init.zeros_(net[3].bias)
    return net


def fit_predictor(train, bank, seed, *, shifted=False, steps=STEPS):
    """Predictor-only InfoNCE; frozen encoder and answer bank, no CE/LoRA.

    This is a NEW isolated memory-key route, not a replay of LP2's LoRA cohort.
    """
    import torch
    import torch.nn.functional as F
    q = normalized(train).detach()
    b = normalized(bank).detach()
    if q.shape != b.shape or q.shape[0] < 2:
        raise ValueError("one prompt and one answer state per memory item required")
    torch.manual_seed(seed)
    net = predictor(q.shape[1]); opt = torch.optim.AdamW(net.parameters(), lr=LR, weight_decay=0)
    target = (torch.arange(len(q)) + int(shifted)) % len(q)
    initial = None
    for _ in range(steps):
        z = F.normalize(q + net(q), dim=-1)
        loss = F.cross_entropy((z @ b.T) / TEMP, target)
        if initial is None: initial = float(loss.detach())
        opt.zero_grad(); loss.backward(); opt.step()
    return net.eval(), {"initial_nce": initial, "final_nce": float(loss.detach()), "steps": steps}


def score(expected, retrieved):
    if len(expected) != len(retrieved):
        raise ValueError("evaluation length mismatch")
    return {"correct": sum(a == b for a, b in zip(expected, retrieved)),
            "abstain": sum(x is None for x in retrieved), "total": len(expected)}


def evaluate(train, bank, holdout, expected, near, *, seed):
    import torch
    if len(expected) != len(holdout):
        raise ValueError("holdout mismatch")
    if len(FACTS) != bank.shape[0]:
        raise ValueError("fixture/bank mismatch")
    holdout = normalized(holdout)
    near = normalized(near)
    values = tuple(answer for _, answer, _ in FACTS)
    wrong_values = values[1:] + values[:1]  # ONLY value binding is shifted
    good, good_loss = fit_predictor(train, bank, seed)
    bad, bad_loss = fit_predictor(train, bank, seed, shifted=True)
    with torch.no_grad():
        predicted = holdout + good(holdout)
        wrong_pred = holdout + bad(holdout)
        predicted_near = near + good(near)
        raw_near = near
    outputs = {
        "raw": retrieve(holdout, bank, values),
        "predicted": retrieve(predicted, bank, values),
        "wrong_trained": retrieve(wrong_pred, bank, values),
        "value_shift": retrieve(predicted, bank, wrong_values),
        "zero_intervention": retrieve(torch.zeros_like(predicted), bank, values),
    }
    near_outputs = {"raw": retrieve(raw_near, bank, values),
                    "predicted": retrieve(predicted_near, bank, values)}
    r = {name: score(expected, out) for name, out in outputs.items()}
    r.update({"expected": list(expected), "outputs": outputs, "near_outputs": near_outputs,
              "near_raw_nonabstain": sum(x is not None for x in near_outputs['raw']),
              "near_pred_nonabstain": sum(x is not None for x in near_outputs['predicted']),
              "good_loss": good_loss, "wrong_loss": bad_loss, "seed": seed})
    return r


def audit_rows(rows):
    """Recompute aggregates from closed per-question answers, reject edited scores."""
    for row in rows:
        expected = row['expected']
        for arm in ('raw', 'predicted', 'wrong_trained', 'value_shift', 'zero_intervention'):
            if row[arm] != score(expected, row['outputs'][arm]):
                raise ValueError(f"invalid {arm} aggregate in seed {row['seed']}")
        for name, key in (('raw', 'near_raw_nonabstain'), ('predicted', 'near_pred_nonabstain')):
            if row[key] != sum(v is not None for v in row['near_outputs'][name]):
                raise ValueError(f"invalid near-miss aggregate in seed {row['seed']}")


def verdict(rows):
    audit_rows(rows)
    if len(rows) != len(SEEDS) or {r['seed'] for r in rows} != set(SEEDS):
        return "LP3_INCOMPLETE"
    if any(r['zero_intervention']['abstain'] != r['zero_intervention']['total'] for r in rows):
        return "LP3_ZERO_INTERVENTION_FAILED"
    gains = [r['predicted']['correct'] - r['raw']['correct'] for r in rows]
    control = [r['predicted']['correct'] - max(r['wrong_trained']['correct'], r['value_shift']['correct']) for r in rows]
    leakage = [r['near_pred_nonabstain'] - r['near_raw_nonabstain'] for r in rows]
    if sum(x >= 4 for x in gains) >= 3 and sum(x >= 8 for x in control) >= 3 and max(leakage) <= 2:
        return "LP3_MEMORY_KEY_CANDIDATE_SUPPORTED_ONLY"
    return "LP3_MEMORY_KEY_NOT_SUPPORTED"


def encode(model, tok, texts):
    import torch
    out = []
    for s in texts:
        chat = tok.apply_chat_template([{"role": "user", "content": s}], add_generation_prompt=True, tokenize=False)
        ids = tok(chat, add_special_tokens=False, return_tensors="pt")["input_ids"]
        if ids.shape[1] == 0:
            raise ValueError("empty tokenization")
        with torch.inference_mode():
            hidden = model(input_ids=ids, output_hidden_states=True).hidden_states[-1][0]
        out.append(hidden[-1].float().cpu())
    return torch.stack(out)


def encode_answers(model, tok, texts):
    import torch
    out = []
    for s in texts:
        ids = tok(s, add_special_tokens=False, return_tensors="pt")["input_ids"]
        if ids.shape[1] == 0: raise ValueError("empty answer tokenization")
        with torch.inference_mode():
            h = model(input_ids=ids, output_hidden_states=True).hidden_states[-1][0]
        out.append(h.mean(0).float().cpu())
    return torch.stack(out)


def write_atomic(path, obj):
    path = Path(path)
    if path.exists(): raise FileExistsError(f"refusing to replace closed evidence: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    data = (json.dumps(obj, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()
    tmp = path.with_name(path.name + f".tmp-{os.getpid()}")
    try:
        with tmp.open('xb') as f: f.write(data); f.flush(); os.fsync(f.fileno())
        os.link(tmp, path)  # no replacement even if another writer races
        fd = os.open(path.parent, os.O_RDONLY | getattr(os, 'O_DIRECTORY', 0))
        try: os.fsync(fd)
        finally: os.close(fd)
    finally:
        tmp.unlink(missing_ok=True)
    return hashlib.sha256(data).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--master', type=Path, required=True)
    ap.add_argument('--master-sha256', required=True, help='full pinned SHA256 of local model.safetensors')
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    if a.out.exists() and any(a.out.iterdir()):
        raise SystemExit('HARD_BLOCKER: existing attempt directory; never resume/overwrite closed evidence')
    try:
        snapshot = preflight_binding(a.master, a.master_sha256)
    except (OSError, ValueError) as exc:
        raise SystemExit(f'HARD_BLOCKER: {exc}') from exc
    actual = snapshot['assets_sha256']['model.safetensors']
    tasks = tuple(HELDOUT) + HARDER
    binding = {"schema": "V13_LP3_MEMORY_KEY_V1", "master_sha256": actual,
               "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
               "lp2_fixture_sha256": snapshot['fixture_dependencies_sha256']['lp2_assignment_objective.py'],
               "snapshot_binding": snapshot,
               "master_scope": "Linux_HF_FP32_FROZEN_ENCODER", "phone_measured": False,
               "runtime_enabled": False, "body_jepa_gate_pass": False, "step2_gate_pass": False,
               "params": {"seeds": SEEDS, "steps": STEPS, "temperature": TEMP, "lr": LR,
                          "items": len(FACTS), "holdout": len(tasks), "min_similarity": 0.35, "min_margin": 0.03}}
    write_atomic(a.out / 'run_manifest.json', binding)
    import torch
    from transformers import AutoTokenizer, AutoModelForCausalLM
    torch.set_num_threads(4)
    tok = AutoTokenizer.from_pretrained(str(a.master), local_files_only=True, trust_remote_code=False)
    model = AutoModelForCausalLM.from_pretrained(str(a.master), local_files_only=True, trust_remote_code=False, dtype=torch.float32).eval()
    q = encode(model, tok, [p for p, _, _ in FACTS]); bank = encode_answers(model, tok, [t for _, t, _ in FACTS])
    h = encode(model, tok, [prompt for _, prompt in tasks]); near = encode(model, tok, [q for q, _ in NEAR_MISS])
    expected = [FACTS[i][1] for i, _ in tasks]
    rows = []
    for seed in SEEDS:
        try:
            row = evaluate(q, bank, h, expected, near, seed=seed)
            write_atomic(a.out / f'seed-{seed}.json', row)
            rows.append(row)
        except Exception as exc:
            # A process SIGKILL cannot write this, but prior seed files survive.
            write_atomic(a.out / f'failed-seed-{seed}.json',
                         {"seed": seed, "error_type": type(exc).__name__,
                          "utc": datetime.now(timezone.utc).isoformat()})
            raise
    audit_rows(rows)
    result = dict(binding, rows=rows, verdict=verdict(rows))
    digest = write_atomic(a.out / 'report.json', result)
    print(json.dumps({"verdict": result['verdict'], "report_sha256": digest, "rows": len(rows)}))


if __name__ == '__main__': main()
