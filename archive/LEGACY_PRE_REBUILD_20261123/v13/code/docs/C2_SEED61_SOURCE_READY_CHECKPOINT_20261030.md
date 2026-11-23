# Seed61 source-ready checkpoint — 2026-10-30 (review-only)

Parent PR #1214, new child branch `assistant/v13-seed61-isolated-body-postclose-20261030`. Immutable preregistration committed first at `8713ee286a6a20a777ce266a557b316c46599429`; source/test implementation committed later. No original seed53/seed59 fixture, scorer, raw artifact, model, runtime, or gate was altered.

## New implementation

- `scripts/c2_isolated_postclose_seed61_20261030.py` uses 24 fresh Age0 homes, seed61 fixture SHA256 `bf4c4da0de4c79bb66555f6e442fe9daacb0affa34b4cf9126bb51d4a83e5bf3`, six cyclic arms, frozen seed53 source-bound scorer, and original model catalog.
- A/B/C single-final-role controls disable background observers. B1/B2 actual final role and model are checked from persisted event; D/E/F retain background observers. This isolates the source of the seed53 invalid B1/B2 arms rather than retroactively relabeling them.
- Body release history is captured both **before** and **after** `runtime.close()`. Each persisted final runner PID and every OfferPacket native runner PID must match a reaped post-close release receipt of the same role. Unexpected body roles, unreaped processes, forged PID, missing source bindings, wrong model, wrong route or C2 provenance veto validity. C2 before-close alive/source-exact and after-close reaping are separately persisted for independent raw replay.
- Source records each invalid turn and original raw evidence, zero-scores invalid rows, and keeps all negative gates. Two comparative signals are explicitly **diagnostic only**, not STEP2 promotion.

## Verified tests and persistence

- Local software adversarial tests **12/12 PASS**, `py_compile` PASS. Tests deliberately use stubbed model imports and are **not** native inference proof.
- Exact prereg/source/test and canonical/model pins were verified by source-only GitHub Actions `41007535305` at `84e60ef668f77405b6692c88479712f70c556dcf`: GREEN; original ZIP SHA256 `7e6352688789323aec68d0990da90ed13ecdb6dfe5c119a96547c1b2335259d5`, CRC clean, 20/20 SHA256SUMS, all 9 stage exits zero, actual runtime module import/scaffold PASS, privacy/diff PASS. Original ZIP privately backed in `/V13-Checkpoints/2026-10-30/Run12-Seed61-IsolatedPostclose/` and byte-exact SHA256 verified after materialization.
- The later source revision `a37bec247276ce714f6f55d546f1f6ce8f331fba` adds persisted C2 before-close evidence, and preflight workflow pin revision `bb61c0d21278f48f2f0fa2f2ddc0f152bb8860be` rechecks that exact source. At this checkpoint its CI result is **PENDING**, so do not claim native readiness from that revision yet.

## Next exact action

Check Actions for `v13-c2-isolated-seed61-preflight-20261030.yml` at `bb61c0d21278f48f2f0fa2f2ddc0f152bb8860be`, download original raw ZIP and verify all stage exits, CRC, inner SHA256SUMS and private backup. If GREEN and no heavy owner active, create a separate serialized source-pinned Linux-native workflow using `python3 v13/code/scripts/c2_isolated_postclose_seed61_20261030.py --home "$V13_HOME" --out "$e/pilot"` with a **fresh** output directory and preserve original raw on PASS or RED. Never re-run original seed53/59 in place. Native proof and Redmi proof remain absent.

**Gates:** Age0 `RECORD_ONLY`; STEP2 `UTILITY_FAIL`; B3 `NO_PROMOTION`; Body-JEPA `UNAVAILABLE`; `jepa_weight=0`; Redmi unmeasured; whole V13 incomplete. Platform budget UNKNOWN.
