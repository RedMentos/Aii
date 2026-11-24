# Run63 — JEF human F1/F5 → native C3 typed receiver paired pilot preregistration

**Date:** 2026-10-31 UTC. **Owner:** GPT-6, review branch `assistant/v13-run63-jef-c3-native-gpt6-20261031`, base JEF C3 envelope software `3d88e10047cca380cac150bace2425f6c11c1563`. Preregistered before native runner, verifier, tests and workflow. No changes to frozen Run47, P2X cohort, source/model/seed/scorer, or original JEF source code.

## Objective and fixed cohort

Test a real local C3 model as **formatter** for a human-source-verified JEF A/B/NONE decision, versus the same C3 directly selecting from both raw sources. Use unchanged P2X seed `2026102921`, exactly **three** calibration cases selected as lexicographically smallest project ID for each oracle action `A`, `B`, `NONE`. This reuses an existing calibration cohort: **engineering integration only, not disjoint utility**. Six paired C3 calls, order A=(RAW,TYPED), B=(TYPED,RAW), NONE=(RAW,TYPED); no substitutions or retry of failed rows. No oracle is passed to C3.

**Pinned native:** C3 LFM2.5-350M QAD Q4 GGUF SHA256 `3d10b6ab8fc91a919534b9558e266255aca0bbc7f6d015963599aa9e74e05b1d`; llama runner SHA256 `79e312188dc1d75c28201771f106e91de470b5cebdd838d31bb4db25eecf5d39`. Existing native Runtime, temperature=0, seed=13, max_tokens=32, two-message prompts. RAW system: select from exact policy+sheet and return only uppercase A/B/NONE. TYPED system: fixed `jef_c3_typed_envelope_candidate.SYSTEM`, payload from actual two F1/F5 HumanDecision SourceRefs and current USER event. Exact same local model/revision in both arms. Serialize heavy native jobs using existing `v13-step2-budget-paired-native-20261030` concurrency group.

## Frozen scoring and structural gates

Per row, `strict_correct=1` iff native decoded text is **exactly** one of `A|B|NONE` and equals original frozen oracle action, no trim/JSON/normalization. Wrong/empty/error =0. Typed arm must also pass the new source-bound JEF C3 formatter verifier. Engineering pilot criterion: 6/6 structurally complete real C3 FINAL, all native processes reaped, exact source/model/runner hashes and closed Store, **TYPED 3/3** strict and **TYPED > RAW** strict. Otherwise retain `RECEIVER_PILOT_RED`; even pilot PASS does **not** promote STEP2, general utility, or whole-system completion.

All original rows and failures are preserved in closed raw report, independent verifier and SHA256SUMS. Never adjust prompt/seed/model/scorer after seeing output. No C3 model weights trained, no native Body, no Redmi, no real TTY/FINAL/output/tool/learning authority. Human correction source integrity proves only explicit source lineage; model output is not a human label.

**Software acceptance before native:** exact pinned source, fixture validation, real SQLite JEF/C3 envelope tests, independent verifier false-claim tests, privacy CLEAN, compile. **Next:** download original native ZIP, verify CRC/manifest/row hashes, save byte-identical private Library backup, scoped BUILD_STATE; if native fails, pursue other Canon work without treating this as whole-blueprint blocker.
