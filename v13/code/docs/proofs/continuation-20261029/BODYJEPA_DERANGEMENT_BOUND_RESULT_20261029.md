# V13 Body-JEPA bounded derangement negative-control result (2026-10-29)

## Source and scope
- Review-only PR #1153, parent `e5e054c7059181952ff2919789c2652e7ce97c45` from PR #1152; no production merge or registered cohort/model/seed rewrite.
- Parent `v13/code/v13/body_jepa.py` Git blob `b935884d41d398ce2f5e513466fafd5821d60104`; candidate Git blob `fe912d908868d5e923297fa52b44e09f1e39bf1f`.
- Canon Git blob `218464b12a2d27d92524c751922fa8e1c3fb0ea7` unchanged.
- New code limits derangement sampling to 64 draws, rejects malformed permutations, preserves original RNG draws and outputs when successful, and fails closed on exhaustion instead of hanging or inventing a negative control.

## Closed original raw evidence
- **RED before source change:** Actions `40960457232`, exact HEAD `1c1bb0a4143f10114e87782f788a6af683f495e7`. Four tests, **2 FAIL**, two existing successful control tests. Raw ZIP artifact `12934394955`, SHA256 `c5b345eeb47d26313f9ce9766d8bd519f54b04b5aa2b8d45dadfe10714621a4b`, CRC clean, **11/11** inner hashes. Original failures: identity RNG called 65th time and leaked `AssertionError: UNBOUNDED_RNG_CALL`; malformed fixed-point-free duplicate permutation accepted without ValueError. CANON/COMPILE/PRIVACY/DIFF exit0, FOCUSED exit1.
- **GREEN after source change:** Actions `40960607664`, exact HEAD `635f57c8f3416a039a9b2bf1084994043716e7b2`. **4/4 PASS**; CANON/FOCUSED/COMPILE/PRIVACY/DIFF exit0. Raw ZIP artifact `12936450368`, SHA256 `64e36d13a172e8f8de598c7c90acb8526d784328c9fb2a92eeb33d3d077d0131`, CRC clean, **11/11** inner hashes.
- Both unmodified original ZIPs backed up privately under `/V13-Checkpoints/2026-10-29/Run10-BodyJepaDerangement/`, and re-materialized byte-for-byte SHA256 matched.

## Limits and next steps
- Only four new stdlib software tests were executed for this package; existing torch/PEFT Body-JEPA tests are **not** claimed passing on the changed source. After separate full-suite PEFT dependency job `40960222503` completes, run the existing Body-JEPA focused tests against this branch with compatible isolated dependencies, preserving all raw and negative gates.
- Age0 RECORD_ONLY; STEP2 UTILITY_FAIL; B3 L1 FAIL; Body-JEPA UNAVAILABLE; LP3 FAIL; jepa_weight0; Redmi UNMEASURED; V13 INCOMPLETE. No training utility, native model or AG6 promotion is inferred from these four tests.
