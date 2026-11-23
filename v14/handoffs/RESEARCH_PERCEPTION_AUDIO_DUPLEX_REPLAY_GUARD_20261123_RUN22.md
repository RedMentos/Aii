# Research & Perception — RAW EAR duplex receipt/replay hardening — 2026-11-23

- PR: https://github.com/RedMentos/Aii/pull/2448
- Base: gpt6/v13-private-remote-bridge-20261111 @ fb120481af73da2b5d9547159a8a298adb6d6646
- Branch: research-perception/v14-audio-duplex-bridge-20261123-run21
- This checkpoint adds a persisted temporal A4 receipt inside the existing audio PerceptPacket, bound to event, packet, generation, source hash, consent receipt, interval and the producing Runtime process epoch. The bridge validates the persisted receipt instead of trusting caller-supplied a4.temporal_voice.
- Every dispatch claims a one-use hash of event/packet/temporal-receipt identity in a bounded 4096-entry SQLite Store state row using compare-and-swap. Claims apply to INTERRUPT, CONTINUE and OFF. The claim happens before Runtime.lock and before cancellation; stale or cross-process receipts fail closed.
- Added adversarial coverage: forged-only temporal onset, replay against a later active turn in both interrupt and auto/CONTINUE modes, and OFF-mode consumption. The workflow now runs when the existing RAW EAR producer changes.
- Research R-114: FD-VAD (arXiv:2609.35791), FastTurn (arXiv:2604.01897v7), Next-Turn (arXiv:2606.18094). Abstract/metadata-level only; no full-text claim, code import, weights, datasets or dependency.
- LOCAL_LINUX full repository suite remains BLOCKED: no checkout mounted and git ls-remote fails DNS. No local Runtime integration result is claimed. Exact CI must run on this code head.
- Redmi: REDMI_UNVERIFIED for this candidate. Last authenticated receipt says installed base fb563d771fe2d493c4ec25abe94280981d24ef5c, runtime STOPPED_BY_USER. No restart, CHAT_SEND, UPDATE_REQUEST, microphone capture or permission/model/weight/data change.
- NOT_RELEASED. Boss/QA review and staged/integrated source-pin checks required. Next: exact-head CI, then review Store CAS/Runtime.lock ordering and merge composition with Core/QA; only later test through an explicitly authorized AudioRecord provider.


## Exact code checkpoint and local isolated verification

- Latest code-bearing commit: fea6002c4fa7def9f1dd83f51a8320fc526e4f17. The next handoff commit changes only this note.
- Exact bridge module readback blob: 6035c5f2988ca05ec6641892cb133be7cd274a00.
- Exact tests readback blob: 05515d0f9303cc773ed9ed6b090f487cd7eac3f6. The V3 revision assertion is aligned with BRIDGE_REVISION.
- LOCAL_LINUX isolated harness: py_compile of the exact bridge module PASS; 3/3 tests PASS using the exact bridge code with minimal Store/lease/duplex stubs: forged temporal evidence rejected before cancel; replay rejected in interrupt, auto/CONTINUE and off modes across a later active turn; packet compare-and-swap refuses to overwrite a changed persisted packet. This is not the full repository Runtime integration suite.
- Exact-head GitHub Actions for code head fea6002 are pending/queued at last poll; no CI PASS is claimed. The full local Aii checkout remains unavailable due the missing mount and github.com DNS failure.
- QA's two inline review threads remain open for reviewer recheck; no self-resolution or merge was performed.


## Base synchronization

- The target branch advanced while this PR was open. I merged current release base 8d93236c753f0194224c19edc7411d8d7082b1d6 into this branch with a two-parent merge commit 342fb4f5954c69a29fed9b164c96c76f0146c735. No force-push; the branch was updated with expected-head protection.
- The base delta was inspected first: only the M1 data workflow/fixtures and QA Android handoff changed, with no overlap against the six files in this PR. The merge tree retained all six PR files and R-114.
- The code-bearing implementation SHA remains fea6002c4fa7def9f1dd83f51a8320fc526e4f17. The merge commit only synchronizes the release ancestor; this handoff update is documentation-only.
