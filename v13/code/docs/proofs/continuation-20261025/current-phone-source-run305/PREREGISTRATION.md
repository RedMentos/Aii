# Run305 — exact current-chain Termux source ZIP and extracted-use smoke (2026-10-25)

Owner: GPT-6 automation. Base exact verified Run304 checkpoint `c0c84fa3a1939e983ec15f3e4bc3ad8ee880afba` (PR302); no overlap with active Run303 Budget, Run297 native Context OS, Runtime, Store or model owners. This package owns a new CPU-only workflow and this scoped proof directory. No production source or frozen Canon edits.

Question: Can the newest verified source (including Run302 read-only :learning and Run304 backup source closure) be delivered as an independently hash-verified, extracted, offline-initializable **Termux source-only** ZIP, without silently claiming native model execution or phone proof?

Precommitted acceptance:
1. GitHub Actions checks out exact PR head, records git SHA and Canon SHA256 `3423906b01b24443fcef733fb5c7ef47296963df63e603d8f843c99d544877ee`.
2. Use existing canonical `scripts/package_source.py --phone-install` without changing its inventory or frozen fixtures; output a single immutable `V13-Phone-Run305.zip`. Verify independently with existing `verify_phone_zip_current_run268.py` against same checkout; require member SHA256, CRC, checkout byte parity, and forbidden private/model file exclusion.
3. Extract ZIP into isolated temporary directory; run existing offline source-only setup (`V13_SOURCE_ONLY_DIAGNOSTIC=1`, no pkg/pip/native downloads) and require truthful diagnostic markers and doctor; run Run304 source-closure tests and existing phone operator tests **from extracted source**.
4. Run official privacy scan; retain raw exit codes, logs, exact source SHA, ZIP SHA256, verifier JSON, and actual ZIP as a GitHub Actions artifact. No native model run and no Redmi proof.
5. If any step fails, keep raw negative result and do not distribute as verified. Fix only within owned package or return to owner of source defect; no gate relaxation.

Scope: actual Linux extracted-source/SQLite software, not Android hardware, model utility or learning proof. Original STEP2 `UTILITY_FAIL`, B3 L1 `FAIL`, Body-JEPA `UNAVAILABLE`, `jepa_weight=0`, whole V13 `INCOMPLETE` unchanged.

Exact next command: open a draft PR to Run304 branch to trigger the dedicated workflow; inspect run logs and artifact hashes; persist BUILD_STATE; then move to substantive Canon utility/learning work.
