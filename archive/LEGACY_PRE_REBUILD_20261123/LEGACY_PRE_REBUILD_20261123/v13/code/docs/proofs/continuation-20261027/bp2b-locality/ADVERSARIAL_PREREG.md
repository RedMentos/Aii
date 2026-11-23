# BP2b adversarial follow-up · prereg before counterexample tests

Base source: `631c532f6e01db579d2b29ac39ad86c3a10fef2d`, software Actions `40501008646` 6/6 PASS, raw ZIP SHA256 `1ba68d762d5b7effdde8056213112f63af4f2179e8c82eeb02e848bd48f0ba8a`, private byte-identical Library backup.

Counterexamples identified by fresh manual review, before source fix:
1. Mixed-case `What is my cat and where i work?` currently leaves unrecognized lower-case `i` in the rewritten anchor (ungrammatical and unsafe to treat as a subject shift). Must return None.
2. Quoted `What does 'my cat' mean?` currently rewrites a literal quote and corrupts its meaning. Must return None; genuine possessive `cat's` remains supported.
3. No generation of a target string or reserved substitution, no new learning authority, original BP2a cohort unchanged.

Procedure: add the two RED counterexample tests first; capture raw GitHub Actions failure artifact and source SHA. Then minimally patch only `locality_anchors.py` and rerun same tests, compile and privacy scan. Keep failed raw and passing raw separately. Do not claim native model utility. Exact test: `cd v13/code && PYTHONPATH=. python -m unittest -v tests.test_bp2b_locality_anchors`.
