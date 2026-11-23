# Run117Q — original Run116 native causal-attribution audit (read-only)

## Scope and source

Separate review branch `assistant/v13-run117q-native-attribution-audit-20261031-hourly11` based on exact Run117P review HEAD `60ab0f7f82173a0f451f893e746741f7a3eac694` (#1496). Does not alter Run116 original native #1494, independent raw auditor #1495, frozen seed1019 cohort, original scores, source/model hashes or production Runtime. No new native call, output, tool, learning, approval or age promotion.

Original Actions 41224639354, native source HEAD `df08a4ce311317bdfd322ba7c7520d9fe8fb2b93`, artifact 13051756857 SHA256 `71de9bb7bc2899f5aee67f58b55d13514d0a9b0d870cd98ae5e8f2f1850d11c5`. Independent Run116 original ZIP audit has already verified all 18 native body calls and 18 native C3 calls, 27 inner hashes and 2199 source hashes; private byte-identical original is stored in `/V13-Checkpoints/2026-10-31/Run116-Native-Pilot/`.

## Independent causal-attribution finding

`run117q_native_attribution_readonly.py` recomputes each arm's JSON output against the **original frozen fixture oracle**, not the original score field. It independently verifies original ZIP SHA, ZIP CRC, all 27 SHA256SUMS, source HEAD, native exit, fixture SHA, 6 ordered cases, 18 native C3 FINAL/reaped receipts, two exact USER sources per arm, prompt hashes, source-role separation, and that the typed candidate already equals the fixture oracle *inside the USER-role prompt before C3*. Original scores must match independent recomputation or fail closed.

Result on the **original** 15,336,958-byte ZIP: RAW_TWO_SOURCE_ROLE 1/6, TYPED_JEF_ROLE 6/6, TYPED_JEF_WITH_BODY_ROLE 6/6. Paired raw→typed improved **5**, worsened **0**; typed→typed+Body improved **0**, worsened **0**. Median C3 prompt tokens: raw **538.5**, typed **686.5**, typed+Body **1626.0**. This prompt-length difference and deterministic answer injection are confounds: the typed C3 system prompt explicitly tells it to **copy** the answer supplied by deterministic JEF. This verifies formatter-copy noninterference on six synthetic examples, **not C3 independent reasoning improvement, Body added utility, JEPA learning, STEP2 utility or generalization**. B1/B2 native runs are real, but no incremental benefit appears in this particular cohort; this does not prove Body has no value in other tasks.

Local original read-only result SHA256 `124b8dc30279c3c855e2308321f9c907eeb55491916d25df0798de9f7d7c4bb5` in private Library. New 7 synthetic tampering tests pass, including forged answer-in-prompt, raw-arm leak, score/JSON tamper, prompt hash/source drift, missing native receipt and wrong outer artifact. **Combined new + inherited source tests 64/64 PASS**, Python 3.13 software/Linux, raw SHA256 `836365743984c18afe2d1e34f7e9a4dc6f07dee450a839ffc8268e9d923a320b`, compile PASS. Synthetic tests are not native execution; original Run116 artifact is the sole native source.

New source SHA256 `976187d69801c6ba75d5134c25d82be15fe11df4b92714378fdcce038fe1d5f8` / Git blob `fbff7e858b8c98e1bdd8a689221a25abeb99c7b9`; test SHA256 `3e72da45d5e1f9e056e68b74bde750b75aa706dfb2f10c24a55d2488a6e7191f` / Git blob `7a0ceffbce2283da4eb61800ad4d0700735544f4`. Git blobs fetched from review branch and match local. No private data committed. Raw results and source in private `/V13-Checkpoints/2026-10-31/Run117Q-Attribution/`.

## Next and negative gates

- CI: download exact original artifact with GitHub Actions `actions:read` (no paid provisioning), verify original bytes, run independent read-only audit + 7 synthetic tests + compile/privacy/diff, close SHA256SUMS; back up original CI receipt privately. Do not replace original native ZIP or rewrite historical score.
- Next functional package: register **new disjoint** tasks where Body carries useful independently source-verified information not already fully available in the raw/JEF prompt; compare against deterministic-JEF-only and single-body controls. Freeze design, model/source/seed and acceptance before native calls. Otherwise 6/6 formatter copying does not establish complementarity.
- `STEP2=UTILITY_FAIL`, `B3=NO_PROMOTION`, Body-JEPA unavailable, `jepa_weight=0`, World-JEPA SHADOW, age0 RECORD_ONLY, Redmi unmeasured, no native JEF/C2 in Run116, whole-system incomplete. Do not activate this diagnostic as a production output or decision gate.

Reproduce on a verified local copy of original artifact:

```sh
cd v13/code
python -m scripts.run117q_native_attribution_readonly --original-zip ORIGINAL_RUN116.zip --out ATTRIBUTION.json
PYTHONPATH=. python -m unittest -v tests.test_run117q_native_attribution_readonly
```
