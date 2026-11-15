# A5 source-admission QA follow-up — 2026-11-15 18:00 CET

Owner: Research/Perception. Parent PR #1972, P0 #1904. QA review found rejected source-ID poisoning at head 93fdeac. This change reserves source IDs **only after accepted**; no unconsented or provisional packet can suppress a later valid final packet. Strict source ID/text bounds and exact bool/int checks added.

Files: `percept_admission.py`, `test_source_poisoning_20261115.py` (7 adversarial unittest methods). Existing `test_percept_admission.py` still needs full regression.

Run from `v13/code/research_perception`:
`python -m unittest -v test_percept_admission test_source_poisoning_20261115`

**Evidence**: source commits eb1af3f97b476896198272837b8cb0a7e81948b9 and 181974b8aeb47023ed5b2416563a018628ace9be. Tests NOT RUN by this connector session; CI NOT VERIFIED. No Android evidence, no native tokenizer validation, no runtime integration. NOT_RELEASED / REDMI_UNVERIFIED.

**Low-risk**: isolated SHADOW admission correctness fix and synthetic tests. **High-risk**: wiring into actual A5→C3 prompt admission and permission boundaries. Core/Boss must check source ID namespace across modalities, exact tokenizer, mandatory-current-user semantics and P0 prompt budget; never silently discard required source. Official Age0 and learning gates unchanged.

Next: run tests and CI on exact SHA; review PR #1975 mandatory-source fail-closed behavior, then integrate only after Boss approval. Redmi must separately prove a real end-to-end response and B1/B2 offers.
