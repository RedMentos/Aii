# HB1b 24-call native C3 format diagnostic — closed evidence (2026-10-29)

Owner: GPT-6 isolated review, PR #1057, branch `codex/v13-hb1b-c3-format-24native-20261029`. Original prospective prereg `4b4978c4ed55b0397ca03ff930bf06477f8d5137`; anti-echo confound addendum `136be8933f99962bcae6d1d41fb46a66f465f541`. Pre-native build-state commit `ebf5a6b835447bb30f354d12b567c1328e28e7a8`. Original HB1a/HB1b RED attempts remain separately retained; no source/seed/model/Canon changes.

## GREEN Linux-native run

- Exact head `282f99dd3d45f203c895de01c7e63492c4eb4c57`, GitHub Actions run `40838569816`, artifact `12881832082`, ZIP SHA256 `7e0308577030b6ea2d45b17bb28ad2afe5da276bb06340ec682920613dd2cae2`.
- Independently downloaded original ZIP: CRC CLEAN, **98/98 SHA256SUMS** valid; **14/14 stage exits 0**; parent HB1a native and both HB1b source artifacts independently rehashed; focused tests 12/12 PASS; privacy CLEAN.
- **24/24 real Linux x86_64 C3 calls FINAL** with pinned LFM2.5-350M model and llama-server binary hashes unchanged before/after, process reaped, `c3_sampling=off` for all four arms, no adapters/training/weight updates.
- Raw SHA256 `f68a33953fea8e8c7f959f50c1fd25d69e0002f5784ad068dc853df1a6a7d174`, score SHA256 `47cb2a7cf3c7ba9f1b89600b1093f77da4c753e6cce09327737fa26414d8ac45`, inputs SHA256 `9562732fd1efc0319a0e7be7f8578e8361c899b7739418c51746d830630db1de`. Permitted private Library backup `/V13/RawEvidence/HB1B_40838569816_24call_linux_native_exact_head_raw.zip` rematerialized and byte-verified.

## Registered descriptive result (six reused public synthetic tasks)

| Source view | Strict JSON exact | Plain token exact |
| --- | ---: | ---: |
| Both original sources | 0/6 | 0/6 |
| Both generated B1/B2 offers | 2/6 | 1/6 |

Plain exact-source arm answered UNKNOWN in all 6; plain generated-offer arm UNKNOWN 3 and NONE 3. Strict JSON generated-offer arm NONE in all 6. No arm produced A. **Removing JSON schema did not recover reliable source-dependent C3 decisions.** This is a posthoc-motivated prospective diagnostic, not an independent 150-row holdout or evidence of a general format causal effect.

## Gates and next step

Age0 RECORD_ONLY; STEP2 UTILITY_FAIL; B3 FAIL; Body-JEPA UNAVAILABLE; LP3 FAIL; jepa_weight=0; V13 INCOMPLETE; Redmi unmeasured. No production merge or new runtime authority. Next substantive work: preregister an independent 150-row P0 native cohort with actual oracle headroom and develop default-off P2 receiver learning (source/action outcomes, shuffled/no-source controls); no rescoring or replacement of this evidence. Exact hash-bound result: `HB1B_C3_FORMAT_24NATIVE_RESULT.json`.
