# Run115B prereg — independent six-project JEF typed-source replication, 2026-10-31

Owner GPT-6. Review-only child of Run114B PR #1484, exact parent `472be2372190f737df44363f6cf95204d99a1de2`. The Run114B original Linux-native exploratory result was RAW_BODY **0/3** vs TYPED_JEF **3/3** with different instructions; this new study is a fresh disjoint replication, not a retune or rescoring of seed947. No production Runtime/Canon/model catalog changes.

## Frozen before implementation
Seed **971**, fixture `docs/fixtures/RUN115B_JEF_B1B2_C3_SEED971.json`, canonical UTF-8 sorted compact JSON + LF SHA256 `21617baf735436af9a388c9be596bf763dc46f8bb394548daa961ad5ec1f57fd`. Six disjoint synthetic public projects; each has exact archived/current USER source, source quotes, and oracle choice+remaining:
- Lumen, grammar ONE, local-only true: expected A, remaining 2.
- Boreal, grammar TWO, local-only yes: expected B, remaining 10.
- Coral, grammar ONE, local-only true: expected NONE, remaining null.
- Delta, grammar TWO, local-only no: expected B, remaining 10.
- Helios, grammar ONE, local-only false: expected A, remaining 20.
- Nimbus, grammar TWO, local-only yes: expected NONE, remaining null.

Frozen arms `RAW_BODY` and `TYPED_JEF`, alternating order starting RAW for Lumen, TYPED for Boreal, etc. Reuse **unchanged** Run114B exact-source/JEF/Context OS SHADOW pipeline via a scoped wrapper; no edit to Run114B seed947 source, fixture, prompts, scorer or original raw. Same pinned existing models: B1 SHA `bb741ebb106d543e9de114b843a3d3d73d51c74b5801e69da2abde821a0cb3e1`, B2 SHA `57d1997790d1744fba5b40a7317df71ea5e2acee28c47e78f0cce39c0703f8cf`, C3 SHA `3d10b6ab8fc91a919534b9558e266255aca0bbc7f6d015963599aa9e74e05b1d`, llama-server b10964 SHA `79e312188dc1d75c28201771f106e91de470b5cebdd838d31bb4db25eecf5d39`. Native jobs serial under `v13-native-c3-ag12-20261030`, no concurrent heavy model owners.

Model-free preflight: six real SQLite Stores, two exact source refs per case, SYNTHETIC B1/B2 observers clearly labeled, fixed JEF `propose` exact source admission, 12 Context OS SHADOW plans, stale USER correction veto, strict JSON scorer, no oracle in C3 prompts, zero native calls/output/actions/learning. Native: six fresh Stores, B2 prior + B1 current + B2 current **18 real native FINAL offers**, 12 real pinned C3 FINAL calls, each model unloaded/reaped; every source/ref, zero-authority JEF candidate, closed Store and negative gate independently checked. Any missing source, model pin, release or quote is structural RED; no synthetic substitution in native, no discarded case.

Strict choice+remaining exact JSON score, no duplicate keys, no extra fields. New prereg exploratory replication signal only if all 12 C3 calls and 18 body offers structurally valid, TYPED_JEF >= **5/6** correct and TYPED_JEF >= RAW_BODY + **2/6**. Otherwise record NO_GAIN; never change threshold after native output. Even signal is **not** causal proof of learned JEF/Body complementarity: deterministic exact-grammar JEF and different arm instructions confound attribution, and six cases are small. No native C2/JEF model, real TTY, Redmi or STEP2 proof.

Negative gates unchanged: Age0 RECORD_ONLY; STEP2_EXIT EVIDENCE_NOT_PASSING; B3 NO_PROMOTION; Body-JEPA UNAVAILABLE; World-JEPA SHADOW; jepa_weight=0; whole V13 INCOMPLETE. Preserve Run111 NO_GAIN, Run113B wrong, Run114B 3/3 vs0/3 and Run105 full-suite RED. Next after result: genuine native C2/JEF control provenance or broader blinded disjoint task families, not a seed971 retune.
