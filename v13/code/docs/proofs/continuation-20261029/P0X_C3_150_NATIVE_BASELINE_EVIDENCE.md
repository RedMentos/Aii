# P0X 150-row C3-only Linux-native baseline — closed evidence (2026-10-29)

Owner: GPT-6 isolated review PR #1060. Original prereg `0c29060578fb0d4a1f4e5732fb159a9ae28613df` committed before implementation. P0X source fixture registered SHA256 `ab03aba600e8085b02247657cc5fb718195e89a83641ef69ad006a27c776647e`, generator Git blob `7ec4e877ad5ea3eed1c60102dac3baa15391dd2b`, 150 holdout rows (50 each oracle A/B/NONE). No source, model, seed or Canon changes.

## Native GREEN and independently verified

- GitHub Actions run `40840179920`, exact execution head `577366b0059d8367f5c5446afc62b0d524d35768`, artifact `12882088542`, ZIP SHA256 `f115796e45e14d1fd1ff86b241222666ab8023b734a391dfa244ae26ccf833c4`.
- Independently downloaded original ZIP: CRC CLEAN, **47/47 SHA256SUMS**, **13/13 stage exits 0**, original P0X source and baseline mock artifacts rehashed, 15 focused tests PASS, privacy CLEAN.
- **150/150 real Linux x86_64 C3 calls FINAL**, frozen C3 GGUF/llama-server hashes unchanged before/after, process reaped, Age0 RECORD_ONLY, no adapters or weight updates.
- Raw SHA256 `79be6584d465b0fc3ccd33294d882a41bb1990920f3098ed39203b7aef7d18a1`, score SHA256 `7c603158c6d821592d5777d46bb4723503f74c063c5c30fcc0f72fe2720b836e`, inputs SHA256 `f8ddddb51bc92a73cf3224489073f21a101f0ec61e1a665a26497097ae9abbf5`, answers SHA256 `9c6f32638ee455e083467ed04201f5f9ddf657105977066907ba1cf93efe2a71`. Private Library backup `/V13/RawEvidence/P0X_40840179920_C3_150native_exact_head_raw.zip` rematerialized byte-identical.

## Descriptive baseline

- C3-only **50/150 exact**, **100/150 wrong committed**, UNKNOWN 0, UNPARSEABLE 0; output was `NONE` in all 150.
- Deterministic two-source oracle 150/150 by software control, preregistered oracle headroom **100/150**, exceeding minimum 15. This permits the **next controlled source-arm experiment**, not STEP2 promotion. No claim of B1/B2 complementarity from a C3-only baseline.
- Next preregistration was committed **before observing this result**: PR #1062, `P0X_C3_SOURCE_ARMS_PREREG.md` first commit `6f76921f434b769394958c9d05768629e471a060`, to compare B1-only/B2-only/both-exact/shuffled native C3 arms against this frozen baseline.

## Gates

Age0 RECORD_ONLY; STEP2 UTILITY_FAIL; B3 FAIL; Body-JEPA UNAVAILABLE; LP3 FAIL; jepa_weight=0; V13 INCOMPLETE; Redmi unmeasured. No production merge, no training, no B1/B2-generated offers in this baseline.
