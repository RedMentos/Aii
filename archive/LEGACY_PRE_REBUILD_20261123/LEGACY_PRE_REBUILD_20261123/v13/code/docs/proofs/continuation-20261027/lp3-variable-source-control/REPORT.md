# LP3 variable-length explicit wrong-source control — 2026-10-27

Review-only child of verified real C3 compatibility PR #731 exact `aeefa413fdcb06252ac280493539371a208eb3d5`. Source-only experimental extension, not a new real-model/utility cohort. Design specified first in `DESIGN.md`, then `v13/lp3_state_prefix.py` adds `answer_logits_from_source`, `answer_loss_from_source`, `next_token_logits_from_source`, and `greedy_from_source`.

The frozen source state is extracted **only from explicit `source_prompt_ids`**; no arbitrary `features=` override or answer token input. Target/source may have different sequence lengths, with same batch/device; identical source/target and invalid token/context/shape are rejected. Both predictor and projector receive CE gradient; frozen base remains unchanged. This makes it possible to preregister a wrong-fact source control on variable-length heldout prompts without padding or weakening the earlier prompt-only feature guard. **It does not itself prove that a caller's chosen source prompt is answer-independent; future dataset provenance audit is required.**

Two new GPT2 synthetic tests cover variable-length source effects on answer and next-token logits, CE gradient, bounded target-free greedy and fail-closed invalid source controls. Existing 12 synthetic tests remain. Isolated CPU CI `.github/workflows/lp3-variable-source-control-review.yml` **pending** at report creation. No native model job, no utility measurement or Age promotion. LP1/LP2, BJ1, STEP2, B3 negative gates, `jepa_weight=0` and Redmi unmeasured unchanged.

Next: verify exact-head synthetic CI and independent review; then preregister a matched real-model CE/own/wrong-source utility study with new harder heldout prompts, source provenance, leakage, retention and drift acceptance gates. Do not merge directly to main.


## Focused software result

Actions **40525062343**, exact source commit `8a3c406d2e3998049587c2f7b37b4fb96a9ebf86`: **14/14 synthetic tests PASS**, Python compile PASS, privacy CLEAN and diff check PASS. This includes both new variable-length source tests and all 12 inherited LP3 tests. No real-model or heldout utility run was performed on this branch. Final metadata-head recheck pending; all gates remain unchanged.
