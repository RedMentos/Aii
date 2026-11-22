# Run68 JEF/C3 native JSON-schema constrained formatter — prereg 2026-10-31

**Owner:** GPT-6 scheduled continuation. New review-only child of Run67 terminal RED PR #1427 at exact `8cf020737f779089d4e9e6534fa21bf5347b9c7c`. Commit and remote-readback this protocol before implementing candidate or launching native. Preserve original Run63/65/66/67 scores and artifacts, registered seeds and source/model/runner hashes. No retune of Run67 observed cohort. **Goal:** test an actual native *constrained-decoding interface* rather than another free-text prompt variant; this is a formatter-copy task with the source-verified action already present, not autonomous reasoning or STEP2 utility.

**Fresh prospective cohort:** seed **727**, six new project IDs `P2X6AE8B9E90F38B8C3`, `P2X0D9B2BECB7624D9B`, `P2XD6D8E3441A568154`, `P2X56274072C1B5EAF6`, `P2XE42AC6C049A5E815`, `P2X302EC23C5BB11303`; expected typed JEF actions **A/B/NONE/A/B/NONE**. Source grammar unchanged: each project current request + one archived policy + one latest sheet, source-verified through existing Store/Memory/JEF envelope; disjoint project IDs and full source strings from original P2X and Run67 seed619. Frozen (domain, first-field/unit, second-field/unit, flag; max1,max2,required; A first,second,flag; B first,second,flag):
```
0 harbor permits; permit fee credits; review window cycles; insured; (210,30,true); (155,20,true); (250,14,true) -> A
1 museum exhibits; floor area cells; opening window slots; accessible; (190,25,false); (220,10,false); (175,18,false) -> B
2 robotics workshop; kit cost tokens; setup window beats; reusable; (120,15,true); (105,16,true); (110,10,false) -> NONE
3 greenhouse sensors; power budget units; warmup window steps; shielded; (280,32,false); (200,24,false); (245,19,true) -> A
4 library storage; shelf quota places; transfer window intervals; covered; (240,25,true); (210,15,false); (230,20,true) -> B
5 festival catering; meal allocation portions; delivery window ticks; verified; (130,12,false); (135,11,true); (125,13,true) -> NONE
```
Frozen canonical table `json.dumps(rows,sort_keys=True,separators=(',',':'))` SHA256 **`84f4f482b09310dcde62dfb867078024423886abbcb2740d20e4e6c8747ec7b1`**. Project ID `'P2X'+sha256(f'JEF727|727|{index}'.encode()).hexdigest()[:16].upper()`.

**Two fixed arms, balanced order:** `BASELINE` calls exact original typed JEF envelope, no schema, output strict byte equality to A/B/NONE. `SCHEMA` calls **the identical original messages** with the existing `LlamaRunner.generate(..., schema=SCHEMA, ...)` native `json_schema` argument, no prompt text change. Frozen schema:
```json
{"type":"object","properties":{"action":{"type":"string","enum":["A","B","NONE"]}},"required":["action"],"additionalProperties":false}
```
Parse SCHEMA output with strict standard `json.loads`: exactly one object key `action`, value one of three tokens; score 1 iff parsed action equals source-verified action, no strip/casefold/posthoc semantic rescoring. Preserve original raw **synthetic-only** model output privately in closed artifact for independent parsing (no personal user content); public result may show only scores/hashes. Cases even BASELINE→SCHEMA, odd SCHEMA→BASELINE. Same pinned C3 GGUF SHA256 `3d10b6ab8fc91a919534b9558e266255aca0bbc7f6d015963599aa9e74e05b1d` and llama-server SHA256 `79e312188dc1d75c28201771f106e91de470b5cebdd838d31bb4db25eecf5d39`, temperature0, generation seed727, max32, <=90s per call, unload/reap each process. No model change, training, human TTY, output/tool/learning authority.

**Engineering gate:** all 12 native FINAL, exact source refs, same model/runner, no cross-project source, process reaped, Store closed, no visible output/TTY/tools/learning; every original raw stage and SHA/CRC preserved. If native schema unsupported, report `STRUCTURAL_RED`, never silently fall back. **Diagnostic scientific success** iff SCHEMA exact parsed score >=4/6 and advantage over BASELINE >=2/6; otherwise `SCHEMA_FIDELITY_RED`. Any parsing failure scores 0. Independent verifier must reparse original synthetic-only native outputs, verify hashes, scores and frozen cohort. No result can promote general C3 fidelity, STEP2, B3, Body-JEPA, World-JEPA, jepa_weight, Age, Redmi or whole-system completion.

**Next:** implement immutable fixture, schema runner, independent report verifier and negative tests; software CI then one serialized native workflow under existing `v13-native-c3-ag12-20261030` group. Stop and preserve RED if any native pin/source/permission/runner schema mismatch.
