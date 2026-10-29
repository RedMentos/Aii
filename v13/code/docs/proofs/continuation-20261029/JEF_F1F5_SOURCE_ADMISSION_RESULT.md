# JEF session-bound F1/F5 human source admission — software result (2026-10-29)

Owner: GPT-6 isolated PR #1082, child of #1081. Prospective prereg commit `0a16d28a1982681a682e52a299a824bf478cc2fa` preceded implementation and tests. No model calls, training, native execution or production merge.

## Implemented and tested

`v13/jef_f1f5_source_admission.py` requires an exact current authoritative `EventEnvelope` from the active session, two distinct active session-scoped F1 fact memories, pre-materialized key SourceRefs (so admission does not create sources), `Memory.candidate` and `Memory._verified_rows` validating original F1 MemoryRecord, F5 HumanDecision and feedback lineage, `permission=record`, exact project/domain topic keys, complete SourceRefs and a global/same-session conflict veto. Only then does it call the previously tested deterministic JEF typed source consumer. Source integrity and F1/F5 lineage **still do not grant live output authority**: results remain `SHADOW_NO_AUTHORITY` with zero native calls and no learning.

[Actions 40864505103](https://github.com/RedMentos/Aii/actions/runs/40864505103), exact head `2f3f3c631885ba0a6cc0019b1f691faac8c99b6b`, **17/17 adversarial tests PASS**, including 36 P2X calibration rows with real persisted human F1/F5 source records: **36/36 complete-source A/B/NONE and 144/144 negative UNKNOWN**. Further tests: restart/replay, actual `Memory.forget` revocation, superseded memory veto, cross-session/global conflict veto, missing F5 packet, missing pre-materialized key ref without mutation, wrong current event/source, zero native calls, unchanged source count during admission. No P2X frozen 72 validation IDs or P0X holdout used.

Original ZIP SHA256 `5dee7a0fc5e05bb3c80d85bbfc6553e7594f6ced001f5e32cc03b0c6dc0b8f7d`, CRC CLEAN, **19/19 SHA256SUMS**, **8/8 stage exits zero**, privacy CLEAN, diff PASS. Private exact ZIP backup byte-verified at `/V13-Checkpoints/2026-10-29/JEF-Typed-Source/F1F5_SOURCE_GREEN_40864505103_sha5dee7a0f.zip`.

**Claim limit:** This is synthetic real-Store F1/F5 software authorization to *read* source facts, not a learned C3 receiver, not a native JEF tool, not live Runtime output, not Redmi. Human F1/F5 source creation in tests is explicit but does not prove a secure general-purpose operator UI for arbitrary two-source facts. Next substantive step is a default-off operator-visible **diagnostic** or isolated CLI, with explicit human input and full event/memory ID provenance, then end-to-end no-model regression; never silently activate the live answer path.

Age0 RECORD_ONLY; STEP2 UTILITY_FAIL; B3 L1 FAIL; Body-JEPA UNAVAILABLE; LP3 FAIL; jepa_weight0; AG6 unapproved; Redmi unmeasured; V13 INCOMPLETE.
