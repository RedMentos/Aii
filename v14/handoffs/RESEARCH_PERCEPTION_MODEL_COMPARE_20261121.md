# Research & Perception handoff — 2026-11-21

## Ownership and scope

- Queue item: V14-005, Research & Perception, model-candidate evaluation.
- Base: gpt6/v13-private-remote-bridge-20261111 at verified commit c0cedbde718ede6107f4df1f1bf9c784df4e00cf.
- Working branch: research-perception/model-compare-c3-v14base-20261121.
- This is a C3-only first slice. It does not close the broader B1/B2 sparse-MoE or whole-Canon requirements.

## Implemented

- v14/experiments/model_candidates.json pins the existing registry's previous C3 candidate LFM2.5-230M-GGUF: revision cdf97bd8205908758f44aec508d68ac1aef98f5c, QAD_Q4_0, 149081056 bytes, SHA256 e75f83268de11b2a1bcfab5f3b5c5c0c97569ddbbc0990aad88437e45b8ba292.
- v14/experiments/model_compare.py adds a read-only sequential comparison using the actual V13 LlamaRunner and installed llama-server. It checks registry revision, GGUF magic, exact size and SHA256; takes the V13 coordinator lock; runs only one native model at a time; records prefill-to-first-token, TTFT, stream/decode, prompt/decode timing, RSS/PSS and four deterministic exact-output checks (including the P0 2+2 case); stores output digests rather than raw outputs.
- Candidate is never downloaded by the script. It does not edit models.json, change permissions, touch SQLite/chat history, install weights, or promote/swap a model. It refuses a busy V13 home and stops if a native process is not reaped.
- v14/experiments/test_model_compare.py covers sequential execution, exact grading and negative controls, missing candidate, hash/revision mismatch, busy lock, symlink, wrong role, native error, output redaction, same-artifact rejection, reverse order and argument bounds.

## Research result

- Current C3 baseline: LFM2.5-350M-GGUF QAD_Q4_0, 219312832 bytes, LFM Open License 1.0.
- Candidate: LFM2.5-230M-GGUF QAD_Q4_0, 149081056 bytes; 70231776 bytes / about 32.0% smaller on disk. The official model card and LICENSE identify LFM Open License 1.0; this is not Apache-2.0. Section 5 conditions Commercial Use on not exceeding its defined threshold (annual revenue USD 10 million or more) and does not license Commercial Use by a Legal Entity that exceeds that threshold; it states a qualified non-profit exception for non-commercial/research purposes.
- Smaller file size is not evidence of lower TTFT, lower peak RSS/PSS, or better user quality. No new candidate download or baseline-vs-candidate run occurred in this pass. Important historical evidence: V13 issue #1904 records a Redmi run with C3 230M returning 2 instead of 4 for 2+2; 230M alone is not a trusted reasoning replacement. No model swap is recommended.
- The latency-prediction paper supports separating prefill and decode and recording runtime/device/prompt/thermal context; its Pixel/Jetson/Orange Pi results cannot be transferred as Redmi measurements. Its full text records generated-token count and per-run telemetry, then uses request-level random splits; whether held-out requests' own telemetry enters the dynamic predictor is unclear, so pre-execution screening claims may be optimistic. The within-device test sets are only 11 and 41 requests. We adopt the measurement schema, not the predictor or its headline screening accuracy. The DVFS paper's prototype is evaluated on NVIDIA Jetson AGX Orin/NX with GPU/EMC controls and is not directly portable to ordinary Termux CPU inference.

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
- Draft PR #2141 also touches V14_WORK_BOARD.json and V14_USER_NEXT_ACTION.md for QA-owned tickets. This branch updates only the separate V14-005 ticket and inserts the Research & Perception snapshot near the top of V14_USER_NEXT_ACTION; #2141's QA append is at the end. The edits are disjoint by section, but the merge order should still be checked. A coordination comment was posted on #2141.

## Next executable step

1. Review this PR and run the exact test file in CI.
2. If the pinned 230M GGUF already exists locally, run the lab in both baseline-first and candidate-first order on the actual Redmi while the V13 runtime is idle.
3. If it is absent, request separate explicit consent before any experimental download into an isolated lab slot. Keep the 350M production model unchanged. A production swap would require a second, separate explicit approval after real comparisons and rollback verification.


## PR / CI checkpoint — 2026-11-21

