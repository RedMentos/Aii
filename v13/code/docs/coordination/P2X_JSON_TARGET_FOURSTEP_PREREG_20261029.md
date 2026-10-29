# P2X C3 JSON-target consistency pilot — preregistration (2026-10-29)

## Narrow hypothesis and frozen comparator
- Existing four-step pilot trains C3 on bare label targets `A<|im_end|>` / `B<|im_end|>` / `NONE<|im_end|>` / `UNKNOWN<|im_end|>`, while pinned llama-server evaluation constrains the first generated token to a JSON object with schema `{"action": "A|B|NONE|UNKNOWN"}`. This **format mismatch is verified in source** (`LoraTrainer._encode`, `p2x_c3_receiver_fourstep`, `hb1a_two_body_native_pilot.C3_SCHEMA`); whether it causes constant-NONE is an **unproven hypothesis**.
- Base exact review head `4f80f88920678ea1aad3a50550b4bc73ea1d80c5` (PR #1100 descendant with P2X CAL36 software integration). New review-only child; do not edit any original trainer, fixture, model, adapter, seed or donor branch. Existing 16×4 native adapter and 360/72-call negative evidence remain immutable.
- New experiment uses the same original **frozen 16 training examples**, same four labels (4 each), same QAD FP32 source, same `rank=2, alpha=4, lr=.0003, steps=4, seed=2026102924`, same target modules, but changes **only the supervised target serialization** to compact `{"action":"LABEL"}<|im_end|>`. This is a new adapter artifact, not an overwrite.
- The frozen training cohort `cd3edfdb464c6f99650b1ea32b5b09854268f0b53faa79df22ddcd135f21985a`, `train.jsonl` `af191c087d872a42924f2d2d465a3f26f6c323bf48c5c0682b30094b9d666cf1`, model source `1d90518482c4ec204bebb4820bbaee4f8a38c5a6df72256f86bcd21fe52ad079`, and all other registered pins are unchanged. Validation inputs/answers are checked for exclusion, never trained on or inspected for tuning.

## Prospective tests and claim limits
1. Source-only exact balanced selection, schema-valid compact target, no answer leakage into prompts, tokenizer measurement matching `LoraTrainer._encode`, target length <=512. RED on invalid labels/overlength.
2. Isolated pinned Linux-native four-step QAD FP32 LoRA run if no concurrent heavy owner. Require finite loss, 4/4 actual steps, source/adapter hashes, original raw receipts and independent offline artifact audit; preserve failure.
3. Optional separate *training-only in-sample* inference can diagnose whether new adapter emits different JSON actions. It cannot establish heldout/generalization/source-sensitive utility. **Do not evaluate on previously inspected CAL36 or frozen 72 validation tasks in this package.**
4. Do not alter production model registration, AG6 approval, Age0 RECORD_ONLY, jepa_weight0, STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, LP3 FAIL, Redmi UNMEASURED or V13 INCOMPLETE.
5. Privacy scan and exact-source hash gates. No paid provisioning, no private data, no force push.

## Ownership and next
Only new `scripts/p2x_c3_json_target_fourstep.py`, `scripts/p2x_json_target_evidence_audit.py`, `tests/test_p2x_json_target_fourstep_20261029.py`, dedicated workflow, and this prereg/handoff. No mutation to the donor owner files.
Next: implement source-only tests, run focused RED/GREEN and then native training only after source pins and resource/owner checks.
