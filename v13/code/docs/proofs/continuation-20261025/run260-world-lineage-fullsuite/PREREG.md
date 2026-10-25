# Run260 — full-suite on fitted-source-bound WorldModel v2 (prereg 2026-10-25)

Base: verified PR259 head `28a9ebcbe51661adb716ae5bdd9ca999dbf2af3c`; upstream PR258 exact full suite at `ddad7815b368819c8987695c0bee1256e104ddff` ran **2663 tests, 0 FAIL, 0 ERROR, 14 skipped** on GitHub Actions run 40184656230, job 121143490591; closed raw artifact 12596161055 SHA256 `187dd0be6fb1cc94175cfb64cd3d1bc239234a714ed3ed0a2577cde1bb5d1739`.

Exclusive ownership: this new workflow and proof directory. Do not change WorldModel, Runtime, Store, C3/JEF, Age, LP3, tests, Canon, model cohorts, native sources, or other owner's work. Reuse the exact Run258 frozen Runtime and reconstructed Run21 helper and Run147 fixture, with same pinned hashes. Heavy jobs serialized by existing `v13-native-c3-run131-serialized` group. This is a Linux software/synthetic full-suite regression, NOT a native model inference or Redmi measurement.

Preregistered: run full unittest discovery on the exact PR260 head (PR259 source + only these two files), compileall, official privacy scan, capture **all** failures and errors without editing historical tests, upload closed raw log even on suite failure. Compare test count and outcome with PR258; investigate any delta, do not infer PASS from previous run. No gate promotions: STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, jepa_weight=0, full V13 INCOMPLETE. Source integrity and model utility remain separate.

Exact next command: inspect the PR260 GitHub Actions workflow run and artifact, record counts/exit code, raw ZIP SHA256 and source head; cross-review WorldModel action-failure coverage independently without touching active PR259 owner.
