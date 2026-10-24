# V13 WP-LP3 — pinned preflight hardening (2026-10-24)

**Ownership:** Codex isolated LP3 candidate + new preflight tests only. No edits to frozen production runtime, Claude-owned packages, Canon, ROADMAP, or the original LP3 preregistration. Base: PR #43 at `f6772ef3071ca30a3461fae4f265e6012f6563b4`; PR #42 and Claude PR #38 unchanged. This is a review candidate, not a native run.

## Confirmed review finding

The original LP3 CLI accepted *any* caller-supplied 64-hex weight SHA and checked only `model.safetensors`; a different weight file could therefore pass by supplying its own hash. It also did not hash-bind `lora_bench.py`, the transitive source of the first eight facts, or the tokenizer/chat template/config/license. Consequently, the previous run manifest could not distinguish changed tokenization or changed inherited fixtures. The original CLI also wrote its manifest before verifying the full snapshot. None of these findings changes LP2's recorded result or invalidates a real LP3 result (none exists).

## Changes (isolated, OFF by default)

- Enforce the exact historical LP1/LP2 HF weight SHA-256 `1c9c77a4471a7f590f85240f74ed1fc26df7fbde88c3006724e2f93ca993ea4e`. No arbitrary master cohort accepted.
- Before any evidence directory is created, verify existence, nonzero bytes, and hash all seven files in the pinned `LiquidAI/LFM2.5-350M@55e5a53e8637c4522a0577040fe68682db3fbbb6` snapshot: model.safetensors, config.json, generation_config.json, tokenizer.json, tokenizer_config.json, chat_template.jinja, LICENSE. JSON assets must parse to objects.
- Bind both `lp2_assignment_objective.py` and its inherited fixture dependency `lora_bench.py` by SHA-256 in the run manifest. The master, code and fixture binding now occurs before manifest publication. Refuse nonempty output directories rather than silently overwrite or resume a partial cohort.
- Explicit limit: the nonweight assets are **content-bound local bytes, not independently upstream-authenticated**; the manifest says `NOT_INDEPENDENTLY_VERIFIED`. The upstream revision string is provenance metadata, not proof that all local files match that revision.
- This does not change predictor, retrieval, scores, original LP3 thresholds, native training, runtime authority, or any V13 gate.

## Verification / evidence level

Command: `cd v13/code && python -m unittest discover -s tests -p 'test_lp3*.py' -v` in a standalone LP3 package with a lightweight LP2 fixture stub; `python -m compileall -q scripts/lp3_memory_key_candidate.py tests/test_lp3_preflight_binding.py`.

**17/17 PASS**, 0 failures, 0 errors; compileall PASS. The first attempt had 2 test-harness failures because the subprocess fixture stub was absent from `PYTHONPATH`; repaired the test setup and reran all 17. This is a **Linux/Python software + synthetic-fixture proof only**; no HF master was loaded and no real native or Redmi execution occurred. Raw final test output: `docs/proofs/continuation-20261024/lp3-preflight/software-tests.log` (SHA-256 `8c65436a1a7c86085a5c70d395458f94e8d2883e0fdd16da87e1a19b06f22569`).

Source SHA-256: LP3 script `82d315ca9f6652e062870cc9abf82d586db7ddcdac37c812592116bf14a639c6`; new tests `d95d0429d00c03cd02cacd625cb409a965441062b92b5ab9d4e8d9d2077418f0`. Git blobs are checked after publishing.

## Current native prerequisites (checked in this execution environment)

`/home/oai/.cache/huggingface/hub/models--LiquidAI--LFM2.5-350M`, `/mnt/data/models` and `/mnt/data/v13/code/models` were absent; no matching heavy native process was seen. Current container memory cgroup is **4294967296 bytes (4 GiB)**, not the historical 8 GiB. This observation does not assert that another worker's cache or ownership is absent; recheck on the actual native host before a run.

## Research provenance

Official model snapshot listing (accessed 2026-10-24): https://huggingface.co/LiquidAI/LFM2.5-350M/tree/55e5a53e8637c4522a0577040fe68682db3fbbb6 — confirms seven expected files and `lfm1.0` license identifier. No external code or model weights copied. Earlier project feasibility: `docs/coordination/LP3_FEASIBILITY_20261024.md` supplies the weight hash and LP2 source provenance. A later `main` template differs, so never silently substitute it.

## Unresolved / exact next step

**HARD_BLOCKER:** independent full-repository suite and `public_repo_privacy_scan.py` require a full checkout; this environment has only connector access plus the small candidate ZIP. Native LP3 additionally needs the exact pinned HF snapshot, dependency versions and exclusive job ownership verified on the native host. The original LP3 `audit_rows` recomputes aggregates but is not a cryptographic proof against consistent edits to both raw predictions and aggregates; a separate immutable receipt / external Git blob binding is still required before interpreting a native cohort.

**Next:** independent checkout review + privacy scan, then verify all seven pinned assets and native ownership, preregistered four-seed run, immutable per-seed hashes and raw row audit. A positive memory-key result is not a generated-answer JEPA result.

**Gates unchanged:** STEP2 `UTILITY_FAIL`; B3 L1 `FAIL`; `jepa_weight=0`; native Body-JEPA `UNAVAILABLE`; Redmi `NOT_RUN`; `canonical_architecture_complete=false`; `user_full_scope_complete=false`. **USER_DECISION_REQUIRED: none.**
