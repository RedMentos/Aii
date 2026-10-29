# P2X candidate360 corrected LoRA argv — independent raw artifact audit

**Date:** 2026-10-29 UTC. **Scope:** review-only, no model execution or production merge. This note is a child of PR #1093 exact source head `6cf8a19ead783ec12461edbe54230a8d94fe3ac1`; original native owner branch remains untouched.

## Artifact acquisition and integrity

- GitHub Actions run: `40876846850` (native job `123457740627`), workflow conclusion `success`, original public artifact ID `12898288641`.
- Downloaded artifact ZIP independently using the GitHub artifact endpoint; byte size **49,350**. Local ZIP SHA256 **`c1b23dfe9af76fdfdddcc52808447e97091e38e645ad54722babad460ae36720`**, exactly matches the SHA256 printed by the original GitHub Actions artifact-upload step.
- ZIP CRC check: clean. Original `SHA256SUMS`: **56/56** declared member hashes match the extracted member bytes. `HEAD.txt` exactly matches `6cf8a19ead783ec12461edbe54230a8d94fe3ac1`.
- Original `SOURCE_EXIT`, `COHORT_EXIT`, `NATIVE_EXIT`, `VERIFY_EXIT` are all `0`. The receipt's five payload SHA256 values match the actual `RAW.json`, `INPUTS.json`, `ANSWERS.json`, `SCORE.json` and `PAIRED.json` bytes. No raw failures discarded.
- Receipt states `recorded_calls=360`, `expected_calls=360`, `process_reaped=true`, `weight_updates=false`, `production_activation=false`, `ag6_approved=false`, `redmi_measured=false`. All 360 raw entries declare `FINAL` and one model call each. Model/binary/adapter hashes are recorded in the receipt; this audit verifies their internal consistency, **not** the external model binary bytes.

## Independent counts from raw outputs and sealed answer key

- **72** unique tasks; oracle distribution: **24 A / 24 B / 24 NONE**. Five arms, **72 rows each**, **360 actual recorded responses**.
- Across all 360 native outputs, **348** are `{"action": "NONE"}` and **12** are the spacing variant `{ "action": "NONE"}`. There is **no predicted A or B** in the raw output.
- C3-only: **0/72** exact, **72** wrong committed. B1-only: **0/72** exact, **72** wrong committed. B2-only: **0/72** exact, **72** wrong committed. Shuffled: **0/72** exact, **72** wrong committed. Both-exact: **24/72** exact, **48** wrong committed; its 24 exact cases are precisely the oracle NONE cases.
- Sealed `PAIRED.json`: `base_exact_both=24`, `candidate_exact_both=24`, **`both_exact_delta=0`**; `foreign_wrong_committed_base=72`, `foreign_wrong_committed_candidate=72`.
- The score and verifier report `P2X_NATIVE_RECEIVER_DIAGNOSTIC_NO_GATE` / `VERIFIED_CANDIDATE360_NO_GATE`. GitHub workflow success means the diagnostic completed and integrity checks passed; it does **not** mean learned semantic utility passed.

## Independent baseline ZIP cross-check

The pinned base artifact `12890306165` was independently downloaded too: **103,879 bytes**, ZIP SHA256 `43e8dcc71370cf17355d4cd0bbc4f9aaa1378ead648a1de3425edf333b082d93`, matching the hash explicitly pinned in the native candidate workflow. CRC clean; **34/34** internal SHA256SUMS match.

Base and candidate `ANSWERS.json` bytes are identical, `INPUTS.json` bytes are identical, and the same **360** `(task_id, arm)` pairs occur. Baseline output distribution: **352** standard `NONE`, **6** spacing-variant `NONE`, **2** `B` (both in the shuffled arm). Candidate: **348** standard `NONE`, **12** spacing-variant `NONE`, **0** `B`. Exactly **20/360** raw output strings changed, mostly JSON whitespace; no change in both-exact semantic choice. This independently confirms `both_exact_delta=0` from the original raw baseline/candidate outputs, rather than merely trusting `PAIRED.json`.

## Interpretation and exact next work

The corrected `--lora-scaled FNAME:SCALE` argv repair restored actual 360-call native execution after the earlier zero-call failure. The model's action outputs, however, collapsed to **NONE** across every arm. There is **no measured gain** over the recorded base control, no evidence of source-sensitive action selection, and no basis for promoting STEP2 or the LoRA/JEPA learning path.

**Next independent research:** check the actual native request/response schema and decoding/token limits against the pinned server, and use a preregistered *fresh* disjoint set with positive A/B controls and negative NONE controls to isolate whether the constant-NONE behavior is a prompt/transport/schema mismatch, model response limitation or adapter issue. Do not tune on the heldout cohort, overwrite it, or dispatch a concurrent native run while another owner is active.

**Negative gates unchanged:** Age0 RECORD_ONLY; STEP2 UTILITY_FAIL; B3 L1 FAIL; Body-JEPA UNAVAILABLE; `jepa_weight=0`; no Redmi measurement; V13 incomplete. No private raw ZIP is republished here. This public review note records only hashes, counts and claim limits.
