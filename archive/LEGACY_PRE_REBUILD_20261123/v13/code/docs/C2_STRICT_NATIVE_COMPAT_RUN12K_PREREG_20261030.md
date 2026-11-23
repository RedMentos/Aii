# Run12K — preregistered disjoint Linux-native C2 strict-admission compatibility (2026-10-30)

Owner: GPT-6. This document is fixed **before** any Run12K native invocation. Parent Run12J draft PR #1266, strict Runtime source blob `22ed11e4a53d9eeae8fbc74a1753082b5785be2b`. No previous frozen cohort/seed/model/source hash is changed.

## Scope and fixed data

- Four disjoint synthetic prompts, original C2 native `_turn` source reused unchanged from `scripts/c2_native_route_provenance_20261030.py`. Original seed **43** is reused because `_turn` is frozen; the prompt cohort is new and disjoint from original seed43 cohort.
- Prompt order and expected `scaffold_route`: (1) `Hello from project Sable; greet me briefly.` → simple; (2) `Project Kestrel: choose between route A and B and explain your choice.` → simple; (3) `What is 13 + 29?` → detail; (4) `Summarize project Ember in one sentence.` → gist.
- Canonical JSON tuple SHA256: `cc45889077cae32fac4911ad91e7b2fa279a6bfd2d8d43ddac712e0ca1cc7014` (json.dumps(tuple,sort_keys=True,separators=(',',':'))).
- Pinned native Needle3 CQ2 file SHA256 `c9d915eca282ed42d1a09b143b592adb4cc6744ffe2d294adf5cfc5548170c38`, model revision `b274efcb211a9eef48c9a88da4b43bd569696a39`, official Cactus-Compute/needle3 Apache-2.0; `specs/models.json` Git blob `7af05962af41d0bc3f7dd18ef01d4eba55eabf99`, `specs/control_tools.json` blob `954a3f468f10195fbce12d27f68585ee7edee2c9`. Build pinned native worker from original source; no substitute model or runner.

## Predeclared readouts and threshold

- **Native invocation**: all four calls must have actual native C2 operation C/FINAL process and source/event/session/ExecutiveControlContext proof, followed by process reaping. If any missing, `native_c2_proven=false`.
- **Strict admission compatibility**: every row must match the independently read-only unique validated `select_processing` decision, and at least **1 of 2** simple-scaffold rows must actually select the native advisory. Non-simple rows must stay scaffold. If not, `strict_compatibility=false`; retain RED, no threshold changes after seeing outputs.
- Report raw `native_control`, source refs, packet context, output, status, model/worker hashes and both expected and actual route selection for each row; include failures, never discard them. Original Run12J software result 57/57 is not native proof.
- **Not tested**: route semantic accuracy/utility, C3 or B1/B2 answer quality, B3, JEPA, Redmi, Age promotion, whole system. `learning_mode=RECORD_ONLY`, `jepa_weight=0`, STEP2 UTILITY_FAIL and all other negative gates remain.

## Execution plan

Source-only prereg + tests first; then one serial GitHub Actions Linux-native workflow under existing `v13-step2-budget-paired-native-20261030` concurrency group. Install pinned Needle3 and build pinned worker, not the other three models; isolate a fresh Store per prompt; preserve original raw and SHA256 manifest even on RED. Independently verify ZIP and byte-exact private Library backup before interpreting results. Never call this a STEP2/Redmi or native utility PASS.
