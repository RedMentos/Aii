# Run626 — opt-in query-conditioned Context OS digest, source-bound

2026-10-27 UTC. Review-only PR621 child of Run625 PR620 exact head `551e18be6948bdb849d6c1532c138a1c4f576d2c`. Frozen prereg commit `8f1b36bcab3e968770820daa3de08f461ef16639`; new test committed `4daf7c7503357fc60bf79a56804459d84377f4dd` **before** three source patches `6c56d746`, `2bd7f2eb`, `6153aeda`. Two additional adversarial tests were added **after** source patch in `7a6b3134`, transparently labelled supplemental.

## Executable functionality

Existing `context_items(...)` default **recent** path remains unchanged, and persisted Context OS default is `digest_selection=recent`. New explicit operator `:ctxos digest select query` switches to a deterministic lexical ranking using existing `memory.relevance`, applied only to source/history-revalidated, nonexcluded Sleep A digest entries. It uses exact extractive lines, stable recency tie order, a bounded character cap and no-match fallback to the old recent path. `:ctxos digest select recent` restores the old behavior. Selection persists across Runtime restart and cannot be changed while a turn is active. The actual C3 Runtime `COMPRESSED` layer now consults this mode and current query; no learned model, fact authority, native KV or training right was added.

## Evidence and measured limits

- Original Run625 source **RED** on the preregistered new regression (missing selector/keyword, operator state), exit **1**.
- Final exact-head GitHub Actions **`40419228581` SUCCESS**, HEAD `ee8cdc638d848974f90af121322fca94c91925b6`: patched **33/33** Linux SQLite/source-only tests PASS; privacy **CLEAN**, exit 0. The tests include the 12-turn fixed old-topic lexical recall comparison (recent under 170-character cap misses; opt-in query includes exact older source), mocked C3 live prompt injection of the source-valid digest, persisted idle-only operator mode, restart, cross-session isolation, source revocation, no-match fallback, equal-score newer-first, cap and invalid-selector fail-closed, plus existing Run624/Sleep A/Context OS regressions.
- **This is lexical source selection, not measured model answer improvement.** No native B2 inference or semantic utility benchmark was run, and no claim that the old-topic test generalizes to new topics is made. The original model default remains recent until independent utility/OOD/ablation evidence.
- Source blobs: `sleep_offline.py` `19761bc0abe6dd3fa0123c1e94d7cf03e425773a`; `context_os.py` `8e43a7dadaf4fc169c9e3a394f06f12a97e0a224`; `runtime.py` `02b1c5e38cd042b829f8819f856fe7df870004ae`; final test `1e6981fd78bcfc88fa2622a731df9a951bd62955`. Canon SHA256 `3423906b01b24443fcef733fb5c7ef47296963df63e603d8f843c99d544877ee` unchanged.
- Original SHA-closed final raw artifact **`12696396729`**, ZIP SHA256 **`99fb4d0fe3dafb867a6cd4e652d89a6885738e15c5410aa2d61ec8b797d7d666`**. All **12** internal raw hashes independently verified. Private Library `/V13-Checkpoints/2026-10-27/Run626/run626-expanded-exact-head-SHA_99fb4d0f.zip`, materialized back byte-identical PASS. First successful 31-test attempt (before added adversarial tests) retained separately with artifact `12697895241`, ZIP SHA256 `84a1724159a05890abd05af7495395adf75b43b71300e938174e6062077ffda7`.
- No model, source cohort or seed hashes modified; no Redmi/Termux native test; no main merge. STEP2 `UTILITY_FAIL`, B3 L1 `FAIL`, Body-JEPA `UNAVAILABLE`, `jepa_weight=0`, V13 `INCOMPLETE`.

## Next

Review source/CI independently, then package an **exact-current source-only Termux ZIP** with this opt-in selector and an operator help entry, verify extracted real SQLite tests and byte parity. Separately pursue native Body learning and heldout answer-level utility rather than promoting a lexical helper.
