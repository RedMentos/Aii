# Run71 exact-blob cross-package JEF/C3/C5/C6 integration prereg (2026-10-31)

**Owner:** GPT-6 continuation, new isolated review-only branch `assistant/v13-run71-c3-crosspackage-integration-20261031-run11`. Exact parent Run70 PR #1430 HEAD `07b5227655528627262736ae91844d5cd3767cf8` (scientific SOURCE_SCHEMA 3/6 RED, typed 6/6). Do not rewrite original Run70 native source, model, seed743, scorer or RED. Canon blob `218464b12a2d27d92524c751922fa8e1c3fb0ea7` unchanged.

## Exact donor imports, no edits
Donor A: our Run11 PR #1429 HEAD `875ee06cab98357ba36d8dd0fb0fa789d6547159`, from same Run68 parent. Import exact Git blobs:
- `v13/code/v13/jef_c3_schema_draft_candidate.py` `ee976c0329ad751b4851862680e6fe6f9ee66e82`
- `v13/code/scripts/jef_c3_c5_c6_operator_cli.py` `25ad2234b353b58ad06bcc505b6ca05f527c0add`
- `v13/code/tests/test_jef_c3_schema_draft_candidate.py` `9b11075e2f7820ea0f571226fed6dcbd0ab145ed`
- prereg `v13/code/docs/JEF_C3_SCHEMA_DRAFT_GUARD_PREREG_20261031.md` `fb393a7f7ed2952137621c9f4cfa87a79b76dbab`.

Donor B: independently developed Run69 `codex/jef-c3-schema-source-recheck-adapter-20261031-auto11` HEAD `7ca690548ef7f077779efdd83f8af8ab452f385a`, exact Git blobs:
- `v13/code/v13/jef_c3_schema_source_recheck_shadow.py` `18aaaa86f416a1df9a703b86b9d12215ad1c00c5`
- `v13/code/tests/test_jef_c3_schema_source_recheck_shadow.py` `c47a6ea2ef47e01b43c6320c60de1280e33607bf`
- original plan `v13/code/docs/JEF_C3_SCHEMA_SOURCE_RECHECK_ADAPTER_PLAN_20261031.md` `fc80a53eb78ca831bc064d5e38d1059dd5a8d9b5`.

No other file changes or merge from another owner's branch. Donor B remains a **read-only** formatter diagnostic, Donor A a **default-OFF Store DRAFT** path; they must remain distinct and cannot be automatically interchanged or promoted. Run70 source-only RED is immutable. This is software compatibility only, not new native proof.

## Prospective checks
1. Verify exact imported Git blob SHAs, unchanged Run70 fixture/runner/scorer and Canon. Fail if source path conflict or source hash mismatch.
2. Run **all five** focused suites on the *combined source*: Run69 schema source-recheck, Run11 schema DRAFT, Run11 legacy CLI, Run70 fixture/no-answer-leak, Run70 independent verifier/tamper. No skipped tests, no waivers. Pin deps, source HEAD, compile, privacy, diff. Retain original full logs, exits and SHA256SUMS even if RED.
3. Cross-package assertion: the two adapters are separate, default-OFF, source verified, no native model claim, no live output/tool/learning; Run70 source-only model prompt still has no typed action. No queued Sleep or real TTY.
4. If all software GREEN, open **draft** integration PR targeting Run70 branch; do not merge donor PRs or main. If RED, preserve original and repair only integration-specific code in new branch, never rewrite frozen cohorts.

## Negative gates
Age0 RECORD_ONLY, STEP2 UTILITY_FAIL, B3 NO_PROMOTION, Body-JEPA UNAVAILABLE, World-JEPA SHADOW, jepa_weight=0, Redmi unmeasured, historical unfiltered 4 FAIL/66 ERROR/28 SKIP, whole V13 incomplete. The Run70 scientific RED remains 3/6 source-only and cannot be erased by this integration.
