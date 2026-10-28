# Prereg: World-JEPA SHADOW fit transactional state (2026-10-28)

Owner: isolated World-JEPA training candidate `assistant/v13-run11-world-jepa-atomic-fit-20261028`. Base: merged C3+ContextOS+WorldJEPA candidate #901, audit-only docs head `2070665b23bf779ab26f62b5f2fcade3bfe06d55`; World-JEPA fit-input guard donor exact blob `87dde9c51ac9c042694870f3e15619711503a537`. Frozen Runtime/model catalog, native C3 script, registered seeds and World-JEPA learning hyperparameters must remain unchanged.

## Reproduced source risk
`WorldJEPA.fit` mutates `self._action_counts`, `self.mu`, `self.sd`, `self.history`, `self.enc/tgt/preds` and `self.zsd` *before* all fit and ensemble stages complete. A failed refit can leave an old fitted model with new partial normalization/support, contaminating SHADOW inference even though no successful fit was returned. First-fit failure can expose partially initialized state. The new finite-input guard alone does not close this failure window.

## Contract
- Stage all fit products in local variables and atomically publish the complete new fit only after all main/ensemble training, support distance and finite-state checks pass. A failed refit must retain the previous complete fit, and a failed first fit must remain unfitted. Do not mutate original parameters in-place while staging.
- Preserve successful fit mathematics, optimizer/EMA, random seeds, action counts, ensemble order, shapes and numerical outputs byte-for-byte as far as deterministic float evaluation allows. Keep zeroed/shuffled-action controls and `steps=0`.
- Reject nonfinite learned parameters/normalization/latent statistics with explicit ValueError before publication. Do not promote SHADOW results into facts.
- Add deterministic tests: injected mid-fit failure, injected ensemble failure, invalid/nonfinite learned state, successful refit and baseline deterministic parity. Test no partial state for new/previous model.
- Run focused World-JEPA + original coverage and checkpoint tests, full software suite, compile, pinned source blobs, privacy/diff, closed raw ZIP SHA256; independently audit. No native training or Redmi claim. This package must not overwrite the parallel native C3 lane or #901.
- No original Stage11/STEP2/B3/Body-JEPA/LP3/Age/whole-system gate promotion; `jepa_weight=0`, World-JEPA remains SHADOW.

Next after proof: only integrate into a verified review chain; continue actual learning utility/STEP2 work, not infer gain from state safety.
