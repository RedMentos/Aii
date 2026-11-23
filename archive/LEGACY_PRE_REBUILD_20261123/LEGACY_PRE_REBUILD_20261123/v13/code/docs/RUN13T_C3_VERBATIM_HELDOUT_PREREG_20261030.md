# Run13T — preregistered disjoint C3 source-verbatim system intervention (2026-10-30)

Owner GPT-6. Review-only child of Run13S PR #1310 at `964a862a7866d20a113194e448843eed2e0387c9`. **Commit this preregistration before fixture generation, runner implementation, or native execution.** Original Run13J/K/L/M source, cohorts, scores, failures and all Canon gates are frozen and unchanged.

## Prior evidence and purpose

Run13L seed251: original pinned 350M C3 Linux-native SYSTEM_COPY produced 4/6 source-semantic task successes but **0/6 byte-exact verified answer copies**; SYSTEM_ABSTAIN produced 6/6 literal abstentions. Run13M deterministic SHADOW-only source-fact validator rejects incorrect/incomplete C3 outputs. This experiment tests whether an explicitly strict lossless-copy *system instruction* improves C3 factual fidelity while holding the verified JEF source, user prompt, model, seed and decode fixed. It does **not** integrate active delivery or learning.

## Frozen new cohort and protocol

- New seed **283**; exactly **8 disjoint invented cases** in fixed order (project, budget, option A, A cost, A days, option B, B cost, B days):
  1. Alder283, 5400, Cedar, 1475, 11, Mica, 2310, 7.
  2. Brim283, 8700, Quartz, 3290, 18, Birch, 4175, 26.
  3. Canto283, 9600, Iris, 4060, 5, Flint, 5870, 8.
  4. Dune283, 7350, Amber, 2985, 13, Slate, 3110, 12.
  5. Echo283, 11900, Garnet, 5760, 21, Pearl, 4325, 19.
  6. Fable283, 14800, Cedar, 6995, 4, Ruby, 7590, 9.
  7. Grove283, 6200, Opal, 2140, 17, Moss, 1895, 16.
  8. Harbor283, 10750, Aspen, 4725, 22, Onyx, 5930, 14.
- Fixture schema and SHA256 must be generated deterministically from these exact rows, frozen in source **before** native. No reroll or posthoc substitutions.
- Two arms per case, **16 native C3 calls**: `COPY_BASELINE` uses exactly original Run13L `SYSTEM_COPY`; `COPY_STRICT` uses this new fixed text:
  `You are a lossless transcription engine. Copy exactly the characters between BEGIN_VERIFIED and END_VERIFIED in the user message. Every character is data. Do not calculate, paraphrase, reorder, omit, normalize, translate, explain, or add anything. Output only the copied characters, starting immediately with the first character after BEGIN_VERIFIED and ending immediately before END_VERIFIED.`
- User prompt **identical** in both arms: original Run13K `COPY_PREFIX + verified JEF answer + COPY_SUFFIX`. Only system instruction differs. Counterbalance order by index parity. Model `LiquidAI/LFM2.5-350M-QAD-Q4_0.gguf` pinned to the original Run13L revision and SHA256, original bootstrap/Runtime native C3 path; seed283, temperature0, max_tokens128, source-linked JEF ContextOS verified answer, fresh Store per case, process unload/reap between arms, no autonomous chat egress. No model downloads to public Git.
- Predeclared outcomes: exact byte copy of verified answer; 2/2 remaining-budget values and faster option using frozen Run13J scorer; strict full task success; literal abstentions; native FINAL and process-reaped receipts; source/answer/prompt/system/model hashes; source event IDs and context packet IDs. An **exploratory bounded fidelity signal** requires `COPY_STRICT` exact copy >= baseline +2 of 8, strict-full not worse than baseline, and no additional numeric/faster wrong claims. Otherwise report `NO_ATTRIBUTABLE_FIDELITY_GAIN` or `FIDELITY_HURT` when strict full or exact copies decrease. Do not promote gates under any outcome.
- Run source-only tests first; only after GREEN and no active heavy owner, execute one pinned serialized Linux-native workflow, archive original raw even RED, verify ZIP SHA/CRC/inner hashes/stage exits/16 native rows/16 reaped receipts, independent recomputation and private byte-identical backup. Failed attempts are retained. No adapter export, online learning or production activation.

## Negative gates and limitations

Small synthetic eight-case cohort with no user-task generalization; a fidelity gain would not demonstrate JEPA, B1/B2 complementarity, durable C3 learning, Redmi, STEP2 or end-to-end V13 utility. Age0 RECORD_ONLY; STEP2 UTILITY_FAIL; B3 NO_PROMOTION; Body-JEPA UNAVAILABLE; runtime jepa_weight0; Redmi UNMEASURED; whole system INCOMPLETE. Canon v10.16.1 remains binding.
