# Run11 bilingual arithmetic heldout operator guide — candidate only

**Scope:** independent, public 16-question Age0 Linux native candidate measurement. This is not an installation guide for a production user home and not permission to change the original V13 blueprint. The baseline arm must be run separately from the exact baseline prompt source.

## Prerequisites

Run only on a fresh, isolated Linux x86_64 runner with enough free disk for the pinned current model catalog and no concurrent native model owner. Use the exact Git commit and pinned model/source hashes recorded in the review PR. The 16-row fixture is frozen at Git blob `ceda0a5cb506cf09885652b24893cf7d8fdff63b`. The candidate prompt Git blob is `646c6f31b52ca2664c1952af7c7e842fc3e20885`. Do not edit these bytes or swap models to make a run pass.

The collector **rejects an existing chat database**. Never pass your regular V13 home. Create a fresh scratch home for this cohort, not a reused test home.

## Exact sequence (from repository root)

```bash
set -euo pipefail
python3 -m venv /tmp/v13-heldout-venv
PY=/tmp/v13-heldout-venv/bin/python
"$PY" -m pip install --no-input 'numpy==2.2.6' psutil PyYAML Pillow 'prompt-toolkit==3.0.52'
export V13_NO_AUTOSTART=1
export OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=1
export V13_HOME=/tmp/v13-heldout-candidate-fresh-home
export EVIDENCE=/tmp/v13-heldout-candidate-evidence
test ! -e "$V13_HOME"
test ! -e "$EVIDENCE"
PYTHONPATH=v13/code "$PY" -m v13.bootstrap --home "$V13_HOME"
PYTHONPATH=v13/code "$PY" -m scripts.age0_bilingual_arith_native_collector \
  --home "$V13_HOME" --out "$EVIDENCE" \
  --prompt-git-blob 646c6f31b52ca2664c1952af7c7e842fc3e20885 \
  --seconds-per-turn 120
(cd "$EVIDENCE" && find . -type f ! -name SHA256SUMS.txt -print0 | sort -z | xargs -0 sha256sum > SHA256SUMS.txt)
```

A workflow must wrap these commands in hard timeouts and preserve **both** nonzero exit codes and raw partial evidence. `RAW_ROWS.jsonl` is append-only and fsynced after every turn. `ANSWERS.json` and `SCORE.json` exist only after all 16 rows are captured and validated. `CAPTURE_RESULT.json` is a native *candidate report*; independent review must still verify the source, actual runner hashes, artifact ZIP digest, and raw per-row status. Never include GGUF weights, native binaries or private chats in the evidence archive.

## Reading results

`SCORE.json` reports strict numeric lexical proxies and unsupported-answer uncertainty markers, **not** semantic correctness or non-hallucination. A failure, timeout, missing final answer, unexpected model role, tool execution or drifted source is RED. Do not replace missing rows with generated data. The scorer cannot verify a manifest's self-reported source/model hashes; the collector's preflight, actual per-row file hashes and independently inspected raw artifacts are essential.

For baseline comparison, create a separate fresh scratch home at the frozen baseline prompt source `a74d7517a7ab70e801e177b58da057e57fd3460c`. Only after both native runs are independently verified, run:

```bash
PYTHONPATH=v13/code "$PY" -m scripts.age0_bilingual_arith_scorer \
  --answers /path/to/candidate/ANSWERS.json \
  --compare /path/to/baseline/ANSWERS.json \
  --out /path/to/new/PAIRED_SCORE.json
```

If routes differ, inspect `paired_route_changed_ids` rather than claiming a pure prompt-only causal effect. New chat sessions share one scratch brain and do **not** prove total global-state independence. Negative gates remain: STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, LP3 heldout FAIL, jepa_weight0, Age0 RECORD_ONLY; no Redmi or whole-system acceptance.
