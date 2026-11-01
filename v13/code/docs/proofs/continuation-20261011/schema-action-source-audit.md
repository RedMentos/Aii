# Schema action source audit — 2026-10-11

This is read-only source evidence and a preregistered diagnostic, not a causal finding or an acceptance rerun. No frozen runtime, harness or STEP2 fixture has been changed.

## What is actually sent

`tests/integration_step2_utility.py` calls the ordinary `LlamaRunner.generate` directly with its decision schema. No first-token output bias is supplied. `v13/runners.py::_generate` places the schema under the native `/completion` payload key `json_schema`; it does not use the OpenAI `response_format` wrapper. C3 anti-echo settings apply only without a schema, so they do not explain this particular structured cohort.

`v13/common.py::dumps` sets `sort_keys=True`. `_generate` sends `dumps(payload)` as the HTTP body. Therefore the *wire* order is `action`, `options`, `project`, despite the schema being authored with `project` first. Each option is forced through `cost`, `days`, `eligible`, `entity`, `local`, `remaining`.

The pinned local llama.cpp-b10964 source corroborates the decoder constraint:

- `common/json.cpp` implements `common_json` using `nlohmann::ordered_json`, preserving the parsed wire order.
- `common/json-schema.cpp` builds the schema object's property vector in that iteration order.
- `common/json-schema-to-grammar.cpp::_build_object_rule` appends required properties in that vector order, emitting them sequentially.
- `tools/server/server-common.cpp` forwards native `json_schema`; `common/chat.cpp` converts it to grammar. The wrapper accepts `response_format` as another input route, but the running application does not take that route.

The grammar thus requires the final choice before the later calculations and eligibility fields. This is a plausible output-order handicap for a small decoder. It does **not** prove that this explains the observed action collapse; the fixed original cohort remains unchanged and its failures stay valid.

## Model and template evidence

The installed C3 GGUF is the catalog's LFM2.5-350M-QAD-Q4_0, model SHA256 `3d10b6ab8fc91a919534b9558e266255aca0bbc7f6d015963599aa9e74e05b1d`, pinned revision `657e078c94084481950a2d555a941481f715536b`. Offline GGUFReader inspection of the actual file found `general.architecture=lfm2`, `general.finetune=QAD`, BOS token ID 1, EOS token ID 7 and an explicit `tokenizer.chat_template`.

That template handles a leading system message, renders user and assistant roles with ChatML markers and appends `<|im_start|>assistant\n` for generation. Therefore a missing template is not supported by this inspection. Runtime `/apply-template` output will be persisted by the new probe. The 350M file is not labelled `Instruct` in the catalog; this alone neither proves an incorrect model nor establishes model capabilities.

The previous 230M catalog entry has SHA256 `e75f83268de11b2a1bcfab5f3b5c5c0c97569ddbbc0990aad88437e45b8ba292`, revision `cdf97bd8205908758f44aec508d68ac1aef98f5c`. Its actual file/template has not been inspected in this check. Offline historical analysis reports 65 A and 5 UNKNOWN actions, whereas the observed 48-row current snapshot reports 48 NONE actions. The historical 230M run is not a known-good semantic control; runtime and inputs also changed. Do not claim the model switch caused the collapse from this comparison.

## Prepared isolated diagnostic

`scripts/schema_action_probe.py` preregisters eight new generic cases: four explicit copy labels A/B/NONE/UNKNOWN and four small arithmetic decisions spanning the same labels. It does not read the acceptance fixtures, historical answers or current STEP2 report. Each case receives four arms:

| Arm | Constraint and interpretation |
|---|---|
| free_json | Same full output instruction, no schema; no anti-echo sampling change. |
| action_only | Action enum schema; smaller output task, explicitly disclosed. |
| schema_action_first | Full schema serialized using the application's sorted-key convention. |
| schema_facts_first | The same full schema and inputs, with preserved schema property order: remaining, eligible, action. |

The two full-schema arms use equal parsed schema constraints, instructions, input, seed, sampling settings and token budget. The only intended difference is HTTP key serialization order. The actual request wire and parsed schema property order are saved per row, along with native template response, raw native completion, tokens/timing, strict action/full-output scores and failures. There are 32 planned calls. The new output directory refuses overwrite, checkpoints after every completed response and hashes the actual model, launcher, adjacent shared libraries and relevant Python sources. No installed application configuration, adapter or sparse memory is activated. The isolated server strips inherited memory variables, binds localhost and is reaped after the run.

Six offline tests pass, including actual-wire ordering and semantic-schema equality, equal free/schema sampling, complete enum coverage, strict failed-output handling and separate action/full-field scores. No native probe calls were made while the frozen 70-case cohort was running. Run only after root confirms that cohort is done:

```bash
python3 scripts/schema_action_probe.py --binary /workspace/scratch/5a9214d3f329/native-audit-cache/bin/llama-server --model /workspace/scratch/5a9214d3f329/native-audit-cache/models/language/LFM2.5-350M-QAD-Q4_0.gguf --out docs/proofs/continuation-20261011/schema-action-350m
```

Diagnostic completion means all planned observations were recorded; it never means acceptance, utility, training or production activation passed. Any runtime serialization change belongs to a later separately tested candidate, following these observations.
