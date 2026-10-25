# Run268 — verified current V13-Phone source-only ZIP (prereg 2026-10-25)

Base: PR267 exact head `0e522d390e35e7eb24de2c034c1cb16979804df6` (Run264 WorldModel synthetic ablation fix + Run267 native G13 asset binding). Owner only new independent ZIP verifier, tests, workflow and proof. Do not edit frozen Runtime, Canon, model registry, setup.sh or other owner's code.

Objective: deliver a **reviewable current runnable-source ZIP** using existing `package_source.py --phone-install`, with manifest SHA256 for every included file, source-tree byte parity, CRC, required Canon/AGENTS/installer/Runtime, executable launchers, and rejection of duplicate/traversal/symlink/private/model members. The historical Run144 verifier pins old Run141 bytes and cannot validate the current ZIP; new verifier is generic but still strict. Tests cover valid ZIP and tamper/omission/escape cases.

CI: exact PR head, official privacy scanner, unit tests, build immutable source-only ZIP, independently verify against checked-out source, preserve raw output, exit codes, source head and ZIP artifact with SHA256. No model weights, secrets or private user data in artifact. This is not a Redmi install, not native execution, not acceptance; user must run setup.sh on device and grant normal local installation permissions for phone proof. Do not ask for that until needed.

Claim boundary: STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, jepa_weight=0, full V13 INCOMPLETE. A verified ZIP is a source checkpoint, not a completed AGI system.

Exact next step: inspect Run268 CI, download/verify ZIP artifact and manifest against remote head; preserve failure if any. Then provide a usable source ZIP link and continue independent native/utility/Redmi proofs. Rejected anyone-writable Drive destination not used.
