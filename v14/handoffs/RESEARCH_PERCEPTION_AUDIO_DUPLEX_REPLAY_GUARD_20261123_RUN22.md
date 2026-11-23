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
