# Run111 — WP-DS2 compositional word grounding ("glas auf stein") lab (preregistered)

Date 2026-10-25 UTC. Base verified Run110 PR #141 `bfd3f66d4b314093324f4fce638f02afb8c4a1a6`. New independent owner: `v13/code/v13/sandbox_composition.py`, `tests/test_sandbox_composition_run111.py`, `scripts/sandbox_composition_bench_run111.py`, isolated workflow and this evidence folder. No edits to DS1/DS2 sandbox.py, Runtime, models, Age, World-JEPA or native cohorts. DS2 Run110 H2 FAIL remains unchanged.

## Canonical scope

Roadmap WP-DS2 follow-up: test whether word combinations ("glas auf stein") generalize through own action/outcome learning, without memorizing every full phrase. Pure synthetic lab, STEP8 still locked. Not a claim of language understanding or embodied hardware.

## Locked generative world (no post-result tuning)

Four object words (glas, kiste, apfel, stein), three support words (stein, kiste, glas), three actions (push, touch, lift), three outcomes (MOVED, BLOCKED, SOUND). Hidden environment outcome distribution for each (object, support, action) is 0.55 times object/action distribution plus 0.45 times support/action distribution, both fixed in source. Agents never read hidden tables; they receive only sampled outcomes. Hold out exactly three complete phrases: (glas,stein), (kiste,glas), (apfel,kiste). Train on other nine pairs only, 600 paired observations per seed; same observations for all models.

Three baselines:
- `pair`: Dirichlet counts for exact phrase/action; unseen phrase stays at prior.
- `object`: Dirichlet counts for object/action, ignores support.
- `factor`: Dirichlet counts for object/action and support/action, predicts their fixed 0.55/0.45 mixture. No oracle truth access.

Fresh seeds 200..219 (not DS1/DS2 100..119), 600 interactions each. Report heldout mean KL(true || predictive), train KL, per-seed wins, source and report hashes. All holdout pairs must remain untrained in pair memory; every constituent word must have training coverage.

## Preregistered verdict (all required)

H1 factor < pair heldout KL in >=16/20 paired seeds.
H2 factor < object-only heldout KL in >=14/20 paired seeds.
H3 factor mean heldout KL <=0.12.
H4 zero holdout-pair training and all heldout constituent object/support words observed in training in every seed.

If any FAIL, keep negative result and do not promote. Tests must prove deterministic streams, normalization, no oracle TRUE access from model, and no holdout contamination. Do not tune same seeds after seeing results.

## Claim limits

Toy language/action composition only, no vision, native LLM, JEPA weights, Redmi or AGI. STEP2 UTILITY_FAIL; B3 L1 FAIL; Body-JEPA UNAVAILABLE; jepa_weight=0; V13 INCOMPLETE. Original Run110 DS2 H2 FAIL remains.
