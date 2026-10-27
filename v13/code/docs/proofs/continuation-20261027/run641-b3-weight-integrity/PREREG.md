# Run641 — B3 exact binding must also bind loadable weight bytes (preregistered 2026-10-27 UTC)

Parent: Run640 review head `0928f3e06855efd4596f7322a1574d9f30fea3e8` (PR #636). Own only `v13/code/v13/bodyport.py`, `v13/code/tests/test_bodyport.py`, this scoped proof directory and Run641 CI. Do not alter the original Run640 files on its branch, model hashes, registered cohorts, seeds, acceptance criteria, learning authority, or Canon.

## Observed gap / hypothesis
Run640's `Ports.bridge_valid` verifies manifest direction and both exact live model bridge keys but does not require `<direction>.npz` to exist or verify its weight digest. A forged/stale manifest alone can report True; corrupt/truncated bridge weights can be accepted by the predicate even though the actual `Bridge.load` will reject them. This is a software integrity bug, **not** proof of B3 latent utility.

## Frozen intervention
Make `Ports.bridge_valid` fail closed unless `Bridge.load` successfully reads the exact matching `.npz`, validates the bridge's saved array digest against the manifest and the current exact live sender/receiver revisions, then checks both bridge keys and direction against that same loaded manifest. Do not grant LATENT authority. Preserve existing `Bridge.save` format and standalone legacy load API. No changes to B3 training, metrics, L1 gate or model bytes.

## Prospective tests
1. Real tiny NumPy bridge with matching bound manifest + NPZ returns True.
2. Same manifest with NPZ missing returns False (pre-fix False? expected pre-fix True).
3. NPZ with a changed valid array, leaving manifest unchanged, returns False (pre-fix True).
4. Truncated/corrupt NPZ returns False without exception (pre-fix True).
5. Legacy revision-only, wrong side key, same revision changed hash/capability, wrong direction, invalid live hash remain False.
6. Body-swap and body-port regression suite remains green; source compiles and public-repo privacy scanner reports CLEAN.

CI must run exact source with isolated NumPy dependencies, preserve raw logs, exits and hashes. A failure is recorded as RED and must not be retroactively reclassified. No native/Redmi claims from Linux software tests.

## Evidence and gates
At prereg time original negative gates: STEP2 UTILITY_FAIL; B3 L1 FAIL; Body-JEPA UNAVAILABLE; jepa_weight 0; Redmi unmeasured; whole V13 incomplete. Branch-scoped review only; no main merge. Next after source CI: independently inspect exact run, archive raw bytes privately if permitted, and proceed to a distinct functional blueprint package.