# Run13L — prospective C3 system-level abstention contrast (2026-10-30)

Owner GPT-6. Review-only child of Run13K #1301 at `edaf8f5354ffc4f9d7091f705af7ceed17d75488`. **Preregistered before fixture/code/native.** Run13J and Run13K remain untouched and RED on source-bound native copy (Run13K 12/12 literal `ABSTAIN.`, both arms).

## Locked cohort and intervention

- New disjoint six-source **seed251**, projects Atlas251, Beacon251, Canyon251, Delta251, Ember251, Forest251. Fixture schema `v13.run13l.c3_system_abstention.fixture.v1`, sorted compact cases SHA256 `ccf9e0aebdf5a4376f2b3a0b65460cce5dd1ac3198ac3dde189080f3dbeb4473`. No reusing seed227/239 source names/cases. Each case has two named options with budget, cost and different completion days.
- Both arms receive the **same** Run13K `COPY_DIRECT` user prompt constructed from the same source-verified Run13I/Run13E/Store/ContextOS JEF exact answer. Only the **system** instruction changes:
  - `SYSTEM_ABSTAIN`: exact frozen Run13J `SYSTEM` = `Give a concise factual answer about remaining budgets and the faster option. Do not invent values. If you cannot answer, say ABSTAIN.`
  - `SYSTEM_COPY`: exact new string = `You are a literal text copier. Reproduce only the text between BEGIN_VERIFIED and END_VERIFIED from the user message, preserving names, numbers, punctuation and line breaks. Do not calculate, explain, or add text.`
- Identical source facts, model, seed251, temperature0, 128 max output tokens and no active chat. Even-index SYSTEM_ABSTAIN first, odd-index SYSTEM_COPY first. Fresh isolated Runtime/Store per source, real native C3 only, model unload/reaping between arms. Pinned model `LiquidAI/LFM2.5-350M-GGUF` revision `657e078c94084481950a2d555a941481f715536b`, file SHA256 `3d10b6ab8fc91a919534b9558e266255aca0bbc7f6d015963599aa9e74e05b1d`. No change to registered model/source/scorer.
- Preregistered outcomes: exact output byte-for-byte equals verified JEF answer, Run11V numeric pair correct (2 per source), Run12N explicit faster correctness, strict full 2/2 numeric + faster, literal `ABSTAIN.` count, actual native FINAL and process reaped. No posthoc whitespace normalization or threshold change. Paired descriptive differences only; n=6 cannot prove generalizable utility. All failed attempts and original raw outputs retained.
- Software preflight checks fixture hash/disjointness, source-witness binding, exact shared user prompt, system strings, pairing, tamper and negative gates. Actual Linux-native workflow serialized under `v13-step2-budget-paired-native-20261030`, pinned sources and isolated public model bootstrap, 12 calls and independent read-only replay.

## Safety and interpretation

A difference would show **system-prompt sensitivity** on a frozen synthetic source-bound copy task, not actual new knowledge, model learning, JEPA, C2 control, B1/B2 complementarity, Redmi utility, STEP2 or whole-system completion. No live egress, tools, permission changes or training. Age0 RECORD_ONLY, STEP2 UTILITY_FAIL, B3 NO_PROMOTION, Body-JEPA UNAVAILABLE, jepa_weight0, Redmi unmeasured, canonical and user full scope incomplete.
