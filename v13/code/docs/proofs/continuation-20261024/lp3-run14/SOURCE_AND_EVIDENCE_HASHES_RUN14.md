# Run14 source/evidence hashes (2026-10-24)

Git blob SHA-1 is over the exact remote file bytes; all blobs below were read back from the work branch after publication. Source/tests and raw proof logs are byte-identical to the downloadable local Run14 bundle. Coordination notes in that bundle are longer local variants; remote notes are separately Git-blob-bound here.

| Repo path (under v13/code/) | Git blob SHA-1 | Local bundle SHA-256 (when identical) |
| --- | --- | --- |
| scripts/lp3_closed_evidence_audit.py | 6068ddafa2ae319f66a1cfcd7fb50127372e20a8 | cb158aaa9b8c68a07414731b98904716d90ec52bcc93859b82148dc213627785 |
| scripts/lp3_native_readiness.py | 7d76411ed11291805de712ba08093abb462154f6 | d4aecfb8acee821e6360112bb2a1126c1e117ba068f77ffd5f0cfb66c2ea9a54 |
| tests/test_lp3_review_run14.py | 913efa6e9085a60cd79619efe8ce255417865bf4 | 88a03e36928045c51e405c01e1f923ef4701b69f9b8f2bacf5e570dfdd888774 |
| tests/test_lp3_native_readiness.py | 091352a8b9469151fab0201d257dbd9b89158342 | f1e5c64ab1b1a3361cb22a6fb8a76f11ecb4b200faac611135da4e157d0393c4 |
| docs/proofs/continuation-20261024/lp3-run14/adversarial_red.log | d1bdf815132d62e5bed41f2daa2ea3f97f4cb0fe | ff179df23e9727dcf9a858ed7c5c221320e750585a6caddb5dd68b36fdfb7b1f |
| docs/proofs/continuation-20261024/lp3-run14/software-tests.log | 9c875e9ec4dd09644f877eb270a564179ee79a8a | c4adbf769e23b67182c997dcf052852a12d3a05e308f9b40afc7bab88e5d8423 |
| docs/proofs/continuation-20261024/lp3-run14/native-preflight.json | 5c4258f5c5e177d5b9a738f809d5972300075963 | 6ea7b752c505b4442a4e2350cc4ead0741d07996fc2cc5f8536dcc3e4a0b394e |
| docs/proofs/continuation-20261024/lp3-run14/compileall.log | 88189252a1a290c74841203b9ae32df8002cf7bd | 7e3c8e5b8f09a33de1a899b9ce090399fa269d907662bc75b3c02a5439b5982d |
| docs/coordination/BUILD_STATE_LP3_RUN14_20261024.json | 829182745aeca072001850bb185101a7cf10d552 | remote only |
| docs/coordination/LP3_RUN14_COMPLETION_LEDGER_DELTA_20261024.json | 00ee21de6d75b977016d7b22ed3cd06fb1e44b1a | remote only |
| docs/coordination/LP3_RUN14_OPEN_QUESTIONS_20261024.md | 7b818e6bd7a9e9cc226c0dbdebeb97124159bc1e | remote only |
| docs/coordination/LP3_RUN14_REVIEW_RESEARCH_20261024.md | a0c84f41aab4a2f3ce5891d141f7e992b97c5d8c | remote only |

Local focused source ZIP SHA-256: `2e4ba9745caee546d18a416897416091b4e86821a664829346c3eb5c77a9d782`.

No native model/Redmi or full suite/privacy-scan proof is claimed. STEP2/B3 negative gates unchanged.
