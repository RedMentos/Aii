# Research & Perception — RAW EAR duplex receipt/replay hardening — 2026-11-23

- PR: https://github.com/RedMentos/Aii/pull/2448
- Base: gpt6/v13-private-remote-bridge-20261111 @ fb120481af73da2b5d9547159a8a298adb6d6646
- Branch: research-perception/v14-audio-duplex-bridge-20261123-run21
- This checkpoint adds a persisted temporal A4 receipt inside the existing audio PerceptPacket, bound to event, packet, generation, source hash, consent receipt, interval and the producing Runtime process epoch. The bridge validates the persisted receipt instead of trusting caller-supplied a4.temporal_voice.
- Every dispatch claims a one-use hash of event/packet/temporal-receipt identity in a bounded 4096-entry SQLite Store state row using compare-and-swap. Claims apply to INTERRUPT, CONTINUE and OFF. The claim happens before Runtime.lock and before cancellation; stale or cross-process receipts fail closed.
- Added adversarial coverage: forged-only temporal onset, replay against a later active turn in both interrupt and auto/CONTINUE modes, and OFF-mode consumption. The workflow now runs when the existing RAW EAR producer changes.
- Research R-114: FD-VAD (arXiv:2609.35791), FastTurn (arXiv:2604.01897v7), Next-Turn (arXiv:2606.18094). Abstract/metadata-level only; no full-text claim, code import, weights, datasets or dependency.
- LOCAL_LINUX full repository suite remains BLOCKED: no checkout mounted and git ls-remote fails DNS. No local Runtime integration result is claimed. Exact CI must run on this code head.
- Redmi: REDMI_UNVERIFIED for this candidate. Current board receipt PIPELINE_STATUS #767 reports installed 8bf44cb50e855a6dba0c91f64f60d8daddcbdc9c, auto-update enabled, Runtime/Dashboard CI_WAIT, last_error NONE. This receipt predates the b20e9 green release and does not prove b20e9 installed. UPDATE_REQUEST #737 is already QUEUED; no duplicate request. No restart, CHAT_SEND, microphone capture or permission/model/weight/data change.
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


## Device-status correction — 2026-11-23

A prior handoff sentence incorrectly described the phone as STOPPED_BY_USER on fb563. The current authoritative shared-board receipt is PIPELINE_STATUS #767: installed 8bf44cb50e855a6dba0c91f64f60d8daddcbdc9c; auto-update enabled; Runtime/Dashboard CI_WAIT; last_error NONE. It predates b20e9's green 37/37 CI and does not confirm that b20e9 reached the phone. UPDATE_REQUEST #737 is already queued. No new update request or device action was sent. This PR candidate remains not deployed and REDMI_UNVERIFIED.


## Replay-guard hard-bound and concurrency regression — 2026-11-23

- Test commit: 431fff0c92c4f72c42891b84d4770f764b4427d7; test blob: 2665a5badac8e4f28cc7cc9cc8305c21129c87f4.
- Added real Runtime/Store regression coverage for simultaneous duplicate claims: exactly one caller may claim the same event/packet/receipt; the other observes the persisted claim and rejects.
- Added a full-capacity negative: 4096 live entries cause fail-closed refusal, with no eviction of unexpired entries.
- LOCAL_LINUX isolated harness was rerun against the exact bridge module after its receipt-ID validation change: py_compile PASS; 5/5 isolated tests PASS (forged temporal, replay in interrupt/auto/off, packet CAS, concurrent claim, full-capacity refusal). Store/lease/duplex are minimal stubs; this is not full repository Runtime evidence.
- Exact-head GitHub Actions were re-triggered by the new test commit and remain queued at last poll. No CI PASS is claimed.
- The current code-bearing implementation SHA remains fea6002c4fa7def9f1dd83f51a8320fc526e4f17; current branch head at this checkpoint is 431fff0c92c4f72c42891b84d4770f764b4427d7. The following handoff-only update will advance the branch head without changing code/tests.


