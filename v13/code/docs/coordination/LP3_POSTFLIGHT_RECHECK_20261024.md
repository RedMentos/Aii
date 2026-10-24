# WP-LP3 Run 11 — postflight source/snapshot integrity (2026-10-24)

Base: `codex/lp3-audit-hardening-20261024` PR #46 at `1aa73471c0fe07c4b166a3d14b5cd0aa9fea9162`. Canon remains `V13_v10.16.1_WORK_HANDOFF_SINGLE_SOURCE_B3_HARDENED.md`, subject to explicit newer user decisions. Remote heads/open PRs rechecked; no newer Claude integration PR than #38 as of inspection. File ownership is limited to LP3 candidate, LP3 auditor, their LP3 tests, and new scoped notes/proofs. Frozen V13 production runtime, canon, original LP3 preregistration, live cohort and other owners untouched.

## Confirmed integrity gap

PR #44 hashes seven HF snapshot assets and both source fixtures *before* the run. It then loads model/tokenizer and trains four seeds without checking that the cache, fixture source and candidate source still match the initial hashes when publishing `report.json`. A mutable cache/symlink target could therefore yield an apparently closed report whose initial manifest no longer describes the inputs. This is a provenance/integrity gap, not evidence of actual exploitation.

## Change

- `verify_postflight_binding()` rehashes all seven assets and two fixture dependencies via the existing pinned preflight, plus the candidate source SHA, after all seeds and before `report.json` publication. Numerical protocol, training arms, seeds, metrics, model, and thresholds unchanged.
- If recheck fails, preserve already written seed JSON and manifest, write a durable `failed-input-binding.json` marker and refuse the final report. No auto-resume or gate promotion.
- Independent LP3 closed-evidence auditor now rejects all `failed-*` attempt markers, including postflight failure. Prior `failed-seed-*` rejection retained.
- Unit tests cover changed weight, tokenizer, transitive fixture, candidate source, symlink retarget, unchanged input, failure and success publication paths, and failed-marker audit.

## Evidence and limits

- Original focused baseline: 43/43 PASS (Run 10 state).
- First modified attempt: 50 tests, 1 failure because the new generalized marker error string broke an inherited regex. Fixed without weakening the rejection; log preserved locally.
- First synthetic lifecycle attempt: 52 tests, 2 errors from missing fake fixture dependency hash. Fixed synthetic test setup; failure reproduced in a separate log and preserved locally.
- Final: **52/52 focused software/synthetic tests PASS**; `compileall` PASS. No native model inference, no Redmi measurement. Full repository suite/privacy scanner not run (no complete checkout; local git DNS unavailable).
- Host prerequisites freshly checked: cgroup memory.max=4294967296, torch 2.10.0+cpu present, transformers absent, pinned 350M master/tokenizer absent in checked paths, no LP3 heavy process in local process list. Other hosts not inferred.
- This postflight check is not a guarantee against an adversary swapping bytes *during* model load and restoring them before the recheck; it is a before/after consistency check. A fully immutable content-addressed snapshot or file-descriptor-pinned loader remains a distinct future hardening option, not silently claimed.

## Research/provenance

- Hugging Face official revision: https://huggingface.co/LiquidAI/LFM2.5-350M/tree/55e5a53e8637c4522a0577040fe68682db3fbbb6 (model license `lfm1.0`, not assumed permissive).
- Official HF Hub API docs: https://huggingface.co/docs/huggingface_hub/main/en/package_reference/hf_api — `RepoSibling` metadata distinguishes git blob ID from LFS SHA256. Local hashes alone do not establish upstream authenticity. No third-party code copied or dependencies added.
- GitHub: https://github.com/RedMentos/Aii/pull/46 — upstream closed-evidence auditor. Source/fixture hash checks are protocol-consistency evidence, not independent native reproduction.

## Gates and next

STEP2 `UTILITY_FAIL`, B3 L1 `FAIL`, Body-JEPA `UNAVAILABLE`, `jepa_weight=0`, full V13 `INCOMPLETE`, Redmi `NOT_RUN`. LP3 native four-seed cohort `NOT_RUN`. Next: independent full-checkout review/privacy scan, verify exact pinned native assets and exclusive heavy-job owner, run preregistered LP3 seeds serially on suitable host, audit and externally anchor receipt, then separate equal-budget generated-answer causal comparison. No USER_DECISION_REQUIRED. Rejected anyone-writable Drive destination not retried.
