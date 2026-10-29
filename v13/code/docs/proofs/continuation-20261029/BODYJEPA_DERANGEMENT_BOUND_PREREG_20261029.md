# V13 Body-JEPA shuffled-target derangement boundedness — prereg (2026-10-29)

## Parent, scope, observed source risk
- Review-only child of PR #1152, exact parent `e5e054c7059181952ff2919789c2652e7ce97c45`; owner only `v13/code/v13/body_jepa.py`, new dedicated tests, new focused CI/proof. No other owner file edits.
- `v13.body_jepa.derangement(n,rng)` currently uses unbounded `while True` calling `rng.permutation(n)` until no index is fixed. For a deterministic/repeated identity RNG, this never terminates; malformed permutation with no fixed points can also be accepted. A B-JEPA shuffled-target negative control must not hang or silently accept invalid pairing.
- Original source Git blob `d510e72d12ecf1d4d300be816ac074a384c0c6f7` is **test_body_jepa.py**, not body_jepa.py; the body_jepa.py source hash must be captured in CI before modification. Canon Git blob `218464b12a2d27d92524c751922fa8e1c3fb0ea7` is immutable.

## Registered adversarial tests before implementation
- A fake RNG returning the identity permutation for 64 calls and raising on call 65 must result in a bounded explicit `ValueError` (`derangement attempts exhausted`) without reaching the 65th call. Old unbounded implementation instead leaks the fake RNG's `AssertionError`.
- A fake RNG returning a malformed fixed-point-free list with duplicate indices must be rejected `ValueError`, not accepted as a valid shuffled-target control.
- A normal fake RNG returning identity then a valid cyclic derangement must return the second permutation unchanged, with exactly two calls. A valid `numpy.random.Generator` seeded control in the existing test must remain unchanged.
- Input `n<2` stays `ValueError`. No deterministic fallback is allowed: exhausting random attempts must **fail closed**, never invent a shuffled negative control.

## Limits and execution
Use 64 maximum draws (BOOT safety cap, not measured optimal). No changes to successful first-draw or later successful sequences, no registered model/seed/cohort/teacher changes. Run dedicated stdlib tests first, plus existing Body-JEPA unit tests only if dependencies already available. No synthetic result is native/Redmi or learning utility. Historical frozen source hashes are not rewritten. Age0 RECORD_ONLY, STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, LP3 FAIL, jepa_weight0, V13 INCOMPLETE.
