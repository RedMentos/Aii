# LP3 shifted-control row identity — preregistration 2026-10-28

Independent C3/LP3 SHADOW research review branch, based on PR #809 verified head `4bd69282647d260efe815b6f57b72ed675fef588` (Actions `40610977438` SUCCESS). Own only `v13/code/v13/lp3_state_prefix.py`, new tests, branch-scoped workflow and this evidence note. Separate from HX1 review and A1 PR #810; no production merge.

## Failure hypothesis and precommitted checks

`StateConditionedPrefix._prefix_for(..., assignment='shift')` currently rejects an entirely identical prompt batch but permits repeated prompts where a row receives **its own prompt's state** after `roll(1)`. Example three-row `[A, A, B]`: shifted row 1 receives A from row 0, so a supposed wrong-source control includes an own-source row. Likewise `[A, B, A]` leaks row 0's own state from row 2. This contaminates causal attribution of the LP3 state-conditioned answer consumer.

RED test: both mixed batches must fail closed before producing logits in teacher-forced and target-free paths, while `[A, B, C]` and `[A, B]` remain valid shifted controls. No model downloads; use the existing tiny synthetic GPT2 setup. GREEN source fix: require each row to differ from its **immediate rolled predecessor**, not just require some difference somewhere in the batch. Do not change the assignment permutation, training objectives, seeds, registered cohorts or native artifacts.

Run focused and complete Linux software tests, compile, privacy/diff checks; archive original RED raw logs and GREEN ZIP with SHA256 and private backup. This is control validity only, not improved model utility or a learned C3 consumer. STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, LP1 NO_ATTRIBUTABLE_GAIN, LP2 ALIGNS_NO_GAIN, LP3 heldout 0/12, jepa_weight=0, Age0/RECORD_ONLY, no Redmi evidence, V13 incomplete.
