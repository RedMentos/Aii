# Run11 paired native archive audit: exact frozen scorer replay — 2026-10-28

After the initial local shim-only sanity pass, the **exact frozen scorer source** and **exact frozen fixture bytes** were independently reconstructed in the local isolated audit workspace and verified by Git blob SHA1 against the source registration:

- `scripts/age0_bilingual_arith_scorer.py` Git blob `0348b17dedc0e4142a73a8ad8c93a57a2c7d6491` (byte-exact).
- `specs/age0-bilingual-arith-heldout-20261028.json` Git blob `ceda0a5cb506cf09885652b24893cf7d8fdff63b` (byte-exact).

With those exact source bytes, the new read-only archive auditor reprocessed the unchanged **candidate** and **baseline** native ZIPs. Both passed all source/row/metadata/score bindings, including the frozen lexical recomputation; the resulting aggregate-only JSON was **byte-identical** to the initial `RUN11_BILINGUAL_PAIRED_NATIVE_AUDIT_20261028.json` (`cmp` PASS). Independent local regression: **9/9 tests PASS** using exact frozen scorer/fixture, replacing the earlier shim qualification. The exact-source GitHub software workflow `40639051157` was separately GREEN (26 focused / 2243 full, 1 skipped, artifact SHA256 `b2bdb166892e87419554d48325bae7eba4a2ea76d032fc70f9e196a1f1b208b3`).

This strengthens reproducibility of the **lexical** result only. It does not establish semantic grounding, causal generalization, Redmi latency, learning or any Age promotion. Frozen scorer and fixture remain unchanged in GitHub.
