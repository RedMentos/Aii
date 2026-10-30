# STEP2 Z2 budget-remainder body-question paired native pilot — prereg 2026-10-30

Exact parent `d7dddf8ab6c23f187003d919570dc18b650d5a8b`, current review chain #1192–#1196, Canon blob `218464b12a2d27d92524c751922fa8e1c3fb0ea7`, model catalog `7af05962af41d0bc3f7dd18ef01d4eba55eabf99`, control tools `954a3f468f10195fbce12d27f68585ee7edee2c9`. Prior original native STEP12 structural PASS but budget remainders **0/2** in independent scorer. This new run uses **fresh disjoint** synthetic projects and does not overwrite/relabel any original registered cohort, fixture, source or seed.

## Fixed 4 fixtures before implementation
1. Project Vega, budget 145 Euro; Amber costs 95 Euro / 3 days; Cobalt costs 125 Euro / 1 day. Remainders Amber **50**, Cobalt **20**.
2. Project Lyra, budget 210 Euro; Copper costs 150 Euro / 2 days; Silver costs 190 Euro / 4 days. Remainders Copper **60**, Silver **20** (cheaper is also faster, counteracts expensive-is-faster shortcut).
3. Project Nadir, budget 180 Euro; Pine costs 130 Euro / 5 days; Birch costs 165 Euro / 2 days. Remainders Pine **50**, Birch **15**.
4. Project Orion, budget 275 Euro; Jade costs 205 Euro / 6 days; Coral costs 250 Euro / 3 days. Remainders Jade **70**, Coral **25**.
All options explicitly local, no cloud; ask remaining budget **for each named option** and concise time/cost tradeoff. No correct remainders are included in the prompt or the candidate body questions.

## Fixed arms, order, score
- **A: C3-only**: `route_override=simple`, body/gist manifest absent. C2/C3 remain available.
- **B: default two-body**: `route_override=both`, original `body_question_b1`/`body_question_b2` unchanged.
- **C: candidate two-body**: same as B except B1 question asks to compute exact remainders from cited source budget/cost values, B2 asks to identify local-only constraint and time/cost tradeoff from the exact source; neither injects target answers.
- Four fixtures × three arms = **12 isolated native turns**, each a fresh scratch Runtime with pinned model/binary symlinks, fresh session and Age0 RECORD_ONLY, `jepa_weight=0`, latents off, seed=13. Serialize model-heavy jobs. No learning, external tools, age promotion, model substitution or paid provisioning.
- Primary outcome per arm: **number of correctly named exact Euro budget remainders out of 8**. The scorer must require exact amount bound to the correct option plus an explicit leftover term; merely echoing costs or swapping values fails. Track final status, B1/B2 offers, C2 native control, runner role, latency and process reaping. Invalid/missing turns count as failures, never silently dropped.
- Pilot signal: C improves over B by at least **2/8** and over A by at least **2/8**, with no loss of valid native FINAL evidence. Small sample, fixed order, no statistical STEP2 gate claim even if pilot signal met. If no improvement, report **NO_GAIN** and keep STEP2 UTILITY_FAIL.

## Evidence and stop
Ubuntu 24.04 Linux-native, not Redmi. Exact pinned public model artifacts deep verified before experiment; no concurrent native jobs. Save all raw per-turn audit JSON and output, stage exits, fixture hash, model/tool/source hashes, HEAD, SHA256SUMS, original failed attempts and private Library backup. Never claim semantic complementarity, B3, Body-JEPA, `jepa_weight` or whole-system completion from this pilot. If bootstrap/network/native fails, preserve RED and continue independent packages.
