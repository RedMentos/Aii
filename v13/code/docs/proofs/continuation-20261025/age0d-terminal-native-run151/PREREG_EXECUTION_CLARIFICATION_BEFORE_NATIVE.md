# Run151 execution settings clarification — before native launch

This note is additive to `PREREG_CORRECTION_BEFORE_NATIVE.md` and supersedes the provisional 32-token / ctx512 line in the first PREREG. The actual pinned Run147 harness source uses **context_tokens=1024, answer_tokens=48, max_tokens=48, threads=2, per-call deadline=45 seconds**, temperature inherited from unchanged Run147 config, and per-question sampling seed **15132 + row id**. Run151 preserves those exact values to isolate the checker change. Global CI timeout 840 seconds; native concurrency group unchanged. The original prereg seed 15131 / task hash was never run.

Binding cohort: seed 15132, exact Run147 task generator with 24 per stratum, 288 rows, SHA-256 `9418de94428bb51a42d4d5e292ab9f5ef5e94acea61382d3f88c1694a7712144`. All source/runner hashes and negative gates unchanged. This clarification is committed before creating the native workflow or starting a model.
