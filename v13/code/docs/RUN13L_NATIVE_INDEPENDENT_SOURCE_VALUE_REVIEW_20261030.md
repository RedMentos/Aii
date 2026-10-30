# Run13L — independent original-ZIP source-value review (2026-10-30)

Owner GPT-6; read-only child of Run13L PR #1302, source `af9b57b92fcf0747299df75cce766a5158ff838a`. This review does **not** change the preregistered cohort, scorer, prompt, runner or original outputs.

## Original bytes and independent checks

Original Linux-native Actions **41087610878**, source head `5a78f544ea349d7d787f2fb6ad5d4d8c86f8e3c9`, artifact **12991823249**, ZIP SHA256 **`cb1c2786f663ca49840ff73d26146f60c3bbebd66546ac7b2d155e24fc72f4cb`**, 28,560 bytes. Local read of original ZIP: CRC PASS, **35/35** `SHA256SUMS`, all **12/12** native raw rows, 10/10 stage exits zero, privacy CLEAN, independent repository verifier `RUN13L_RAW_REPLAY_VALID`. Private Library original `/V13-Checkpoints/2026-10-30/Run13L-C3-System/run13l-native-original-41087610878.zip` was downloaded again and `cmp` exit 0, identical SHA256.

A separate local read-only Python check (not the prereg scorer) reconstructed each expected source answer using integer subtraction and day comparison, then compared literal raw outputs. The six `SYSTEM_ABSTAIN` outputs were **all exactly `ABSTAIN.`**. All six `SYSTEM_COPY` outputs differed from the exact four-line JEF answer, despite nonzero task-score improvement.

| Case | Expected remainders A / B | Expected faster | Raw SYSTEM_COPY issue |
| --- | ---: | --- | --- |
| Atlas251 | 531 / 345 | Silver | Juniper value present; Silver remainder omitted; delimiter and `euros` variant |
| Beacon251 | 303 / 465 | Cobalt | Wrong/swapped numeric associations; faster absent; trailing delimiter |
| Canyon251 | 529 / 312 | Lark | Both values and faster correct; leading delimiter, punctuation differs |
| Delta251 | 427 / 266 | Marble | Both values and faster correct; leading delimiter, punctuation differs |
| Ember251 | 325 / 386 | Copper | Both values and faster correct; BEGIN/END delimiters and single-line formatting |
| Forest251 | 348 / 435 | Frost | Both values and faster correct; BEGIN/END delimiters and single-line formatting |

Original frozen exploratory score **SYSTEM_ABSTAIN**: 0/12 numeric, 0/6 faster, 0/6 strict full, 0/6 exact copy. **SYSTEM_COPY**: **9/12** numeric, **5/6** faster, **4/6** strict full, **0/6** exact copy. These are source-bound Linux-native observations on six synthetic tasks, not semantic generalization or STEP2 acceptance.

**Causal scope:** The two arms differ only in system instruction; the new copy-system arm improved these frozen lexical outcomes on this cohort. That does **not** prove reliable exact copying, safe delivery, robustness to unseen human sources, or utility outside the fixture. The Beacon251 wrong value association is a concrete negative control against blindly trusting C3 output. No posthoc rescore or hidden formatting repair is allowed for this registered cohort.

Age0 RECORD_ONLY; STEP2 UTILITY_FAIL; B3 NO_PROMOTION; Body-JEPA UNAVAILABLE; jepa_weight0; Redmi unmeasured; whole-system incomplete. Original Run13J/Run13K native RED and Run13A/G14 historical RED preserved.

## Next

Before any delivery change: (1) preregister a **new disjoint** heldout source cohort with source-to-answer exact validation and contradiction controls; (2) require a deterministic JEF/Store source check on **every** candidate output and fail closed on missing, swapped or extra claims; (3) keep live C3 egress disabled until explicit authorization and gates. A prompt change is a candidate, not a proven learning mechanism.

Reproduction: fetch original ZIP from `https://github.com/RedMentos/Aii/actions/runs/41087610878`; verify outer SHA256, CRC, all `SHA256SUMS`; inspect `pilot/raw/00..05_SYSTEM_*.json`. Exact source fixture `v13/code/docs/fixtures/run13l_c3_system_seed251_20261030.json`, frozen model revision `657e078c94084481950a2d555a941481f715536b`, model SHA256 `3d10b6ab8fc91a919534b9558e266255aca0bbc7f6d015963599aa9e74e05b1d`. Platform remaining budget UNKNOWN.
