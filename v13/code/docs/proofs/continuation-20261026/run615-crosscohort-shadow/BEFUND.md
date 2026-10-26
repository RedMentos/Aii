# Run615 — Cross-cohort trainable B1→B2 readout (SHADOW): NO_CROSS_BODY_GAIN

Date 2026-10-26 UTC. Review-only PR610, branch `codex/automation11-run615-crosscohort-shadow-20261026`; base Run614 PR609 `7cac4d667c075e863822b64b771e6a6af8fcd5ff`. Preregistered before source at `1b1188c2a60d0aa60ded9e40b0f6d5993a4d3563`. Both native heldout cohort results were already known: this is **posthoc exploratory**, not a new prospective confirmation.

Implemented source-bound, train-only ridge and 32D regularized orthogonal Procrustes B1→B2 readouts. Original Run608 and Run614 Linux-native frozen read-only state artifacts and model pins were SHA-verified. 50 fixed shuffled-label controls each, exact opposite-paraphrase 20-row test. No native inference or body weight updates in this package; no receiver injection, no EMA/JEPA body training.

| Heldout metric | top1 | MRR |
| --- | ---: | ---: |
| Run614 B1-only | .65 | .748 |
| Run614 B2-only | **.85** | .917 |
| Cross-cohort: train Run608, test Run614, ridge | .20 | .391 |
| Cross-cohort: train Run608, test Run614, Procrustes | .25 | .437 |
| Within-cohort: train Run614 60, test Run614 20, ridge | .30 | .475 |
| Within-cohort: train Run614 60, test Run614 20, Procrustes | .30 | .473 |

Cross-cohort shuffled-label empirical p=.0196 for both readouts; **neither approaches the stronger within-body B2-only baseline**, so the frozen +.10 over best single body criterion fails. Shuffled p does not imply system utility. Original Run614 B2-only proxy remains within-body, not a two-body success.

Original native states SHA256: Run608 `c6e6a7a6521d14c90805a996e723e9cd7716cd6ba6d13577480eff30349625ca`; Run614 `cb535df87749c0cf5d698d26268e6b03f3d6f57690b95434aebc6c875a3ea189`. Result JSON SHA256 `97423cb19d1e9bed323aedb076fdf1f0e6f53293fc3acb253ffb9e98bfc710d9`; independent Linux GitHub Actions output matched this SHA exactly. Script Git blob `22c1c4c55d95588135e0959693e7321d3706fdb0`; tests Git blob `f044640343cd0a4953d5f35563a06cb92c391625`.

Evidence: local 9/9 real-artifact/contract tests PASS; GitHub Actions run `40411617253` SUCCESS, exact head `7c80fc086ebc11ad5ec86eac41d2bc8c7f4b7e1b`, artifact `12692083889`, tests exit 0, privacy exit 0, download exit 0, raw manifest verified. Failed attempts `40410913347`, `40411043460`, `40411352495`, `40411558215` retained; causes were artifact extraction and shallow Git privacy scan setup, not hidden. Full original states/reports, local source/tests, local raw and hashes saved privately under `/V13-Checkpoints/2026-10-26/Run615/run615-closed-evidence.zip`; GitHub CI raw has 30-day retention and is not the sole backup.

No gate promotion: STEP2 `UTILITY_FAIL`; B3 L1 `FAIL`; Body-JEPA `UNAVAILABLE`; `jepa_weight=0`; Redmi `UNMEASURED`; V13 `INCOMPLETE`. The binding blueprint and user decisions remain intact.

Next: finish Run616 B2 read-only semantic cue operator; then source-disjoint native utility test of candidate retrieval with actual stored taps and human-facing Context OS output. Requires original B2 native tap and target Redmi run for phone evidence. Do not treat this posthoc readout as Body-JEPA.
