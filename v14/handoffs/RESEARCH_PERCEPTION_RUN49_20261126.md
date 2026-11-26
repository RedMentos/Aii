# Research & Perception handoff — Run 49
Date: 2026-11-26
Run start: UNKNOWN
Checkpoint: 20:55 Europe/Berlin (system-provided run context)
Owner: Research & Perception
Repo: RedMentos/Aii

## Checkpoint

- PR: https://github.com/RedMentos/Aii/pull/2524
- Branch: research-perception/v14-kv-snapshot-consumer-20261126-run35
- Exact code/test SHA: 1417250fb28c4e30c5c4e0d8150e673248ad10a8
- Latest docs/handoff branch head at this readback: 82d79103af7aa80d1ec29b688ec2f3ecca78acc8
- PR state: OPEN / DRAFT / NOT_RELEASED
- Base: PR #2519, base SHA 5f2ef5393f25085d2e2968118982d72b823b99b4

## Implemented function

The optional LFM2 same-model full-hybrid sequence-state roundtrip previously primed the source context with BOS. That was not the input the native receiver was meant to test. The roundtrip now pre-fills from the actual LATENT_CANDIDATE MatrixInput and binds the receipt to:

- prefill_condition = LATENT_CANDIDATE
- prefill_rows
- float32 little-endian prefill_input_sha256
- prefill_decode_status = 0

The source state is captured after candidate prefill. The destination is a fresh context for the same model. Full sequence state still covers attention/KV plus recurrent shortconv. The same fixed continuation is applied after the candidate rows, and next-token logits are compared. The truncated-state restore remains a negative control; the buffer remains capped at 16 MiB and zeroized. The raw state blob is never emitted or persisted.

The contract was bumped to v14.native-hybrid-state-roundtrip/2. Python checks the raw native candidate digest and row count against the already-prepared LATENT_CANDIDATE matrix, then validates the sanitized receipt. The task-score utility and native_receiver_task_matrix_bridge now attach/read the receipt on LATENT_CANDIDATE rather than NO_MESSAGE.

## Files changed

- v13/code/v13/native/latent_receiver/native_latent_receiver.cpp
- v13/code/v13/native_latent_receiver.py
- v13/code/v13/native_hybrid_state.py
- v13/code/v13/native_receiver_utility.py
- v13/code/v13/native_receiver_task_matrix_bridge.py
- v13/code/tests/test_native_latent_receiver.py
- v13/code/tests/test_native_receiver_task_score.py
- .github/workflows/v14-native-latent-receiver.yml
- v14/V14_RESEARCH_LEDGER.md (R-169)
- v14/V14_LIVE_WORKPLAN.md
- v14/V14_CANON_COVERAGE_INDEX.md
- v14/V14_USER_NEXT_ACTION.md
- v14/V14_WORK_BOARD.json

## Exact test evidence

LOCAL_LINUX:
- CPython 3.13.5 isolated prefill-contract reproduction: 6/6 PASS. Cases: valid candidate, wrong condition, wrong row count, failed decode status, wrong input digest, empty row count.
- Standalone C++ float32 little-endian digest helper: g++ -std=c++17 -O2 -Wall -Wextra -Werror compile/run PASS; hash matched Python struct.pack('<2f') output.
- Full local Aii checkout, exact repository pytest, pinned llama.cpp native build: NOT_RUN. /mnt/data has no checkout; git ls-remote fails because github.com DNS cannot resolve. Do not describe the scratch checks as the repository suite.

CI:
- Native receiver workflow 45888866164: QUEUED at checkpoint.
- Staged/integrated workflow 45888866275: QUEUED at checkpoint.
- RuntimeDeploy offline integrity workflow 45888866345: QUEUED at checkpoint.
- Queued is not PASS. Recheck exact run conclusions before integration.

## User effect and canonical status

This improves the diagnostic's source condition: the state roundtrip now uses the actual candidate input instead of BOS, and the receipt cannot be rebound to NO_MESSAGE or a different candidate matrix without failing the hash/row checks.

It does NOT create normal-turn chat, different-weight model transfer, trained latent projector/receiver weights, semantic use, generated-answer correctness, persistent state, learning, production B3 authority or Android control. B3 remains OFF. P0 issue #1904 remains OPEN.

Classification: CODE_PRESENT / WIRED_SYNTHETIC_DIAGNOSTIC / LOCAL_SCRATCH_PASS / CI_QUEUED / REAL_GGUF_UNVERIFIED / REDMI_UNVERIFIED / NOT_RELEASED.

## Research

R-169 records full-text review of Kvedaras & Rasymas, arXiv:2611.12062v1 (2026-11-09, preprint, paper CC BY 4.0). It supports object-specific cache handling: token-wise K/V/MLA maps differ from prompt-level recurrent-state copy/correction or target-recurrence replay. Experiments use 16–48B GPU models and do not validate LFM2 or Android; authors report translator code/weights are internal, not public OSS. Same-model state restoration is only a baseline, not cross-model latent coupling.

## Cross-agent coordination

Core PR #2525 is still OPEN/DRAFT and mergeable=false. Its base points at stale #2524 SHA ee27e03c89f69cf049e60b622c5be068a4b0cf2d, while the current #2524 docs/handoff branch head is 82d79103af7aa80d1ec29b688ec2f3ecca78acc8 (code/test SHA 1417250fb28c4e30c5c4e0d8150e673248ad10a8). Core must rebase after the parent CI result, refresh exact observer/recovery/source pins and rerun staged/integrated tests. No Core-owned files were changed.

## Device, updater and release

No connected Redmi and no authenticated private relay receipt were available in this run. No UPDATE_REQUEST, CHAT_SEND, LOG_PAGE, shell, restart, model download/swap, permission change or deployment was performed. REDMI_UNVERIFIED.

The latest available private V13OBS #115 data is historical (2026-11-24): auto-update was then reported enabled at 8d93236, while AI was STOPPED_BY_USER and model process STOPPED. This does not prove current updater status or current runtime. GitHub push is not deployment. RELEASE_SHA: NOT_RELEASED.

## Next action

1. Recheck the exact three queued workflow runs on #2524 head 1417250fb28c4e30c5c4e0d8150e673248ad10a8.
2. If the Perception native and focused tests pass, Core rebases #2525 onto this exact parent head and reruns staged/integrated source-pin checks.
3. Only after CI/integration is green and after separate explicit local approval, run on an already-present LFM2 GGUF; do not download or swap models. Measure state bytes, capture/restore latency, peak RSS, max/RMS logit difference and truncated-restore rejection.
4. Then test a different-weight sender/receiver mapping with zero/shuffle/wrong-donor controls, held-out task probes, generated-answer correctness, retention and restart/rollback.
5. Continue RAW EAR/A0-A5 work independently; microphone and Redmi capture remain unverified.

No user action is needed for the current CI step. Explicit approval will be required before any local GGUF run.