- PR #2142: https://github.com/RedMentos/Aii/pull/2142 — ready for review, open, mergeable at last readback; base commit c0cedbde718ede6107f4df1f1bf9c784df4e00cf.
- Code-bearing checkpoint commit: 64ff26aa51f3a9ec4c6a169588ef41004b7ba2a0; this also adds .github/workflows/v14-model-lab.yml for future V14 experiment changes.
- Exact branch CI now PASS: workflow run 44849343250, job model-lab, on exact PR head 6aadf841434bcc43fbde1827a4ed2ef9d61bc4b0. It compiled both Python files, validated the candidate JSON, and ran 13 tests in 0.020s (Python 3.13.18, GitHub Linux runner). This is exact-commit CI, not native inference.
- No actual GGUF or llama-server is present in the CI runner, so native model inference remains NOT RUN; no candidate download and no Redmi proof.


## Shared handoff updated — 2026-11-21

- V14_WORK_BOARD.json: V14-005 moved from READY to IN_PROGRESS_PARTIAL with PR #2142, exact CI run 44849343250, and explicit NOT_RUN/REDMI_UNVERIFIED native evidence.
- V14_USER_NEXT_ACTION.md: added a Research & Perception checkpoint and corrected source_HEAD (shared base c3c32c05; latest code-bearing merge 3db6d1f has exact merge-push CI green but no Redmi install receipt), local-test boundary, candidate-only status and next action.
- The PR's current head is authoritative and should be read live; code/manifest commit 6aadf841434bcc43fbde1827a4ed2ef9d61bc4b0 passed exact CI run 44849343250. Subsequent candidate-manifest edits only clarified license wording and fixed a status label; LOCAL_LINUX JSON_PARSE_PASS, no CI rerun for those metadata-only edits. Subsequent other commits update board/next-action/handoff/ledger.


## QA finding fixed — executable identity, 21 November 2026

QA identified that V13 `LlamaRunner` uses `V13_LLAMA_SERVER` when set, while the first lab version reported the hash of `home/bin/llama-server` regardless of that override. The measurement could therefore describe a different executable from the one actually launched.

The current PR branch adds `verified_runner_binary()`:
- Before generation, resolve `runner.binary` and require it to match the previously verified installed executable.
- After generation/load, resolve `runner._loaded_binary` (the actual selected `cmd[0]`) and require the same identity.
- Require baseline and candidate runs to report the same executable SHA256.
- Report the actual resolved executable's name, size and digest; no absolute path is emitted.

Three regressions cover a different environment override (refused before generation), an override resolving to the installed executable (accepted), and a changed loaded executable (aborts, then runner cleanup runs). The exact test file now contains 16 tests.

### Verification at this checkpoint

- LOCAL_LINUX isolated helper: `py_compile` PASS; 5/5 executable-identity checks PASS. This is a focused helper-level test, not a full checkout or native inference.
- Exact PR head `fef505ac3f6ea30f034fdce5ee5a9abc6b5c30b7`: model-lab CI run 44853309109 IN_PROGRESS at last readback.
- Full repository checkout remains blocked by local DNS resolution for github.com.
- Native GGUF inference NOT_RUN; no candidate download or model swap; no phone action. REDMI_UNVERIFIED / NOT_RELEASED.

Next: read back exact-head CI, then obtain independent Core/QA review. Keep 230M diagnostic-only unless a new authorized Redmi A/B comparison proves quality and performance; no production swap without a separate approval and rollback evidence.


### Corrected exact CI readback — 21 November 2026

The first post-fix workflow run 44853309109 failed only because the new loaded-executable regression expected a different error string than the fail-closed helper emitted. The implementation correctly rejected the changed executable. The test assertion was aligned; no safety check was relaxed.

