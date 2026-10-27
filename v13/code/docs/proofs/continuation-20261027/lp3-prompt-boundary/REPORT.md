# Independent LP3 prompt-state boundary review — 2026-10-27

**Scope:** review-only child of PR #726 exact `4b8a2fa7dbbbb88ac11c5314ae28635d45c6222d`; no change to registered LP1/LP2/BP2b cohorts or live V13 runtime. Owner: this isolated review branch. Source/test files are `v13/code/v13/lp3_state_prefix.py` and `v13/code/tests/test_lp3_state_prefix.py`.

## Source review findings and changes

1. **Untrusted feature injection:** the original public `answer_logits(..., features=...)` and `next_token_logits(..., features=...)` accepted any finite same-shape tensor. A caller could derive it from target answers, bypassing the claimed prompt-only state boundary. The review rejects supplied features unless they are exactly the detached frozen state recomputed from the same prompt. Internal calls compute prompt state only once. This is an API containment guard, **not** a claim that all downstream data are leak-free.
2. **Decoder context overrun:** teacher-forced and target-free calls did not preflight soft-prefix + prompt + answer length against `max_position_embeddings`. Both now fail closed with `ValueError` before invoking the frozen decoder.
3. **Prompt validation bypass:** `prompt_features` previously omitted empty-batch, vocabulary and context validation. It now uses the common prompt validator.
4. **Wrong-assignment invalid control:** `shift` previously allowed a batch of identical prompts. The control now requires at least two distinct prompts.

Three new synthetic counterexample tests cover supplied answer-dependent features, invalid prompt/context, and degenerate shift. Existing gradient/frozen-base/causal-alignment tests remain. No model downloads are required by the tiny GPT2 fixture.

## Evidence boundary

Review workflow: `.github/workflows/lp3-prompt-boundary-review.yml`, isolated CPU Torch 2.14.1 / Transformers 5.20.2, `python -m unittest -v tests.test_lp3_state_prefix`, `py_compile`, privacy scan and `git diff --check` against exact parent. **Workflow result must be read from the exact GitHub Actions run; no local transformer or Redmi/native model run is claimed.** At report creation the run was pending. Source and test bytes are remote Git objects on the review branch; no private data or optimizer/model bytes uploaded.

## Unchanged gates and next step

LP1 NO_ATTRIBUTABLE_GAIN; LP2 ALIGNS_NO_GAIN; BJ1 NO_SIGNAL; STEP2 UTILITY_FAIL; B3 L1 FAIL; registered `jepa_weight=0`; Age authority 0; Redmi unmeasured; V13 incomplete. No deployment, learned utility, JEPA proof or Age promotion. Next: verify exact-head CI, inspect any failure and repair on this branch; independent review; then separate preregistered real-model LP3 utility experiment only after active BP2b native ownership clears. Do not merge review branches into main without integration review.
