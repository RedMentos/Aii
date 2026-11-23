# Context OS F5 warm + Sleep A/B F5 integration — preregistration

UTC 2026-10-28. Owner GPT-6 review-only. Base PR #797 exact `c9de3de39a6b11c650e32dc2ffbb7fb7ee0a66ee` (dependent on PR #796, which itself descends from combined PR #794). The PR797 focused/full test result is pending at preregistration; **do not edit source until its exact CI passes**.

Independent verified prior source: PR #795 `assistant/v13-context-warm-f5-review-20261027`, candidate `context_os.py` blob `127af0b872bfce002c6dd72020a22574f52691e8`, exact Run271 test blob `cc1423c7f4961b038f073c77ceec6a31cbc99a43`; Actions 40600569995 SUCCESS: 69 focused, 2056 full (1 skipped), raw exits 0, privacy CLEAN. Its parent memory F5 blob `501c8f43c92f031e034e4b93f4adbd4c67b7edfe` matches PR797. PR797 ContextOS source currently `07b46ade7a1dbefce01343c95ea822c8a6deca3e` and is missing warm F5 verification.

## Narrow change

Only import the exact source and Run271 test from PR795 after confirming the current branch's source outside `ContextOS.warm` is byte-identical to PR795. Preserve all other production sources, including `sleep.py=2fa642218712a217a6d55061c9208e2445c0be25` and Memory F5. Keep exact original failed REDs and no changes to Canon, cohorts, model/seed hashes, C1/B3/World/HX/AG8. Add dedicated pinned Actions full software test workflow for combined Run271, Run274, exact-ID fixture, Memory F5, ContextOS, Sleep and full suite; check privacy and raw evidence.

## Acceptance and limits

Both old and new guards must work together: revoked F5 must not reenter C3 warm context, Sleep A retention or Dream B seeds; valid independent second correction remains usable; exact-memory-ID checks remain strict. No native/Redmi or learning evidence; no Age/approval change. STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, jepa_weight=0, whole V13 incomplete. No automatic merge; this is a dependent review chain. Stop source integration if parent CI fails or branch diverges. Next: inspect parent CI, import exact blobs, focused/full tests, independent review, remote byte verification, then next independent package.
