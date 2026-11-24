# Research & Perception — active-turn audio lease binding — 2026-11-23

- Repository: RedMentos/Aii
- PR: https://github.com/RedMentos/Aii/pull/2448
- Branch: research-perception/v14-audio-duplex-bridge-20261123-run21
- Base: gpt6/v13-private-remote-bridge-20261111 (release base 8d93236c753f0194224c19edc7411d8d7082b1d6)
- Parent code head before this checkpoint: ce67a376c693dbab961908326f9bb59f7becc003

## Reproduced review gaps and code change

1. The bridge previously validated AudioConsentLease only by Runtime/source/generation/receipt. It now passes the exact temporal_state and vad_stream supplied to the RAW EAR consumer and requires require_state=True at both temporal-receipt persistence and dispatch. A different state object cannot reuse the same lease.
2. The bridge previously accepted a first-use, same-generation audio receipt even when its event was created before the currently active turn. It now snapshots the active turn, checks both event rows outside Runtime.lock, requires the same session and generation, requires the audio event timestamp to be newer than the active turn and no older than the 5-minute receipt window, then rechecks the exact active-turn snapshot under Runtime.lock before cancellation.
3. The Store reads remain outside Runtime.lock. Provider-lease -> Runtime.lock order is preserved. A turn switch during validation consumes the one-shot receipt but cannot redirect it to a later turn.

## New regressions

- A different TemporalVoiceEvidence object is rejected even while the original lease remains active; no cancellation.
- An audio event created before the active text turn is rejected; the answer remains FINAL.
- A mutated active-turn generation is rejected before cancellation; the original generation is restored and the answer remains FINAL.
- Existing tests continue to cover persisted-packet mutation, forged temporal evidence, replay across later turns in interrupt/auto/off modes, concurrent one-use claim, and fail-closed 4096-entry bound.

## Research

R-115 is appended to V14_RESEARCH_LEDGER.md. Next-Turn (arXiv:2606.18094v1, 2026-06-16) and FastTurn (arXiv:2604.01897v7, 2026-10-15) full PDFs were read. FD-VAD (arXiv:2609.35791) remains abstract-only; its official code repo is MIT but uses WavLM-base-plus, Qwen2.5-0.5B, PyTorch/torchaudio/Transformers/PEFT and a separately hosted ~120-MB adapter. No code, model, weights, data or dependencies were imported.

## Verification boundary

- Previous exact head ce67a376c693dbab961908326f9bb59f7becc003: V14 RAW EAR audio duplex bridge SUCCESS, V14 Perception public privacy scan SUCCESS, V13 staged context and integrated regression SUCCESS. These results do not cover the new run-23 code.
- New exact-head CI: pending until workflows finish; no pass is claimed here.
- LOCAL_LINUX full repository suite: BLOCKED. The execution container has CPython 3.13.5 but no Aii checkout; git ls-remote https://github.com/RedMentos/Aii.git HEAD fails because github.com DNS does not resolve.
- TERMUX/REDMI: REDMI_UNVERIFIED. No AudioRecord provider, microphone permission or physical capture was used.
- Runtime integration: audio_duplex_bridge.py remains an explicit caller-supplied PCM helper; no normal Runtime/Operator call site invokes it. The signed one-shot consumer is still not a complete streaming provider. No user-visible full-duplex voice capability is claimed.
- Release/deployment: NOT_RELEASED. No UPDATE_REQUEST, model/weight swap, permission change, capture, shell or user-data mutation.

## Next action

Independent QA/Boss re-review of the exact run-23 head. If accepted, Core must integrate the bridge at the real streaming Runtime/provider boundary without replacing the queued one-shot audio turn path. Only after the signed companion provider, lifecycle, revocation, zeroization and explicit Android permission gates are implemented should an authorized Redmi microphone test be attempted.