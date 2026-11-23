# P2X-CAL36 — preregistration before implementation (2026-10-29)

## Provenance and owner
- Independent review-only child of PR #1093, exact parent commit `6cf8a19ead783ec12461edbe54230a8d94fe3ac1`. Owner: codex/v13-p2x-cal36-transport-20261029. No changes to the parent branch.
- Existing frozen P2X fixture generator: `scripts/p2x_disjoint_receiver_trainset.py`, schema `v13.p2x.disjoint_receiver_trainset.v1`, seed 2026102921, expected canonical fixture SHA256 `cd3edfdb464c6f99650b1ea32b5b09854268f0b53faa79df22ddcd135f21985a`.
- Pinned C3 model SHA256 `3d10b6ab8fc91a919534b9558e266255aca0bbc7f6d015963599aa9e74e05b1d`, runtime archive SHA256 `9abf88aea48a55d0f80edb1ee20220b186848cca0b4e919d71518cfd7ca67443`, original candidate adapter SHA256 `062c20d796c59169579529f4a069f77693a847123f599d00f374bd01a8618e92`, pinned llama-server binary SHA256 `79e312188dc1d75c28201771f106e91de470b5cebdd838d31bb4db25eecf5d39`. Runtime uses existing QAD+LoRA path and scorer seed 13. No model, source, cohort or seed substitutions.
- Prior held-out result: PR #1096 independently audited 360 candidate calls; all selected NONE, both_exact 24/72 vs baseline 24/72 (delta 0). This observation motivated this diagnostic but **the 72 held-out validation tasks are excluded from this experiment**.

## Question and hypotheses
Does the candidate C3 LoRA path produce any source-conditioned positive A/B decisions when tested on the **already registered, disjoint calibration partition** rather than on the held-out validation partition?

H0: positive A/B decisions remain absent or source-independent. H1: the model chooses the correct A/B for a nonzero number of the 24 positive calibration rows *and* abstains in the corresponding C3-only negative arm. This is diagnostic evidence only, not STEP2 utility.

## Frozen sample, prompts and arms
- Select exactly 36 fixture rows where `partition == "calibration"`, sorted by immutable ID; expected 12 A, 12 B, 12 NONE. Do not use the 252 training or 72 validation rows.
- Two arms per row in this exact order: `both_exact` (same B2 policy and B1 option sheet, with current request) and `c3_only` (current request only). 72 calls total, no human-supplied extra hints, no label examples, no oracle or target in model input.
- Use the existing pinned `p2x_candidate360_standalone.LocalServer` and its fixed `--lora-scaled FNAME:SCALE` argv; same `/apply-template`, `/tokenize`, `/completion`, JSON schema, decode parameters, seed, token and context budgets as parent. Run a single owned loopback server. No alternate prompt format or runtime tuning.
- No native execution until resource owner and serialization are checked. First implement source-only tests with mocked server and a strict offline verifier. A native run, if subsequently authorized and possible, must persist every original raw call and failure, exact input/model/adapter/runtime/binary hashes, output, duration, receipt and deterministic score; no overwrite of an output directory.

## Primary metrics and interpretation (no posthoc gate change)
- `positive_correct`: exact A/B in the 24 both_exact positive rows, range 0–24.
- `negative_abstained`: UNKNOWN on 36 C3-only rows, range 0–36.
- `paired_source_sensitive`: positive A/B both_exact correct **and** same-row C3-only UNKNOWN, range 0–24.
- `none_correct`: NONE on the 12 both_exact NONE rows.
- `wrong_committed`, `unknown`, `unparseable` separately for both arms. A wrong NONE on an A/B row is a wrong commitment, not success.
- If `positive_correct == 0`, reject the hypothesis of positive A/B transport on this calibration. If `paired_source_sensitive == 0`, reject source-dependence evidence even if some A/B are guessed. If either is positive, it motivates a separately preregistered native comparison but **does not** promote STEP2, JEPA, B3 or AG6.
- No repeated runs/tuning against calibration results without a new preregistration and disjoint data. No analysis may treat the calibration set as an unseen held-out validation set.

## Safety, negative gates, next step
Age0 RECORD_ONLY, STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, jepa_weight=0, AG6 unapproved, Redmi unmeasured, V13 incomplete. Runner is isolated from Runtime Store, no adapter registration, no learning, no write tools. Raw artifacts may contain prompt text and stay in approved private storage; public git contains only code, synthetic tests, hashes, non-sensitive aggregate results and handoff. Preserve original failed attempts and immutable source pins.

Success for this package: deterministic 72-row source-only plan, fail-closed offline score/verify, mocked 72-call persistence/restart/failure tests, source-only CI, exact-head remote verification and explicit handoff. Next substantive step after source verification is **one** serialized pinned Linux-native CAL36 execution and independent raw audit, if a resource owner is available. No gate promotion from source-only work.
