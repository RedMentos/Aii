# WP-BP2b complete source-manifest binding — software RED/GREEN closed, 2026-10-27

**Parent:** PR #709 exact `b6ad3d025a8f93cbafd9bca97d2e9e5a657b83c5` (review-only). **Owner:** GPT-6 independent branch `assistant/v13-bp2b-manifest-binding-20261027`. No production merge or native run.

## Defect and repair

The one-arm native runner checked only `model_facing_sha256` after `prepare()`. A changed training source hash, scoring-only hash or selected-index order could pass into a `COMPLETED` attempt while its `plan` still attested the original cohort. Added `scoring_only_sha256` to the plan and fail-closed comparison of **seed, source SHA, heldout SHA, model-facing SHA, scoring-only SHA, train SHA, selected indices, heldout count, age_authority and jepa_weight** before attempt directory creation. Original cohort, 4 arms × 3 seeds, pinned model and tokenizer hashes remain unchanged.

## RED and GREEN evidence (original raw ZIPs independently verified)

- RED Actions `40504901468`, exact head `20abddfaf62f9daf4fd6315b706431702b9adb8b`: **20 tests, 3 expected failures** (train hash, scoring-only hash, selected-index order); dry-run, compile and privacy exit 0/CLEAN. Original artifact ID `12733809462`; SHA256 `605cda2cf856b7daff0ea094df7365e119cb1eea0ce51fcce085ecdc0da01fb8`, ZIP CRC PASS.
- GREEN Actions `40504938622`, exact head `b3968a498caafb3fa99171f20680ce33b4d5e05b`: **20/20 software tests PASS**, dry-run, compile and privacy exit 0/CLEAN. Original artifact ID `12734372398`; SHA256 `d5b6d33cbdfd7c1a04bd4ddd7e42eefc15c282eb367896d4b0f5a91245964a22`, ZIP CRC PASS.
- Original raw ZIPs privately backed up to ChatGPT Library `/V13-Checkpoints/2026-10-27/BP2b-Manifest-Binding/`, re-materialized and compared byte-exact to the original downloaded ZIPs, both PASS. No anyone-writable Drive used.

**Evidence class:** software/synthetic only; no model download or native training. STEP2 UTILITY_FAIL, B3 L1 FAIL, BJ1_NO_SIGNAL, jepa_weight=0, Redmi unmeasured and V13 incomplete. No Age, tool, route or learning promotion.

**Next command:** `cd v13/code && PYTHONPATH=. python -m unittest -v tests.test_bp2b_native_runner tests.test_bp2b_transfer_score`. Next substantive path: retrieve/stream-hash the exact public master and seven metadata files in isolated preflight, then check heavy owner and run one registered native FP32 arm; Q4 and Redmi remain separate.