- Exact code/test SHA: `f5c5265a89258a6fd1ab5d25c20c733d21bb2ab4`.
- Exact GitHub Actions run: [44853451281](https://github.com/RedMentos/Aii/actions/runs/44853451281), Linux/Python 3.13.18, compile PASS, manifest JSON PASS, 16/16 tests PASS.
- LOCAL_LINUX helper-level identity suite: `py_compile` PASS, 5/5 tests PASS. Full repository checkout/test is still blocked by DNS.
- Native GGUF inference NOT_RUN; no candidate download/swap; no Redmi receipt; NOT_RELEASED.
- Current PR head includes subsequent documentation-only checkpoints; code/test bytes remain the tested SHA above.


## A5 timed audio review — finality boundary

Core PR #2144 currently validates an exact process-local PCM16 window, but the window schema does not carry finality and the Runtime overlay calls `consume_pcm16_window` without an explicit finality argument. The bridge's default is `FINAL`, so the Runtime cannot preserve a provisional capture as provisional. I posted this finding on #2144 and requested an explicit `PROVISIONAL|FINAL` field with a negative test proving provisional windows are excluded from B1/B2/C3 prompt admission while remaining non-authoritative A4 observations.

The staged path does recheck consent at admission, context creation and each consumer read. However, the current extractor measures only RMS/peak/ZCR; pitch, voicing, speech/non-speech and prosody are unmeasured. This is a partial synthetic PCM path, not Android microphone/full voice completion. Next Perception work should build a low-cost time-windowed feature extractor and measure ARM CPU/RSS before integration. No Core-owned files were edited.


## Core A5 staged-consumer CI follow-up

Core PR #2144 remains draft. Exact-head run 44853452893 fails one provenance assertion because it expects the old literal without `meta.get('source_recall_refs',[])`; the staged builder adds the audio ref after the source-recall refs. Earlier run 44853319109 fails because `staged_tests.mkdir()` collides with the `tests/` directory created by the stager. Both are test fixture/assertion failures, not audio runtime proof. I posted the exact provenance expression and the separate finality-field gap to Core. Keep #2144 unmerged until its tests pass and explicit PROVISIONAL/FINAL handling is present.


Additional Core CI failures on the same #2144 head:
- 44853452891: strict additive validator rejects staged builder/script paths outside the allowed inert-module/test/handoff scope. Do not weaken the validator generically; require a narrow explicit allowlist or restructure.
- 44853452940: 239 passed, 10 skipped, 47 subtests passed, 1 failed because the recovery-stage test still expects the 2026-11-12 builder filename while the current hash-bound manifest points to the 2026-11-21 builder.
Combined with the earlier `mkdir` and provenance assertion failures, four exact CI blockers remain. I posted all four findings to Core. PR #2144 stays draft/unmerged, and the explicit finality field is still missing.


## QA integrity blockers repaired — 2026-11-21

The second review found a pre-lock model-file race and a mutable license URL. The comparison now acquires the V13 coordinator lock before reading installed settings, model registry revision, paths, sizes or hashes. Under that lock it copies the baseline and candidate into a private temporary directory on the V13 data volume (not a possibly RAM-backed /tmp), using no-follow file opens. It verifies source inode/size/mtime/ctime before and after copy, checks copied bytes against pinned size/SHA, fsyncs them, marks copies read-only, and rechecks them immediately before and after each runner. The installed llama-server digest is pinned at locked preflight and compared to configured and loaded runner identity.

The candidate license URL is pinned to the exact weight revision. An immutable LFM Open License v1.0 text snapshot is included at v14/experiments/licenses/LFM-OPEN-LICENSE-v1.0.txt with SHA256 61d7e939a05911c765b7e98ffaa1ab5ca6c0174a65350766c25cb10197d19fc8. Its source is a commit-pinned public mirror and its text was cross-checked against Liquid AI's official license page; byte-for-byte identity with the model repository's own LICENSE file is not asserted. The legal terms remain conditional, not Apache-2.0.

New negative/integrity tests cover a candidate replacement immediately before lock acquisition, mutation of installed model files after staging, read-only staged bytes, runner binary replacement after preflight, and the repository manifest's pinned license snapshot. The exact model-lab workflow must be rerun on the new commit. Full local checkout remains blocked by GitHub DNS; native GGUF inference and Redmi remain NOT_RUN / REDMI_UNVERIFIED.

The shared V14 board, ledger and next-action files are left to Boss/Integrator PR #2149 to avoid competing edits; that PR already carries the whole-system status and the prior model-lab checkpoint.


## Latest Research & Perception checkpoint — 2026-11-21

### Verified code checkpoint

- The QA license-snapshot patch from draft PR #2154 is now integrated into this branch's model lab. Code/test commit: `40deb8a56686455b361ba41e63cb57b981b5a71b`; current PR #2142 branch head should be read live.
- `verify_license_snapshot()` now reads the pinned snapshot, rejects absolute/traversal paths, symlink components, missing files and SHA256 mismatches, and runs before either native inference or the `CANDIDATE_NOT_INSTALLED` return. Reports mark the snapshot verified and emit only the digest actually read.
- The earlier integrity fixes remain present: coordinator lock before installed-state reads; baseline/candidate copies staged on the V13 data volume, no-follow and hash-verified, fsynced and read-only; revalidation around runs; runner executable identity checked before and after load.
- Exact GitHub Actions workflow [44861145442](https://github.com/RedMentos/Aii/actions/runs/44861145442), job `model-lab`, exact code/test SHA above: **PASS** on GitHub Linux / Python 3.13.18 — `py_compile`, candidate-manifest JSON validation, **23/23 synthetic tests**. Tests include missing/tampered/traversal snapshot, pre-lock candidate replacement, staged-file replacement, runner identity and sequential one-at-a-time execution.
- LOCAL_LINUX full-checkout suite remains **BLOCKED** because this worker cannot resolve github.com; no local full-suite PASS is claimed. GitHub Actions is CI/Linux, not a local or Redmi measurement.

### Research completed in this run

- R-007, arXiv:2608.16347v2, was upgraded from ABSTRACT_VERIFIED to FULLTEXT_REVIEWED in the V14 ledger. Only one of three causal decoder-only pairs showed modest held-out activation-injection effect (23.3% vs 0% unrelated-state control); the two Mistral-target pairs were null. The positive pair's generated text was often not the correct answer. This argues for pair-specific causal receiver tests against text and no-message baselines, not a universal latent bridge.
- R-010 records Qwen3-0.6B-GGUF as a possible comparison lead only: Apache-2.0, Q4_0 429 MB, Q8_0 805 MB, BF16 1.51 GB; official Qwen3 guide says llama.cpp support from b5092. No exact model revision/SHA was pinned and no download or trial is authorized or performed. Its Q4_0 file is about 1.96× the current 219,312,832-byte LFM2.5-350M baseline; memory and quality are unknown.

### Boundaries and next action

- No GGUF candidate was present/verified for this run, so actual native model comparison remains **NOT_RUN**. The LFM2.5-230M candidate remains diagnostic-only and has historical Redmi 2+2 failure in #1904.
- No fresh private Redmi receipt; **REDMI_UNVERIFIED / NOT_RELEASED**. No device action, updater request, model download/swap, permission change or weight edit occurred.
- Exact staged-context workflow is still absent; the green model-lab CI does not make #2142 release-ready. Ask QA/Core for independent review and the staged-context gate before any integration.
- Research/Perception owns the R-007 full-text note; shared board and `V14_USER_NEXT_ACTION.md` remain on Boss's open #2149 branch to avoid concurrent edits. Boss was asked to sync the new SHA, 23/23 CI and paper result there.


## A5 RAW EAR follow-up — 2026-11-21

- Additive-only PR #2155 now contains the separate `v13.audio_voice_cues` module and eight synthetic regressions. Current exact code/test head: `40e1f877157df57643267470bab3aff39c1eaaee`.
- Exact safe-additive CI [44862523075](https://github.com/RedMentos/Aii/actions/runs/44862523075): **PASS**, Python 3.11.18, compile PASS, 8/8 tests PASS in 2.20 s. This includes voiced pitch, deterministic noise/silence/impulse, sample-rate stability, Store/A4/C3 admission, provisional-only A4, malformed-cue rejection, consent revocation and one-second bound.
- New module blob `7ac80a0d0deec8f52361fe89756ebd743b0a3537`; test blob `e1fa096f12c8ad9b8ca7c68098bad8cda96e4e23b`. Existing Core-pinned A5 bridge/contract/ear files are unchanged. Core can opt in by adding this one new module to its staged candidate and calling `consume_pcm16_voice_window`; no old source hash needs refreshing.
- The exact staged-context/integrated regression [44862523082](https://github.com/RedMentos/Aii/actions/runs/44862523082) is still IN_PROGRESS at this readback; it is not a pass. Core's #2144/#2153 stage overlay has not yet consumed the new module.
- LOCAL_LINUX full checkout remains DNS-blocked. The local Python helper check is only a copied algorithm smoke test, not repository integration. No Android microphone/OS permission, native model, speaker identity, ASR, full-duplex, Redmi receipt or deployment. REDMI_UNVERIFIED / NOT_RELEASED.
- Next: read exact staged-context workflow result; coordinate Core opt-in and only then run staged Runtime regression. Do not mark full RAW EAR/voice complete from this partial acoustic cue adapter.


## Rebase/readback checkpoint — 2026-11-21

- This branch is rebuilt directly on current V14 base `c0cedbde718ede6107f4df1f1bf9c784df4e00cf`; the previous #2142 branch was stale and reported mergeable=false. Model-lab code, tests, workflow and license snapshot are copied byte-for-byte from the reviewed old branch; the shared research ledger is deliberately not copied, so newer base research is not overwritten.
- Prior exact code/test commit `40deb8a56686455b361ba41e63cb57b981b5a71b` passed GitHub Linux/Python 3.13.18 run `44861145442` with compile + 23/23 synthetic tests. That run is historical evidence from the previous ancestor; the rebased branch requires its own exact-head CI.
- **Current new-base exact CI: PENDING.** Full local repository tests remain blocked by GitHub DNS. No native GGUF inference was run; the candidate is not known to be present on the phone. Redmi remains REDMI_UNVERIFIED and deployment NOT_RELEASED.
- No candidate download, model swap, model-manifest edit, permission change, user-data read or production action was performed. Keep this C3 comparison lab diagnostic-only.
