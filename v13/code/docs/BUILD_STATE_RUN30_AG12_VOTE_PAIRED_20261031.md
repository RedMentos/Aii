# Run30 — independent paired AG12 vote diagnostic (read-only, posthoc)

Owner: GPT-6 scheduled continuation, review-only child of Run29 at `be88168989fb47cac2c8a81db62217468456fb4b`. 2026-10-31 UTC. Source script `v13/code/scripts/run30_ag12_vote_paired_raw_audit.py`; no production runtime modification, no model calls, no training, no changed registered cohort.

## Original immutable evidence independently checked

- Run25 Linux-native B1/B2 original Actions 41142873467, artifact ID 13020430675, ZIP SHA256 `4a4b99a12cc2b60fa755aab7db5930cb9f8cd65ceea76272d8b2279e1b08331e`; CRC PASS, 27/27 inner hashes, all exit stages 0. Exactly 352 role-calls.
- Run27 Linux-native three-organ BodySolver vote original Actions 41144174479, artifact ID 13019429115, ZIP SHA256 `6263b4f84060eec826cd819fdc108a6ac609b5261d84df0508d889736305d7ae`; CRC PASS, 23/23 inner hashes, all exit stages 0. Exactly 528 role-calls and 176 voted rows. Three distinct pinned GGUF models. Neither artifact contains private prompt text in the exported AG12 row summaries.
- DE suite SHA256 `37c4c4283eeb3ea7e0c80b1336de586413c8078d6377210b0e2db534d93cb635`, EN `218bd5bd89de161fb75e0fdc24dfb63919f7ee0d5abcd58b5a0c638c6cde5375`. Each 88 IDs matched in exact order, no duplicates, all correctness values integer 0/1. Raw ZIPs remain under GitHub Actions artifacts; do not commit them to the public repo.

## Observed paired outcomes (88 items each)

| Language | Comparison | Baseline correct | Vote correct | Both correct | Vote-only correct | Baseline-only correct | Both wrong | Exact McNemar p (posthoc) |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| DE | B1 vs vote | 19 | 31 | 17 | 14 | 2 | 55 | .004181 |
| DE | B2 vs vote | 30 | 31 | 27 | 4 | 3 | 54 | 1.000000 |
| EN | B1 vs vote | 14 | 30 | 14 | 16 | 0 | 58 | .000031 |
| EN | B2 vs vote | 31 | 30 | 29 | 1 | 2 | 56 | 1.000000 |

**Interpretation:** The existing offline three-organ vote substantially outperforms B1 alone on this narrow procedural suite, but **does not demonstrate improvement over B2 alone** (DE +1/88, EN −1/88; discordant 4/3 and 1/2). Exact paired p-values are exploratory after seeing the data, not registered utility gates, not evidence of learned transfer or generalized reasoning. This does not prove live JEF fusion or STEP2 complementarity. Run26 oracle upper bounds are separate and cannot substitute for a real selector.

## Reproduction, acceptance, next work

Download the exact Run25/Run27 original ZIP artifacts and verify their SHA256. Then run:

`python3 v13/code/scripts/run30_ag12_vote_paired_raw_audit.py --run25 /path/to/run25-bodies.zip --run27 /path/to/run27-native.zip --out /fresh/run30-vote-paired.json`

The script must reject mismatched original ZIP SHA, CRC, incomplete/duplicate inner manifest, nonzero stage, changed suite hashes, misordered/duplicate IDs, malformed correctness, and non-fresh result path. Synthetic unit tests `python3 -m unittest -v tests.test_run30_ag12_vote_paired_raw_audit`; CI workflow `v13-run30-ag12-vote-paired-software.yml` launched separately; **no CI pass claimed before inspecting the original run**.

Next: inspect Run29 registered real-file World-JEPA workflow, download and independently verify original ZIP and W1..W6; preserve any RED. For AG12, pursue a separately preregistered actual fusion/selector comparison on disjoint data rather than treating posthoc oracle coverage as performance. No automatic production merge.

Gates unchanged: Age0 RECORD_ONLY, STEP2 UTILITY_FAIL, B3 NO_PROMOTION, Body-JEPA UNAVAILABLE, jepa_weight=0, World-JEPA SHADOW, no Redmi and whole-system completion false.
