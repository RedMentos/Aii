# Run265 — exact full-suite after synthetic WorldModel ablation source-scope repair (prereg 2026-10-25)

Base: verified PR264 head `1336793237f295092701b9ce8fd895d7300557d6` (PR259 source-bound v2 + PR260 exact full-suite + Run264 synthetic-only compatibility fix). Exclusive ownership: new workflow and proof folder. No production WorldModel/Runtime/Store, frozen tests, Canon, registered models/seeds, native sources or gate changes.

Run260 full-suite on PR259 exact head `bfe8896348eff0016f67c83344a2a8096940bd07`: **2669 tests, 2 FAIL, 0 ERROR, 14 skipped** (run 40185499205, artifact 12595902858 SHA256 `1959b681a2da917cfb0085400903da55e51c2b02ffd3ef0ab0a50bb4d97fb927`). Both failures were the preregistered synthetic confidence ablation using real Store with patched synthetic transitions. Run264 focused actual-source CI: **19/19 PASS**, privacy CLEAN (run 40185990655, artifact 12595588523 SHA256 `b4c9439ee397e78f98da8b9e0eb59a65d618734b2492500e63fa5a691090b07f`). Source guards unchanged.

Predeclared: rerun full `unittest discover` on exact Run265 head, pin Runtime and reconstructed Run21 helper and Run147 fixture, isolated CPU dependencies, official privacy scanner, preserve all failures and complete raw log. Serialize with existing native group. Expected count may rise due new Run264 tests; no automatic PASS claim. If any failure, preserve and investigate rather than change historical tests or lower source requirements.

Evidence classification: GitHub Linux software/synthetic full suite, not native model inference, not Redmi, not body training. STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, jepa_weight=0, full V13 INCOMPLETE. Independent Run261 valid ERROR/nonterminal DISPATCHED source-binding failures remain unresolved and must not be concealed by a green suite.

Exact next command: inspect Run265 Actions jobs and raw artifact, record exact test count and exit code; then reconcile Run261 under PR259 owner and run native/Redmi proof separately.