## Additional exact-source syntax checks — 2026-11-23

- The exact GitHub-readback test file (blob 2665a5badac8e4f28cc7cc9cc8305c21129c87f4) was copied unchanged into the local isolated test workspace and passed CPython py_compile.
- The exact workflow YAML was parsed with PyYAML; jobs and both push/pull_request path filters were valid and matched. This is syntax/path-parity validation, not a GitHub Actions pass.
- Local evidence remains: bridge py_compile PASS; test-file py_compile PASS; workflow YAML/path parity PASS; 5/5 isolated Store/lease/duplex-stub tests PASS. Full Runtime suite remains blocked locally; CI remains queued.


## 2026-11-24 — retryable handoff preparation and review follow-up

- Reproduced a separate failure in the existing duplex.handoff() consumer: it removed pending[event_id] before reading the previous event/message, parsing the stored packet, and publishing the partial-answer SourceRef. A missing event, missing user message, malformed packet, or Store.source() exception could therefore return/raise after permanently consuming the only handoff.
- Fixed v13/code/v13/duplex.py so it prepares the source-bound handoff first, then re-reads the state and CAS-consumes only the same pending entry. CAS retries reuse the already-created SourceRef. Read/parse/source failures leave the pending row available for retry.
- Added regressions to v13/code/tests/test_audio_duplex_bridge.py: missing event, missing user message, malformed packet, source-publication failure followed by successful retry, and one-use success consumption.
- Added v13/code/v13/duplex.py to both push and pull-request path filters and the explicit py_compile list in .github/workflows/v14-audio-duplex-bridge.yml; edits to the actual duplex consumer now trigger this suite.
- Exact commits: code 942bb1ce2028502bb73de5996f9e490b820196c3; tests 4663dab8ded125f8108e8152d869b242cc310f6b; workflow 2d772ca3ce36d54179de35c26d53c18de18ef736. Readback verified code blob 7d3829364c70b1473fce71e95116805406ced3ea, test blob 15e98960114103fce286ce67b4844c5f99534381, workflow blob 799382648fbc0776eac152153c59c654cba23ee0; branch head 2d772ca3ce36d54179de35c26d53c18de18ef736.
- LOCAL_LINUX isolated CPython state-machine reproduction: old implementation dropped the pending row in all 3 injected failure cases; revised ordering preserved it in all 3. A simulated single Store-CAS conflict retried successfully, consumed the pending row once, and called source publication only once. This is an isolated fake-Store reproduction, not the full Aii Runtime/SQLite pytest suite.
- Full local Aii checkout/pytest remains BLOCKED: no repository checkout is mounted and git ls-remote cannot resolve github.com. Exact-head GitHub Actions run 45291585143 ended startup_failure with no jobs; GitHub refused retry (403, run cannot be retried). No CI PASS is claimed for these new tests.
- Existing code readback also confirms the two prior Boss findings are addressed in this branch: duplex.record() is CAS/first-writer-wins per interrupted target, and on_audio_input() holds the per-Runtime handoff lock, commits the handoff before setting cancellation, and rolls back only the exact unconsumed relation if the target changed. The test file contains direct first-writer, distinct-receipt and commit-before-cancel race regressions. These branch tests still require a fresh successful exact-head CI run and independent Boss/QA review.
- Device/deployment: latest public blocker receipt #1904 comment 7108089370 says installed release 8d93236c753f0194224c19edc7411d8d7082b1d6, auto-update enabled, AI runtime STOPPED_BY_USER, autostart false, and native residency unavailable. Preserve that stop state. Candidate 2d772ca is NOT_DEPLOYED / REDMI_UNVERIFIED. No update request, restart, CHAT_SEND, microphone permission, model/weight change or user-data operation was made.
- Next: obtain a successful exact-head CI run, then independent QA/Boss review of both duplex race fixes and retryable handoff semantics. Only after that should Core reconcile the signed Android audio provider with this caller-supplied PCM bridge; microphone capture remains OFF.
