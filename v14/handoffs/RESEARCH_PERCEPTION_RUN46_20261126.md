# Research & Perception — Run 46 Handoff
Date: 2026-11-26
Repository: RedMentos/Aii
PR: https://github.com/RedMentos/Aii/pull/2524
Branch: research-perception/v14-kv-snapshot-consumer-20261126-run35

## Checkpoint
- Code/test head: 076a973eaad808b537c7f74337464d02cf41d633
- Latest docs/board head before this handoff file: 9e34d6763760a1765166742d1201b3d34e798b3e
- Release SHA: NOT_RELEASED
- Deployment: NOT_DEPLOYED
- Redmi: REDMI_UNVERIFIED; no fresh authenticated receipt and no device action.

## New executable path
Added an opt-in LFM2-only native C++ full-hybrid sequence-state roundtrip behind --hybrid-state-roundtrip:
1. Create two fresh small contexts with identical model and context settings.
2. Prefill BOS in the source context.
3. Capture sequence 0 using llama_state_seq_get_size/get_data.
4. Try a truncated restore as a negative control; clear destination state.
5. Restore the full sequence into the fresh context using llama_state_seq_set_data.
6. Feed the same 1–64 teacher-forced continuation tokens into both contexts.
7. Compare full next-token logits after each continuation token; emit hashes, byte counts, timings and fidelity metrics only.
8. Cap the ephemeral state buffer at 16 MiB and zeroize it. No raw state export, raw state persistence, installed-runtime write, training, weight edit or production authority.

Python binds the receipt to receiver model SHA/revision, receiver tokenizer revision, pinned llama.cpp revision, native binary SHA, task context SHA, NO_MESSAGE input SHA and target-token-ID SHA. It validates the truncated-state negative control and attaches the receipt to the NO_MESSAGE condition. The Perception Runtime bridge can opt in explicitly; default remains OFF.

This is same-model/same-weight state restoration only. It does not prove sender-to-receiver latent transfer, trained B3 coupling, or generated-answer quality.

## Exact upstream source audit
Pinned llama.cpp revision: b29c606e28a01b1bc8c1351026a0fa6e616bf6c4.
- include/llama.h: public sequence-state API signatures.
- src/llama-context.cpp: sequence-state wrappers and byte-count return path.
- src/llama-memory-hybrid.cpp: state_write/state_read include mem_attn and mem_recr except partial-only mode.
- src/models/lfm2.cpp: LFM2 recurrent short-convolution state path.
- LICENSE: MIT.
No upstream source was copied wholesale. No new paper is claimed as read in this run; this was a primary-source implementation audit.

## Tests and evidence
Workflow: 45813438280, exact code/test head 076a973...
- Python 3.13 focused tests: PASS.
- Python 3.14 focused tests: PASS.
- Staged receiver/deploy-chain compile: PASS on both Python versions.
- Public diff privacy scan: CLEAN.
- Android arm64-v8a cross-compile step: PASS (compile only; artifact upload was still pending at last poll).
- Linux pinned llama.cpp build: IN_PROGRESS at last poll.
- Shared source-tap identity gate: FAIL/BLOCKED because Core's native_receiver_matrix_runtime.py producer hook is not present on this Perception branch. This is the cross-lane integration blocker; it is not a focused Python test failure.
- Full LOCAL_LINUX checkout/pytest: NOT_RUN; no Aii checkout is mounted and GitHub DNS is unavailable in this runtime.
- Actual GGUF model execution: NOT_RUN.
- Redmi/Termux: REDMI_UNVERIFIED.

## Cross-agent coordination
Core PR #2525 is stale against the latest #2524 head. Core must rebase #2525 onto the current #2524 branch, expose include_hybrid_state_roundtrip as a separate explicit local-lab option (default OFF), and rerun the source-tap/integrated Runtime gate. Do not enable this on normal turns by default because it temporarily creates an additional context and has no Redmi RSS measurement yet.

The RAW EAR chronology PR #2527 and next-delta PR #2498 remain separate Perception consumers; preserve their ownership and rebase order. Do not fold their code into this native-state patch.

## Next executable steps
1. Finish Linux pinned build and Android artifact upload; keep the source-tap gate marked blocked until Core rebase.
2. Core rebase #2525 and expose the explicit lab flag.
3. Run against an already-present, explicitly approved LFM2 GGUF with 32–64 continuation tokens. Measure exact state bytes, capture/restore duration, peak RSS, max/RMS logit delta, top-1 agreement and truncated-restore rejection.
4. Extend the state test from BOS to a real LATENT_CANDIDATE prefill.
5. Only then test different-weight sender/receiver transfer with zero, shuffled, wrong-donor and no-message controls. B3 remains OFF until the full Canon gates pass.

No model download, model swap, weight mutation, permission change, updater request, user-data mutation or device action occurred. No user action required.