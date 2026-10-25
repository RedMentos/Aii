# Run177 native-firing integrated source chain reconciliation — prereg (2026-10-25)

Base: verified PR256 source-drift audit head `ff89e52be43df7a5b306e2c16587273ed1c4b4d7`. Exclusive production-like ownership: `v13/code/scripts/integrated_candidates.py` **only** (source-chain reconstruction, not live runtime), new test, unique CI and proof directory. No edits to live runners.py, Runtime, historical snapshots, model/seed registrations, Age, DS3, WorldModel, LP3 or any active owner.

Exact drift evidence: PR256 GitHub Actions `40184314153`, source diff SHA256 `e72ac6d55f2f857196b77b805b1e1c7ce72cd411a55662c51086e24ee91ea1b1`, 28 diff lines, **only** runners.py differs. Expected integrated SHA256 `87312169d871bcb1498ad028df058b0ab6e100f6e51c011ead4b9ecfb1b831c5`; live SHA256 `18db214f930953a5f781aa8aaa2b4425e048fd8bacf7848793c112a4e06af798`. Difference matches reviewed GitHub commit `dd122cf8f5c5` Run177 exactly: tap docstring, B2_GIST native dimension 1024 and Qwen3.5 tap_id. Three other live files already match.

Predeclared acceptance:
1. RED-first test on current chain must show `integrated_candidates.integrated_sources()['v13/runners.py']` is not live and `overlay` refuses.
2. Add a single narrowly scoped Run177 transform using three unique exact anchors, append it **after** existing reviewed transforms in `_later`. Do not replace, weaken or delete any existing chain step.
3. GREEN: four integrated files byte-equal to live; runners SHA256 matches `18db214f...`; original frozen snapshots and Run177 live source bytes unchanged; `overlay` accepts only exact integrated live.
4. Run existing historical native-firing candidate source and merged software tests without actual native model; fail-closed tests must still pass for mismatched assets and no semantic authority.
5. No actual native firing/quality claim. If further errors appear, preserve raw logs and do not claim full suite PASS.

No STEP2/B3/Body-JEPA/jepa_weight/whole V13 gate promotion. Run255 full suite concurrently collecting independent pre-fix failure evidence; heavy jobs remain serialized.
