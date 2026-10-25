# Run291 — pinned Linux-native source-first prompt A/B: NOT SUPPORTED

Date 2026-10-25 UTC. Preregistered before execution at `PREREG.md` (candidate suffix SHA256 `e85a1ca602ed5ebcc39272b79edacec7ba591524663eacbd8bc2e0332dcd30b2`). Exact native source head `6855943f5d568f08fc5b64faa958a3cf51866310`; base Run290 checkpoint `5c7c4876c7e50158d5eabc30d5647316549b10d8`.

## Actual measured outcome

**`RUN291_RESULT=NOT_SUPPORTED`**, not a production prompt change and not a memory-retrieval PASS.

Two serial pinned actual-weight integration lifecycles ran on fresh Linux-native installed artifacts, with identical registered fixture, model/seed/source/thresholds and unmodified integration harness. Baseline and ephemeral source-first suffix both had valid exact native prompt capture and source delivery, genuine C3/B1 calls, wrong-topic/different-entity/session rejection and C3 source use. Both `tests/integration_retrieval.py` arms returned 2 / `MEMORY_RETRIEVAL_PARTIAL`, solely because **`native_detail_answer_uses_human_source=false`**.

- Baseline B1 actual: “The topic involves budgeting for Project Kelmo16. I'm considering the financial framework needed. There's some uncertainty about exact figures.” C3 mentioned “400 Euro”.
- Candidate B1 actual: “The topic is about the financial framework for Projekt Kelmo16. I do not have a definitive answer, but here’s what I understand. [uncertain]”. C3 improved to exact “400 Euro”, but B1 still omitted it.
- Both: `native_detail_exact_source_delivery=true`, `native_language_exact_source_delivery=true`, `native_language_answer_uses_human_source=true`, negative retrieval controls true, `diagnostic_valid=true`. No threshold or fixture changed. Candidate **not** promoted.

## Evidence and hashes

- GitHub Actions workflow `40196741577`: source-only 5/5 PASS, official privacy CLEAN; native diagnostic job SUCCESS means **valid experiment**, not native utility PASS. Closed raw artifact `12600522164`, SHA256 `16b3e9f02759f7aa72a66d63d1afb6b209bccbc17c63e688846eec4b987980c2`.
- Raw artifact contains full baseline/candidate `.json`, `.features.json.gz`, `.summary.json`, source/model bootstrap and host logs, per-arm return codes, comparison, privacy and `RUN291_RESULT.json`. Exact source head and model source hashes captured before run.
- `scripts/run291_memory_prompt_probe.py` Git blob `0eac13f93b3e8b3d320f43120657233d78409de2`; unit test `1407c611af0f8ada1b99f36eb55ce2f8ecb45080`; CI workflow `46410a57d618f48a0ac40c41af0eefb289ac92eb`; prereg `0a146bda6bd8fdfc96499b208e40bf58815bda15`.
- Full raw ZIP stored in private ChatGPT Library `/V13-Inquisition/Proofs/Run291/V13_Run291_Native_Prompt_AB_Raw.zip`; downloaded back and SHA256 matched `16b3e9f02759f7aa72a66d63d1afb6b209bccbc17c63e688846eec4b987980c2`. Rejected anyone-writable Drive destination not used.
- Canon SHA256 `3423906b01b24443fcef733fb5c7ef47296963df63e603d8f843c99d544877ee` unchanged.

## Boundaries and next work

The source was delivered and verified but B1 failed to use it under both prompts. A stronger instruction alone did not solve this registered case. Do not change production prompts on this result. Next native utility work should investigate an explicit source-bound output channel / B1-C3 integration with original provenance and abstention gates, **without** substituting C3 output for B1 in the unchanged acceptance test. Run292 separately owns the latewatch learned-wake conflict and a serialized native wake-only retest; PR284 Runtime cancellation remains owned/RED. Independently, Run288 output-adapter metrics suggest a bounded-bias feasibility problem requiring rigorous raw-feature proof before algorithm change.

`STEP2=UTILITY_FAIL`, `B3 L1=FAIL`, `Body-JEPA=UNAVAILABLE`, `jepa_weight=0`, `Redmi=UNMEASURED`, `V13=INCOMPLETE`. No AGI/full-system claim.
