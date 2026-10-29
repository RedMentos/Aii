# P2X 16×4 LoRA artifact independent offline evidence audit — prereg (2026-10-29)

Owner: GPT-6 independent reviewer. Exact parent: PR #1088 head `c4243164f8d100dc826f3e1ee2d7d169228cd649`. This child branch changes no training, runtime, model, seed, frozen cohort or production configuration. The parent software Actions run 40868563641 was IN_PROGRESS when registered. Separate source-only review; do not compete with a native model owner.

## Hypothesis and threat model

A four-step trainer return value is not independent proof of four optimizer steps or a usable adapter. Existing `p2x_c3_receiver_fourstep.py` verifies GGUF hash and reported 44 tensor count but does not independently bind the PEFT safetensors file, exported GGUF path, source-selected rows and all metrics after artifact preservation. An adapter/report pair may be missing, modified, symlinked, mismatched or overstate source coverage. Build a **read-only** offline audit of a native result using the exact frozen trainset and the existing P2X source selection. Do not use P2X validation answers or P0X holdout.

## Prospective implementation and tests

Add `scripts/p2x_fourstep_evidence_audit.py` and `tests/test_p2x_fourstep_evidence_audit.py`. Validate immutable prereg constants and source identities; deterministic 16 selected row hashes and A/B/NONE/UNKNOWN balance; exactly 4 finite CE history entries; fixed seed/rank/targets/jepa=0 and negative authority flags; exact adapter GGUF and safetensors SHA256 and file sizes; disallow symlink/escape outside an explicitly supplied evidence root. Reject malformed, missing, forged or nonfinite fields. Report `ARTIFACT_CONSISTENT_ONLY`, not independently observed training or native utility. Preserve any negative result, never mutate input. Include positive and adversarial tests with synthetic files clearly labeled synthetic, and a source-pinned GitHub Actions focused + full software suite, hash/exit/privacy evidence.

## Acceptance / stopping

A GREEN software run means only the verifier's source-only behavior passed; even an artifact-consistent native report is self-reported training history and must be paired with the original Actions raw artifact and independent native execution audit. No QAD GGUF deployed-path parity, P2X heldout utility, AG6 approval, JEPA, STEP2, B3, Redmi or full V13 promotion. Keep Age0 RECORD_ONLY, STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, LP3 FAIL, jepa_weight0, Redmi unmeasured, V13 INCOMPLETE. Check exact remote head, original ZIP CRC/hash and private backup only through permitted storage; do not retry rejected public Drive destination.

Next command: run source-only workflow on this child review branch; audit raw SHA256SUMS and stage exits; then use this offline verifier against the original 16×4 native artifact if/when that native job is authorized and complete. Continue other independent canonical work while waiting.
