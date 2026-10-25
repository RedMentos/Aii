# Run120 — actual unpacked Run119 ZIP software smoke (preregistered)

2026-10-25 UTC. Source under test: immutable Run119 PR #150 exact branch commit `e8d0e0a84ba1cedd862a58131198e9266eb39360` (not PR merge ref). Owner: new Run120 CI/proofs only. No production runtime, model, tests or canon edits. Does not overlap active Run106 episodes.py.

## Protocol
1. Build the **exact Run119 source archive** with `git archive --format=zip` from pinned commit `e8d0...` and the identical allowlisted paths, not from Run120 HEAD.
2. Verify ZIP CRC and required AGENTS, ROADMAP, decisions, both full canon copies, BUILD_STATE and executable source entry points; unzip into a clean temporary directory.
3. From **extracted bytes only**, with isolated Python + pinned NumPy/prompt-toolkit and no setup/model downloads, run `compileall` and the seven Run118 World/LateWatch regression suites (51 tests expected).
4. Run the official privacy scan. Keep exact hash and failures. This proves unpacked Python source-level usability for the scoped model-free tests only. It does not prove native models, Termux/Redmi, complete installation or end-to-end V13 utility.
5. If archive SHA differs from Run119 artifact, fail and investigate. Do not silently accept a different commit/ZIP.

## Gates
STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, jepa_weight=0, DS2 H2 FAIL, V13 INCOMPLETE. Run115 LP3 full-suite FAIL and Run117 confidence selective-risk NOT_SUPPORTED remain. Next after green: retain exact raw evidence, hashes and next command, then continue functional blueprint work.
