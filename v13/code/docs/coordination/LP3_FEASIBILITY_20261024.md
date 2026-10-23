# WP-LP3 feasibility — 2026-10-24

Read-only assessment; no model loaded or trained. Original LP1/LP2 protocols and trainer remain unchanged.
The separate candidate, if implemented, is a research-only HF-master experiment with zero runtime authority.
It is neither B1/B2 plasticity, B3 permission, Context OS re-entry nor genuine transformer-layer re-entry.

## Exact recovered inputs

- LP2 script SHA256: `266518776365677379086eb8f2a7cd104f6cf8fc19f144880cfdb4c70a98f324`.
- Frozen trainer: `45ee09f701239d2a09285edcc970d87652e2cadc17f43bc3c4fe3b546d8895cb`.
- Prompt-boundary candidate: `e98e810b039ff329837cb5ccf6d264dee91c622f58cad4a895d4be0491003c1e`.
- LP1/LP2 HF-master weight SHA256: `1c9c77a4471a7f590f85240f74ed1fc26df7fbde88c3006724e2f93ca993ea4e`.
- Matching upstream snapshot recovered from official file history:
  `LiquidAI/LFM2.5-350M@55e5a53e8637c4522a0577040fe68682db3fbbb6`.
  [Official commit](https://huggingface.co/LiquidAI/LFM2.5-350M/commit/55e5a53e8637c4522a0577040fe68682db3fbbb6);
  [weight pointer](https://huggingface.co/LiquidAI/LFM2.5-350M/blob/55e5a53e8637c4522a0577040fe68682db3fbbb6/model.safetensors).
  Accessed 2026-10-24; CURRENT source, matching weight bytes. Historical LP2 did not hash tokenizer/config bytes, so
  matching this snapshot cannot retroactively prove historical tokenizer identity.
- Bind config.json, generation_config.json, tokenizer.json, tokenizer_config.json, chat_template.jinja and LICENSE from
  that same snapshot before execution. License identifier is LFM Open License v1.0; preserve it and do not redistribute
  master weights in a code checkpoint.
- Deployed Q4 is a different path: revision `657e078c94084481950a2d555a941481f715536b`,
  SHA256 `3d10b6ab8fc91a919534b9558e266255aca0bbc7f6d015963599aa9e74e05b1d`.
  Old AG6 used a different master beginning `9e6c6ccf`; do not merge those cohorts.

Default project Python initially had none of torch/transformers/peft/safetensors/gguf. Root subsequently prepared an
isolated environment with torch 2.10.0+cpu, transformers 4.57.6, peft 0.18.0, safetensors 0.8.0 and tokenizers 0.22.2.
No master was initially present; root owns retrieval of the pinned snapshot. Current cgroup limit is 8 GiB; run one
heavy worker at a time and measure real RSS. Serial sample-gradient accumulation avoids retaining all 16 example graphs.

## Feasible causal path

Official [LFM2 implementation](https://github.com/huggingface/transformers/blob/main/src/transformers/models/lfm2/modeling_lfm2.py)
was inspected (blob `d52d5bf2847c229b3f227ecdaaf6364454adfb30`, accessed 2026-10-24). It accepts inputs_embeds and supports
causal attention plus convolutional state. The installed version must pass its own API/bare-embedding equivalence
check before using real data. [Official configuration](https://huggingface.co/LiquidAI/LFM2.5-350M/blob/55e5a53e8637c4522a0577040fe68682db3fbbb6/config.json)
sets hidden width 1024, EOS 7 and pad 0; derive these from the pinned tokenizer/config instead of copying constants.

Candidate: query-only forward → last prompt state h → residual predictor P(h) → small learned projection → one bounded
native-input soft-prefix slot → a second C3 forward answering the original query. CE must traverse the prefix path;
NCE aligns predicted states to stop-gradient slow answer targets. No target token or item index enters the query
encoder during evaluation. The prefix uses a trained projection and embedding-scale calibration, not an uncalibrated
foreign hidden vector.

Four training arms: CE+KL; PREFIX_NO_NCE; PREFIX_NCE_OK; PREFIX_NCE_SHIFT. Each uses the same LoRA scope (w1–w3), optimizer,
seed, dataset and step count. Within the same trained correct model, compare active prefix, zero prefix, shifted
query-derived prefix, static mean prefix and removed prefix. Prefix removal changes positions/conv context; it is
not equivalent to zeroing a slot. Run the same extra query pass for CE and report measured wall cost; make no compute
or efficiency claim from matched step counts alone.

A memory-key variant (predicted state chooses an exact provenance-linked fact) is an optional retrieval positive
control. It can prove retrieval contribution; it cannot establish a learned latent decoder, body plasticity or JEPA
utility. Do not silently substitute it if genuine soft-prefix execution fails.

## Pitfalls and verification requirements

- Reusing `_greedy` with inputs_embeds can truncate real output: HF generation without input_ids may return only new
  tokens, while `_greedy` blindly slices len(prompt). Use an explicit bounded greedy decoder or verified cache adapter.
  Initially use no-cache full forwards for all arms, resetting hybrid conv/cache state between independent queries.
- Prefix training labels require a masked prefix position in addition to masked prompt positions. Check the full
  prompt survives and target tokens exist. The boundary candidate alone permits only one remaining prompt token;
  the new short fixed cohort should reject any truncation at all rather than use that loophole.
- Compute h from query alone; reading h from the end of a prompt+answer sequence risks target leakage if indices drift.
- LP2 target answers are bare text states, not a general theorem about future world states. Report the exact target.
- Old `answer_hit` is substring/any-key: 4417 can match 14417, one birthday component can count as a hit, and “redmi”
  does not prove the full model name. Freeze an explicit per-fact scorer with token boundaries and all required fields;
  retain old metrics only as historical diagnostics. Negated/conflicting answers must not earn a new strict hit.
- The 32 LP2 held-outs and five published failures are now development/diagnostic data. Freeze new paraphrases before
  running; report the old failures separately, never select a new primary set by observed model errors.
- LP2 resumes solely by (arm, seed), writes rows without fsync and saves no predictor/optimizer state. New experiment
  needs complete source/model/config/dataset bindings, atomic durable optimizer/predictor/LoRA/RNG checkpoints,
  one-row-per-key integrity, immutable failed attempts and fail-closed incomplete cohort status.
- Preserve CE/KL/NCE gradient attribution separately for LoRA and predictor; one sampled gradient diagnostic is not a
  full-batch gradient proof. EMA must follow actual updates and be included in a resumed checkpoint.
- Benefit requires correct-prefix answer gain beyond both CE and same-parameter no-NCE baseline, causal degradation
  under shifted/zero/removed intervention, unchanged near-miss/retention guards and independent seeds. A latent score
  increase or nonzero gradient alone never closes LP3, STEP2, B3, a phone gate or full-system completion.

## Bounded proposed next cohort

Freeze protocol before measurement: 4 arms × 2 seeds × 12 full-batch steps, one slot, rank-8 LoRA, bounded 24-token
answers, exact full-prompt retention, source-bound rows/checkpoints and a hard process budget. This is a small pilot,
not a substitute for fresh larger replication. H1: finite nonzero applied NCE gradient into intended LoRA/predictor
paths; H2: fresh strict answer hits beat CE and PREFIX_NO_NCE by a prespecified paired margin on both seeds; H3:
correct-prefix utility exceeds shifted/zero/removed interventions; guard: no extra contradiction/leakage and bounded
probe drift/forgetting. Thresholds and exact fixture bytes must be chosen and committed in the new PREREG, never
retrofitted to outcomes. Incomplete/duplicate/stale/tampered rows never produce PASS.
