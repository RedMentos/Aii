# Run109 prereg — fresh STEP2 long/revised native-cohort fixtures, software-only preparation (2026-10-29)

Owner: GPT-6 scheduled continuation. Conditional review-only child of Run108 #1012 exact `7546d14bb116f3a3c32f6c8d687eb35e464c9f46`, Actions `40800196929` pending at prereg. **Do not execute Run109 until Run108 original raw independently GREEN**. Run107 pinned native CI must finish before starting any later heavy B1/B2 model cohort. This package creates and tests **only a deterministic fixture generator**; it does not run a model, prove B1/B2 complementarity or change the old Z2d cohorts.

## Six preregistered public synthetic cases (no substitutions)
Use the existing `scripts.step2_z2_timescale.episode` and `recipe` for oracle/action; copy fixture dicts, never mutate `z2.FIXTURES` or original `EPISODES`.

LONG: `Atlas` SPLIT rules (130,6,true), options A=(60,3,true), B=(85,4,false); `Borealis` RULE rules (95,4,false), A=(50,3,false), B=(70,2,true); `Cygnus` SPLIT rules (115,5,true), A=(80,4,true), B=(75,6,true). For each, place 12 fixed filler sentences after kickoff header **before** the three rule sentences in history[0]. This exceeds 240-char B2 excerpt and 200-char quote expansion; measure missing rule access, do not silently fix.

REVISED: `Delta` SPLIT old (80,7,true), latest (100,5,false), A=(65,4,false), B=(60,6,true); `Epsilon` RULE old (120,6,false), latest (90,4,true), A=(75,3,true), B=(55,5,true); `Fornax` SPLIT old (70,8,true), latest (110,3,false), A=(80,2,false), B=(65,4,false). For each, history[0] explicitly records old rules; history[1] explicitly records **later revision** with latest rules; history[2] retains original options sheet/status note. Oracle and fixture `rules` remain the latest values; no assertion that B2 will actually choose correctly.

## Pre-execution software acceptance
- Six unique fixtures, 3 LONG/3 REVISED, fixed types and values, no original z2.FIXTURES mutation; each oracle matches `recipe` applied to **latest** rules and options.
- LONG first rule starts beyond character 240; B2 bounded excerpt cannot contain all three rules. REVISED has distinct old/latest values and ordered history; no ambiguous oracle.
- All history/current texts are source-exact public synthetic; deterministic SHA256 of canonical JSON stable across runs; no model or Store calls.
- New `scripts/run109_step2_fresh_fixtures.py`, focused unit tests, branch state, pinned software CI raw SHA256SUMS, privacy/diff and full suite. No native/Redmi, no user decision, no source/model/seed change.

## Later distinct native cohort (NOT authorized by this software prereg)
After this fixture package is independently GREEN, create a **new** prereg with fixed model/runner/source hashes and fresh seeds 20/21/22, arms CQP (two bodies, B2 pointer), DQP (shared body, pointer; model+architecture confounded), CQ (off control), paired same-arm `prompt_only_dual` and best single, 6 episodes × 7 variants. Explicitly distinguish model confound, old/revised rule false commits, quote coverage, latency/RSS, episode-bootstrap intervals and STEP2 gate remains negative unless every canonical condition independently passes. Do not launch multiple native jobs concurrently.

Age0 RECORD_ONLY; STEP2 UTILITY_FAIL; B3/Body-JEPA/LP3/jepa_weight/Redmi/whole-system negative.
