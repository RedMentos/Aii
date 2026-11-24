# Research & Perception — RAW EAR interval ordering and A4 integration checkpoint (2026-11-24, run 17)

## Verified source and branch

- Release-development base: `gpt6/v13-private-remote-bridge-20261111` at `8d93236c753f0194224c19edc7411d8d7082b1d6`.
- Current Perception PR: [#2472](https://github.com/RedMentos/Aii/pull/2472), branch `research-perception/v14-a4-audio-source-outcomes-current-20261124-run16`.
- Code-bearing checkpoint SHA: `8df6a16fd5dced71a2643eae141f9f204fc66855`. Subsequent branch commits in this run only updated handoff/workplan/board documentation.
- Commits: source `c5a68bafed30365eec7719c56f190b76f9061ea9`; regression `87dc1cc8a2a27fb74188a3c1ef66559e87830ac3`; comparator source-pin update `8df6a16fd5dced71a2643eae141f9f204fc66855`.
- Exact readback blobs: `audio_temporal_evidence.py=f5fcab22e5d5463bcc3e1ab1a5ce4a586deb4b3e`; `test_audio_temporal_evidence.py=6f16afa97a04d4f0da9ab37a95cad38a25413fce`; `v14-raw-ear-vad-comparison.yml=76389ccba3d68c121c26876a5f5eb6f99f111375`.

## Runtime defect and implementation

The previous RAW EAR temporal filter required only `end_ms` to advance. A later interval such as `[90,180]` could therefore be accepted after `[100,140]`, even though its start moved backwards, provided its end was later.

The current #2472 branch now:

- tracks `_last_start_ms` alongside `_last_end_ms` per source/generation;
- rejects a backwards start with `audio window intervals must advance monotonically`;
- still permits equal starts when a cumulative window extends its end, and permits ordinary partial overlap;
- preserves the previous ordering baseline after rejected input;
- resets both ordering baselines on source/generation change or a configured long stream gap;
- updates the RAW EAR/WebRTC comparator workflow to pin the exact new temporal source blob, not the previous one.

This is a deterministic temporal-integrity guard for A4/RAW EAR. It is not a trained VAD, semantic endpointer, Android microphone provider, or neural weight update.

## Tests and evidence

- **LOCAL_LINUX isolated reproduction: PASS, 5 assertions.** Exercised a normal overlapping sequence, rejection of a backwards start, unchanged ordering state after rejection, acceptance of an equal-start cumulative extension, and independent source time bases. This was an isolated reproduction of the changed ordering rule, not the full repository test suite.
- **Prior PR #2471 focused CI: PASS** for the temporal interval regression workflow on Python 3.13 and 3.14, including compilation and the temporal/state-retention test command. This is evidence for the earlier #2471 head, not proof for the new #2472 head.
- **New exact #2472 head CI: QUEUED/PENDING** at readback: runtime deployment run 2178 (45461037584), controller guard run 631 (45461037614), public privacy scan run 1544 (45461037620), staged/integrated regression run 4678 (45461038016), and release-event integration run 3001 (45461037991). No new exact-head CI pass is claimed.
- **Full LOCAL_LINUX Aii suite: BLOCKED / NOT_RUN** because no repository checkout is mounted in this execution environment and the prior direct GitHub DNS attempt failed.
- **TERMUX/REDMI: REDMI_UNVERIFIED.** No phone was connected or queried during this run.

## Integration and release boundary

- PR #2472 remains **OPEN / DRAFT / NOT_RELEASED**. The interval-order fix is now carried on this current-base branch so the older #2471 branch is not required as a separate integration dependency. Keep #2471 open until #2472 exact-head CI is green and independently reviewed; then close #2471 as superseded. Do not merge stale #2433.
- Core owns the staged composer and its recovery/stager/deployer source-pin chain. If current staged/integrated jobs fail on the updated temporal source or other Perception source bytes, Core must rebind exact hashes bottom-up; do not weaken or bypass fail-closed checks.
- No new code is installed. The last available consented V13OBS #115 snapshot (2026-11-24 09:28:11 UTC) predates this work and reports auto-update enabled, Runtime/Dashboard UP_TO_DATE at `8d93236`, AI STOPPED_BY_USER, model STOPPED, and zero valid B1/B2 offers. It does not prove installation of this PR. No UPDATE_REQUEST, CHAT_SEND, shell, restart, model/weight/permission change or user-data mutation was performed.

## Research intake — FD-VAD

Mathur & Manocha, *FD-VAD: Semantic Endpoint Detection for Streaming Full-Duplex Speech*, arXiv:2609.35791v1 (submitted 2026-09-16). This run reviewed the arXiv abstract, official project site, official code repository at `fd-vad/fd-vad` revision `99112fc9cf6efbf80f556378d8e553d78a932300`, its MIT LICENSE, and the Hugging Face model card. The full paper text was not independently reviewed, so this is **not** marked FULL_TEXT_REVIEWED.

- Reported design: causal 2.56 s windows at 320 ms stride; WavLM-base-plus → two-layer audio adapter/downsample → Qwen2.5-0.5B-Instruct with LoRA; last-chunk Continue/Stop supervision; confidence-gated endpoint commitment and boundary-focused hard negatives.
- Reported evidence: 0.853 TurnBench dev EOT recall at FP 0.097; 0.832 chunk F1 and 0.966 utterance accuracy on the authors' English Smart Turn test; 45.8 ms per window on one NVIDIA A100 and 1,019 ms median commit latency in the TurnBench table. These are source-reported results, not V14 reproduction or Android measurements.
- License/reuse: official code MIT; HF card labels the FD-VAD weights MIT; WavLM base MIT, Qwen2.5-0.5B Apache-2.0, Smart Turn data BSD-2-Clause. The adapter is 119 MB and the model card describes an approximately 1.5 GB offline bundle. The code lockfile includes CUDA 12.4 PyTorch/Torchaudio and the latency script hardcodes CUDA; no Android/Termux ARM64 dependency closure was established. The repository's base YAML defaults to Zipformer/24 kHz while the WavLM path is configured separately at 16 kHz, so exact config/checkpoint pairing must be audited.
- V14 implication: keep acoustic RAW EAR onset/offset and semantic end-of-turn as distinct signals. A future semantic endpoint head could feed the duplex turn controller with a conservative confidence gate; it must not replace RAW EAR, transcript provenance, non-speech/prosody, or user barge-in. The 0.5B + WavLM stack and 1.5 GB bundle are not a Redmi candidate without separate measured comparison and explicit approval. No code, weights, dataset or dependency was imported/downloaded.

## Next executable step

1. Inspect every exact-head #2472 workflow and read failed job logs; fix Perception-owned defects only, while handing Core-owned source-pin failures to Core.
2. Require Python 3.13/3.14, A4, RAW EAR, controller guard, privacy, deployment, staged/integrated and source-recall checks on one exact head before requesting independent review.
3. After #2472 is green and reviewed, close #2433 and #2471 as superseded; do not release or request a phone update from this draft.
4. Keep AudioRecord OFF until QA's signed companion verifier, lifecycle, consent-revocation and zeroization gates are integrated.

**User action: none required.**
**Run start time: UNKNOWN. Checkpoint timestamp: 2026-11-24T18:38:34.128Z.**


# Research & Perception — one-lease audio generation scope (2026-11-24, run 18)

## Current source and implementation

- Repo: RedMentos/Aii.
- Release-development base: gpt6/v13-private-remote-bridge-20261111 at 8d93236c753f0194224c19edc7411d8d7082b1d6.
- Perception branch: research-perception/v14-a4-audio-source-outcomes-current-20261124-run16; PR #2472, OPEN / DRAFT / NOT_RELEASED.
- Code commit: b08238d53a441aeb2aa650b97c0ac8cbda39b5f8; test commit: 4b036157337debaa2a6db2cb70e9cc5f142dcdef.
- Readback blobs: audio_voice_cues.py=5d47c48467025199d77ba82974bb2ecea8c65b3d; test_audio_speaker_evidence.py=1eef34083aa39785d0ef06608f9352e9c987ee39.

## Concrete integration gap

The current Core PR #2478 branch core/v14-fair-b1-b2-preanswer-budget-clean-20261124-run2 has runtime.py blob 7a803bae06e3bca606ffb7cd3103b74148c8cbf8. At line 651 it directly iterates runner.generate(messages, ...); the file contains no audio_consent_generation_scope import/call. The current Core branch therefore does not hold the Perception lease through the normal Runtime's B1/B2/C4 context construction and complete C3 iterator.

## Implemented API

audio_consent_generation_scope(...) now provides a context manager that:

1. Opens the provider's linearizable audio_consent_lease for the source, generation and opaque consent receipt.
2. Calls consume_pcm16_voice_window(..., consent_lease=lease), so RAW EAR, temporal/prosody/speaker evidence, A4 attention and bounded C3 admission use that same lease rather than reacquiring consent at each internal stage.
3. Calls a Runtime-provided messages_factory(audio_result) while the lease is still held. Core can compose source-bound B1/B2/C4 context and the fixed Context OS header here.
4. Creates the runner iterator and yields (audio_result, iterator) to the caller while still inside the lease. The iterator is closed on normal context exit, early close/cancel, or exception; then the provider lease is released.

Required Core integration shape:

    with audio_consent_generation_scope(...) as (audio_result, token_stream):
        meta["audio_percept"] = audio_result
        for token in token_stream:
            # existing normal Runtime output commit/append/latewatch logic
            ...

Do not persist raw PCM or pass the opaque lease into model prompts. The messages factory must preserve the packet/source refs and can add only the bounded admission summary; the lease is a Runtime capability object, not model-visible content.

## Tests

- LOCAL_LINUX isolated harness: **PASS** — python -m py_compile /tmp/test_audio_generation_scope.py; two concurrency assertions passed (revocation blocked through full iterator; early iterator close exits the scope and releases the lock).
- This harness stubs Store/RAW EAR internals. It is not the exact project test and does not prove Android behavior.
- Exact repository regression added: test_audio_generation_scope_holds_provider_lease_through_full_runner_iterator. It exercises the real audio_consent_generation_scope and consume_pcm16_voice_window with the test Store, synthetic PCM and a fake runner. It is not locally run because no Aii checkout is mounted.
- Exact #2472 head workflows after the new commits were **QUEUED** at readback; no pass is claimed.
- Full LOCAL_LINUX suite: **BLOCKED / NOT_RUN** (no checkout mounted; git ls-remote failed due DNS/network resolution).
- TERMUX/REDMI: **REDMI_UNVERIFIED**; no device was connected or queried.

## CI and ownership

The previous #2472 exact-head controller guard and staged/integrated jobs failed before feature assertions because the Recovery Builder still expected the previous controller-guard SHA. This is Core/QA-owned. Rebind the guard in the Recovery Builder and recompute dependent stage/deployer pins bottom-up; do not weaken or bypass integrity checks.

## Research

- R-108 addendum: full text of FD-VAD arXiv:2609.35791v1 reviewed. It uses 2.56 s causal windows at 320 ms stride, WavLM-base-plus plus Qwen2.5-0.5B and 10.3M trainable adapter/LoRA parameters. Reported 0.832 chunk F1 and 0.6% false-stop; A100 latency is not Redmi latency. The official repo is MIT, HF adapter card MIT, WavLM MIT, Qwen2.5 Apache-2.0, Smart Turn data BSD-2-Clause; ~1.5 GB bundle and CUDA-oriented dependencies make it research-only for this device.
- R-109: full text of HiThink Turn arXiv:2609.34096v1 reviewed. Its state separation (audio validity, user intent, playback state) and 240 ms chunk supervision are useful future duplex design references. It fine-tunes Qwen3-ASR-1.7B with LoRA on 7,633 h using eight H100s; upstream base model is Apache-2.0, but the paper-specific fine-tune license/release was not found. No model/code imported.

## User impact and next action

No user-visible Runtime behavior changes until Core integrates this API. No release SHA; PR #2472 is not released. The existing updater was not invoked and no device mutation occurred. Next step is Core wiring plus exact-head staged/integrated tests. **User action: none required.**
**Run start:** 2026-11-24 21:37:30 Europe/Berlin. **Completed/readback:** 2026-11-24 21:48:05 Europe/Berlin.
