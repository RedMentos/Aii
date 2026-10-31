# Run115I prereg — disjoint Linux-native C3 exact two-source role ablation (2026-10-31)

Owner GPT-6 hourly continuation. Review-only child of Run115H PR #1490, exact parent `39f0244fab8e1ac6252a3ea8730184cda82ae10f`. Run115C seed971 native structural RED remains immutable. New **seed 983** and six *new* project IDs; no old cohort is rescored or retuned. Design committed before fixture/code/workflow/native execution. No production Runtime or Canon edits.

## Question / registered arms
Can the existing pinned Linux-native C3 `LFM2.5-350M-QAD-Q4_0.gguf` (`3d10b6ab8fc91a919534b9558e266255aca0bbc7f6d015963599aa9e74e05b1d`, revision `657e078c94084481950a2d555a941481f715536b`, pinned runner SHA256 `79e312188dc1d75c28201771f106e91de470b5cebdd838d31bb4db25eecf5d39`) compute a source-grounded eligibility answer using two exact USER source records when the records stay in the JSON user-data role rather than in the system role? This tests C3 only, not native B1/B2/JEF/C2 or split-brain gain.

Arm FULL_TWO_SOURCE: actual Run115H real Store+Context OS role-boundary prompt, plus fixed trusted task instruction in system role; no source text in system. Arm CURRENT_ONLY: same task instruction and current source JSON only, with prior omitted. Order alternates by row; 12 native C3 FINAL attempts, deterministic seed983, temperature 0, schema JSON exactly `{"choice":"A|B|NONE","remaining":integer|null}`. Max output 96 tokens, deadline 90s per native call. No tool invocation or live output. Model-free preflight and native reports must preserve full prompt hashes, exact SourceRefs, outputs, FINAL metrics, process-reap receipts, closed Store integrity and failure rows.

## Frozen six-case source cohort and strict expected oracle
Prior policy always comes from a distinct earlier USER event; current options from the latest USER event. For each project, both sources start with `Project <ID>.`. Cheapest eligible choice respecting budget, deadline and local-only, remaining = budget - cost; NONE has null remaining.

1. **Vireo:** prior budget 180 euros, deadline 5 days, local-only true. Current A cost 160, duration 4, local yes; B cost 130, duration 7, local yes. Oracle A/20.
2. **Solara:** prior budget 250, deadline 8, local-only false. Current A cost 230, duration 7, local yes; B cost 210, duration 6, local yes. Oracle B/40.
3. **Nyxford:** prior budget 90, deadline 3, local-only true. Current A cost 95, duration 2, local yes; B cost 85, duration 5, local yes. Oracle NONE/null.
4. **Etrion:** prior budget 300, deadline 9, local-only true. Current A cost 260, duration 8, local yes; B cost 220, duration 7, local no. Oracle A/40.
5. **Quendia:** prior budget 220, deadline 6, local-only true. Current A cost 210, duration 6, local no; B cost 180, duration 5, local yes. Oracle B/40.
6. **Morenix:** prior budget 150, deadline 4, local-only false. Current A cost 160, duration 3, local yes; B cost 140, duration 6, local yes. Oracle NONE/null.

All six cases are fixed here before implementation. Balanced A/B/NONE = 2/2/2. `oracle` and `expected` must not enter model prompts. No posthoc threshold change: exploratory signal only if FULL >=5/6, FULL-CURRENT >=2/6 and no false selection in NONE cases. Any result below is **NO_GAIN**, not a reason to alter this cohort. Native engineering failure is RED with original raw retained; do not call it scientific failure unless 12 valid native FINAL calls are obtained.

## Execution / acceptance
First create exact UTF-8 JSON fixture, hash-lock its bytes in runner, test six oracle labels and no oracle leak; source-only CI with real SQLite/Context OS and source ZIP/manifest/privacy proof. Only after green preflight and checking heavy native owners, launch pinned C3 under concurrency group `v13-native-c3-ag12-20261030`, `cancel-in-progress: false`. Record original ZIP SHA/CRC/SHA256SUMS and private Library byte-exact backup. Do not silently change pins, seeds or fixtures. No synthetic result counts as native.

All gates remain: Age0 RECORD_ONLY, STEP2 EXIT EVIDENCE_NOT_PASSING / UTILITY_FAIL, B3 NO_PROMOTION, Body-JEPA unproven, World-JEPA SHADOW, `jepa_weight=0`, Redmi UNMEASURED, whole V13 INCOMPLETE.
