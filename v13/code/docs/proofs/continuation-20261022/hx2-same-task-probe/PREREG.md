# WP-HX2 Preregistration: same-task probe without gold answers (B2 rule quote, STEP2)

Written 2026-10-22 before any HX2 model run. Runner `scripts/hx2_same_task_probe.py`, core `v13/agi/harness_probe.py`.
Evidence level: Linux cloud, 4 CPUs, same three models as Z2b/Z2c (bootstrap, b10964 runner). No Redmi. Never promotes
the canonical STEP2 gate (stays UTILITY_FAIL).

## Question
Can an allow-listed harness edit (target `prompt.b2_earlier_context`, the B2 earlier-context instruction, frozen
weights) chosen by a gold-free probe on the same task raise STEP2 utility on held-out episodes and fresh seeds, and is
the gain specific (an unguided edit of similar length does not give it)?

## Path and settings
Pre-2026-10-21 quote path, so there is room to gain: `LEGACY_QUOTE_PATH | z2.ARMS['C'] | {seed, b2_quote_select: off}`,
two bodies, Z2b targeted question on current-turn offers (= Z2c arm CQ, B2 full-rule rate .167 there). The live default
now uses the pointer switch (.969 in Z2c); HX2 is a test of the method, not a live change. Arms differ only in the
harness overlay (bench-only `harness_probe.overlay`, restored after each run). cognition.py is hash-pinned by the
source-handoff chain and stays unchanged: the overlay rewrites the exact base text inside the B2 system message of each
native call and counts the rewrites (REF: none; every other arm: > 0, else INVALID).

## Proposals (fixed now, written by the cloud editor, appended to the unchanged base text)
- V1 general: "Copy every quote character for character from one source sentence: same words, capitals and punctuation; never shorten, join or reword it."
- V2 domain: "When the current text does not restate a project rule such as budget, deadline or a local-only requirement, quote the whole earlier source sentence that states it, word for word."
- V3 = V1 + V2.
- U unguided control (similar length, unrelated to the observed failure): "Keep the summary in plain, friendly English, in complete sentences, and avoid repeating the same word twice in a row."

## Stage 1 probe (seed 20, arms REF V1 V2 V3, all 10 episodes run)
Selection uses only probe episodes P = Kestrel, Lumen, Meridian, Quasar, Sirius and only a gold-free score:
mean over B2 current-turn offers (variants b2_only, both_none, both_exact, both_control) of verified/emitted quotes
(emitted = first 3 quotes, verified = not rejected by the exact source check; offer without quotes = 0). No oracle,
no utility, no rule label is read for the choice. Behaviour differences vs REF (quotes, rejected, summary, answer,
prompt tokens) are logged per task. Choice = best score if it beats REF by >= .05, else **HX2_NO_CANDIDATE** (stop).

## Stage 2 holdout (seeds 21 22 23, arms REF, chosen, U)
Held-out episodes H = Nimbus, Orion, Perseus, Rigel, Tycho (never looked at for the choice). Per episode the mean over
the 3 seeds is one cluster; 95 % percentile bootstrap over the 5 clusters (10000, seed 20261022).
Axes: both_exact tool-replay utility (primary), b2_only, b1_only utility, B2 full-rule rate (gold-scored, RULE/SPLIT
episodes only), wrong committed answers (sum).

Decision, in this order:
1. HX2_INVALID: a structural failure, or an arm's targeted question not on every current-turn offer.
2. HX2_AXIS_WORSE: chosen wrong commits > REF, or any axis mean (chosen - REF) < -0.02.
3. HX2_NO_HOLDOUT_GAIN: primary (chosen - REF) CI lower bound <= 0.
4. HX2_UNSPECIFIC_CHANGE: (U - REF) CI lower bound > 0, or mean (chosen - U) <= 0.
5. HX2_PASS otherwise.
Secondary (reported, not deciding): the same gate on all 10 episodes at seeds 21-23; B2 prompt tokens per arm.

## What follows
PASS: the harness overlay may be proposed to the user via AG8 (kind harness, shield), live wiring still only with the
user's approval; HX5 export unlocks. Any other status: nothing changes live, HX5 stays locked, result recorded as is.
