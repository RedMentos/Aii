# HB1b prereg addendum — isolate output-format variable before native calls (2026-10-29)

Original immutable prereg: `HB1B_C3_FORMAT_SOURCE_PREREG.md`, first committed at `4b4978c4ed55b0397ca03ff930bf06477f8d5137`, Git blob `16f328584fb9678a034ee8fa9234460f4fbcfc4e`. No HB1b native model calls have occurred.

**Observed source-code confound before execution:** pinned `v13/code/v13/runners.py` Git blob `efda7aa1aa5729e974d0d641870d4da05d21c961` applies `C3_DECODER` anti-echo sampling only when `schema is None` and `c3_sampling == "anti_echo"`. If HB1b inherited the HB1a `anti_echo` configuration, plain and schema arms would differ in **both** output format and sampler settings. That would make the registered format comparison uninterpretable.

**Prospective correction:** for all four HB1b arms set `c3_sampling="off"` (a non-`anti_echo` value) in the isolated C3 RunnerPool configuration. Keep `temperature=0.1`, `top_k=50`, `repeat_penalty=1.05`, seed 13, threads 2, context 2048, max 48 tokens identical. JSON schema is still supplied only to `*_schema` arms, as preregistered. This changes no HB1a raw/score, model/runner source or model weights, and does not enable any live runtime switch. Add a source-only regression that checks the runner's conditional anti-echo branch and the fixed HB1b config before native execution.

This addendum is committed BEFORE implementation of the HB1b native executor and before any HB1b native run. It is a methodological correction to isolate the intended experimental variable, not a post-result rescore. All negative gates unchanged.
