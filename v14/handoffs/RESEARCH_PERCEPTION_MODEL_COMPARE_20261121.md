# Research & Perception handoff — 2026-11-21

## Ownership and scope

- Queue item: V14-005, Research & Perception, model-candidate evaluation.
- Base: gpt6/v13-private-remote-bridge-20261111 at verified commit c3c32c05a0374e970d274f8a777a7ab85c067d66.
- Working branch: research-perception/model-compare-c3-20261121.
- This is a C3-only first slice. It does not close the broader B1/B2 sparse-MoE or whole-Canon requirements.

## Implemented

- v14/experiments/model_candidates.json pins the existing registry's previous C3 candidate LFM2.5-230M-GGUF: revision cdf97bd8205908758f44aec508d68ac1aef98f5c, QAD_Q4_0, 149081056 bytes, SHA256 e75f83268de11b2a1bcfab5f3b5c5c0c97569ddbbc0990aad88437e45b8ba292.
- v14/experiments/model_compare.py adds a read-only sequential comparison using the actual V13 LlamaRunner and installed llama-server. It checks registry revision, GGUF magic, exact size and SHA256; takes the V13 coordinator lock; runs only one native model at a time; records prefill-to-first-token, TTFT, stream/decode, prompt/decode timing, RSS/PSS and four deterministic exact-output checks (including the P0 2+2 case); stores output digests rather than raw outputs.
- Candidate is never downloaded by the script. It does not edit models.json, change permissions, touch SQLite/chat history, install weights, or promote/swap a model. It refuses a busy V13 home and stops if a native process is not reaped.
- v14/experiments/test_model_compare.py covers sequential execution, exact grading and negative controls, missing candidate, hash/revision mismatch, busy lock, symlink, wrong role, native error, output redaction, same-artifact rejection, reverse order and argument bounds.

## Research result

- Current C3 baseline: LFM2.5-350M-GGUF QAD_Q4_0, 219312832 bytes, LFM Open License 1.0.
- Candidate: LFM2.5-230M-GGUF QAD_Q4_0, 149081056 bytes; 70231776 bytes / about 32.0% smaller on disk. The official model card and LICENSE identify LFM Open License 1.0; this is not Apache-2.0. Section 5 does not grant Commercial Use to a Legal Entity whose annual revenue is USD 10 million or more; the license states a qualified non-profit exception for non-commercial/research purposes.
- Smaller file size is not evidence of lower TTFT, lower peak RSS/PSS, or better user quality. No new candidate has been downloaded or run. No model swap is recommended.
- The latency-prediction paper supports separating prefill and decode and recording runtime/device/prompt/thermal context; its Pixel/Jetson/Orange Pi results cannot be transferred as Redmi measurements. The DVFS paper's prototype is evaluated on NVIDIA Jetson AGX Orin/NX with GPU/EMC controls and is not directly portable to ordinary Termux CPU inference.

## Verification

- LOCAL_LINUX, Python 3.13.5: py_compile PASS; 13/13 isolated synthetic unit tests PASS on the local implementation copy.
- Full repository checkout and repository-native test discovery: BLOCKED because git ls-remote could not resolve github.com in the local container.
- GitHub readback: all three committed experiment files exist on the branch. CI for the PR is the required exact-commit follow-up; do not treat the local fake-runner tests as native inference.
- Native model inference: NOT RUN; this environment has neither the installed V13 model files nor the Redmi llama-server binary.
- Redmi: REDMI_UNVERIFIED; no connected authorized phone or private receipt was obtained.
- Deployment: NOT_RELEASED; no update request or model operation was sent to the phone. Existing auto-updater state is unchanged and not re-verified in this run.

## Cross-agent coordination

- Open PRs #2115, #2116 and #2122 already cover registry provenance/integrity/disk-budget slices; this PR does not duplicate their files.
- Older PR #2118 contains a single-model probe on a stale branch. This PR is based on the current V14 branch and adds the missing sequential two-model comparison using the runtime LlamaRunner.
- Draft PR #2141 currently touches V14_WORK_BOARD.json and V14_USER_NEXT_ACTION.md. This handoff deliberately does not edit those shared files to avoid a cross-agent conflict; the Boss/Integrator should carry this checkpoint into V14_USER_NEXT_ACTION after reconciling #2141.

## Next executable step

1. Review this PR and run the exact test file in CI.
2. If the pinned 230M GGUF already exists locally, run the lab in both baseline-first and candidate-first order on the actual Redmi while the V13 runtime is idle.
3. If it is absent, request separate explicit consent before any experimental download into an isolated lab slot. Keep the 350M production model unchanged. A production swap would require a second, separate explicit approval after real comparisons and rollback verification.


## PR / CI checkpoint — 2026-11-21

- PR #2142: https://github.com/RedMentos/Aii/pull/2142 — ready for review, open, mergeable at last readback; base commit c3c32c05a0374e970d274f8a777a7ab85c067d66.
- Code-bearing checkpoint commit: 64ff26aa51f3a9ec4c6a169588ef41004b7ba2a0; this also adds .github/workflows/v14-model-lab.yml for future V14 experiment changes.
- Exact PR workflow runs and commit statuses were still empty at last readback. CI is NOT_RUN, not PASS. The existing V13-specific workflows did not trigger for this V14-only path; the new workflow is committed but was not observed executing in this run.
- Local 13/13 synthetic tests remain the only execution evidence for the lab logic. No native inference, no candidate download and no Redmi proof.
