# JEF→C3 formatter recency probe — disjoint six-case prereg (2026-10-31)

**Owner:** GPT-6 scheduled continuation. Review-only child of original Run66 PR #1424 exact HEAD `4ba8717f7a6e27b20673c1197ce642b837b3ca0e`. **Commit and remote-readback this registration before writing any runner, test, workflow or native run.** No changes to original P2X/Run63/65/66 cohorts or scores, Canon, production Runtime, native runner/model or any existing source hash. This is a separate fresh synthetic-source *formatter-copy fidelity* diagnostic, **not** second-attempt utility, reasoning, training or safe delivery.

**Frozen prospective cohort:** seed **619**, six new project IDs `P2X282ED33426B9995B`, `P2X3F5F6BD92028DADD`, `P2XFEA846052E574D2C`, `P2X934BE0D650CBBB78`, `P2XB12AEB2D637A1025`, `P2X0765323444E23BCE`; expected deterministic typed JEF actions **A/B/NONE/A/B/NONE**. Each case has exact two independent synthetic human-source strings (archived policy and latest option sheet) plus current user request. Domain/field/units: (festival venue, rental fee tokens, access window ticks, covered), (workshop equipment, kit size blocks, assembly window beats, reusable), (community garden, water allocation drops, setup window cycles, shaded), (satellite mockups, payload mass units, spin up window steps, shielded), (exhibition crates, container volume cells, opening window slots, insured), (classroom planning, seat quota places, preparation window intervals, accessible). Fixed (max1,max2,required; A first,second,flag; B first,second,flag) by case:

```
0 (150,20,true); (100,12,true); (160,12,true) -> A
1 (180,18,true); (220,10,true); (140,14,true) -> B
2 (120,12,true); (150,9,true); (90,16,true) -> NONE
3 (300,25,false); (120,18,false); (220,12,true) -> A
4 (200,24,true); (170,20,false); (185,15,true) -> B
5 (100,10,false); (120,8,true); (90,15,true) -> NONE
```

Table canonical `json.dumps(rows,sort_keys=True,separators=(',',':'))` SHA256 **`69b2d02675ca2bcddce00f87a70265ff9aab024ff62d2b063369d60232090ee3`**. Generated project ID rule `'P2X'+sha256(f'JEF619|619|{index}'.encode()).hexdigest()[:16].upper()`. Source strings follow existing `jef_typed_source_shadow` grammar. Reject any project/source overlap with original P2X 360 rows and wrong source-only oracle.

**Frozen arms:** `BASELINE` = original exact `build_jef_c3_typed_envelope(...).messages` (no changes); `RECENCY` = same verified two-role envelope with a third USER role containing exactly `Verified JEF action: <A|B|NONE>. Copy that token only.` appended. This intentionally repeats the **already-authorized typed JEF action** for a formatter task, not an independent oracle/learning target. Order even case BASELINE→RECENCY, odd case RECENCY→BASELINE. Each native call separate unloaded process, same pinned C3 model SHA256 `3d10b6ab8fc91a919534b9558e266255aca0bbc7f6d015963599aa9e74e05b1d`, llama-server SHA256 `79e312188dc1d75c28201771f106e91de470b5cebdd838d31bb4db25eecf5d39`, temperature **0**, generation seed **619**, max tokens **32**, bounded deadline **90s**. No model substitution.

**Score fixed before native:** exact UTF-8 output equals `typed_jef_action` (strict 0/1), *no trim, casefold or rescoring*. Structural gate: 12/12 actual C3 FINAL with pinned hashes, all processes reaped, source-verified prompt and Store closed, no FINAL/output/TTY/tool/learning, original negative gates intact. Diagnostic candidate success iff RECENCY strict >=4/6 **and** RECENCY−BASELINE >=2/6; otherwise `RECENCY_FIDELITY_RED`. Structural fail is `STRUCTURAL_RED` regardless of score. Report both arm counts, all output hashes and redacted source hashes, no raw source/output published. Preserve original failures and raw. No positive result promotes C3 general fidelity, STEP2, B3, Body-JEPA, jepa_weight, Age or Redmi.

**Checks:** software fixtures/source admission, negative malformed and swapped sources, no output/tool/learning, hash pin refusal, independent report verifier and CRC/SHA256 manifest. Run heavy Linux-native only under existing `v13-native-c3-ag12-20261030` serialized owner group. No native execution until prereg remotely verified. Actual Redmi/real TTY require separate user/device action.
