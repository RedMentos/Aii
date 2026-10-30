# Run13U — independent original Run13T C3 native raw replay (2026-10-30)

Review-only child of Run13T PR #1311 at `e46f8e9f3e6ffca231f201a21d9a300688b82862`. Original native source, prereg, amended scorer, fixture, system prompts, model, seed and frozen Run13J/K/L/M remain unchanged. This review executes **no model** and never authorizes delivery, learning or age advancement.

## Original evidence and independently replayed outcome

Original GitHub Actions **41097658020**, tested head `d9d0b312168000283e84109ec3e7951304e6520b`, artifact **12996917793**, ZIP SHA256 **`86f728599312518bfa67efa0ae16e66be0eaec9ccfd8c3da8710fba40192717c`**. Independent read-only stdlib audit of exact original ZIP verified CRC, **39/39** inner SHA256SUMS, **10/10** stage exits zero, **18/18** original software tests, source/model/fixture/answer/prompt/system bindings, **16/16** native FINAL rows, **16** distinct positive native PIDs with process-reaped receipts, 8 paired source/answer IDs, all original row-level exact-copy and explicit wrong-claim counts, original aggregate totals and unchanged negative gates. Six synthetic ZIP tamper counterexamples passed locally; they are **not** native evidence.

**Outcome: `FIDELITY_HURT`** for the stricter transcription system instruction, compared with frozen Run13L copy system on new seed283 heldout tasks:

| Diagnostic | Baseline COPY | Strict COPY |
| --- | ---: | ---: |
| Byte-exact verified answer | 0/8 | 0/8 |
| Strict-full task correctness | 6/8 | 4/8 |
| Deterministic source-facts validator | 3/8 | 0/8 |
| Correct budget values | 12/16 | 12/16 |
| Correct faster option | 8/8 | 7/8 |
| Explicit regex-scannable wrong claims | 0 | 0 |

The last count is a conservative **lower bound**, not evidence that no misleading statements were generated. The strict arm sometimes omitted entire verified fact lines, altered formatting or failed to name the faster option. Neither arm copied the full answer exactly in any case. The experiment is small and synthetic; it does not prove general C3 inability, nor justify changing registered scoring after observing results. Do **not** promote STEP2, B3, Body-JEPA, JEPA learning, Redmi or whole-system utility.

## Integrity, persistence and next action

Original native ZIP was privately backed up under `/V13-Checkpoints/2026-10-30/Run13T-C3-Verbatim/run13t-native-original.zip`, materialized back and byte-compared with the downloaded original (same SHA256). Original preflight green ZIPs were also backed up and read back byte-identical. The public review branch stores only stdlib verifier, synthetic tests, CI and non-sensitive result summary; no model weights or native raw ZIP. Rejected anyone-writable Drive destination remains unused.

Next: run source-only CI against the original artifact and preserve original CI raw including failures. Then prioritize a source-bound **deterministic JEF answer fallback / C3 SHADOW validation** candidate for non-copying small C3 outputs, without modifying the frozen native cohort or enabling autonomous delivery. Original 4027-test unfiltered full-suite historical RED remains. Age0 RECORD_ONLY; STEP2 UTILITY_FAIL; B3 NO_PROMOTION; Body-JEPA UNAVAILABLE; jepa_weight0; Redmi unmeasured; whole-system incomplete.