# Run11 independent GREEN B1 scorer × World-JEPA SHADOW integration prereg — 2026-10-28

Parent integration base PR #826 `0cc5e59fc1c91a71b0b232b42f70668c562d9d2b`. Separate review branches: PR #827 `50c24ee6450feb25cb4660f485c4f13db537de50` (7/7 focused GREEN Actions 40624407139, privacy CLEAN, RED predecessor 40624346822 retained); PR #828 `6ea120820b5d09e652238900976ded8bcdf26b84` (9/9 focused + actual synthetic 400-step GREEN Actions 40624788398, privacy CLEAN). Both source/test changes are disjoint: #827 modifies only STEP2 four-arm scorer and adds its tests/workflow/docs; #828 adds isolated World-JEPA heldout-action research script/tests/workflow/docs, no frozen Runtime/Canon changes.

## Exact integration plan registered BEFORE importing source
- Create a fresh review-only branch, no main or owner-branch mutation, no force-push.
- Import exactly the ten changed Git blobs from PR #827 and PR #828 onto base, with no text rewrites; preserve both branch heads as extra Git commit parents when possible.
- Run new independent full Linux software CI with pinned deps, focused cross-organ tests, full `unittest discover`, compile, privacy scan, diff check, source blob check, raw exits and durable private raw ZIP.
- Recheck original negative gates and no private data. This is integration proof of software-only/synthetic contracts, not native/Redmi/Body-JEPA/STEP2 or world-model utility promotion.
- If full CI RED, retain raw artifact, diagnose and fix **only on this integration branch**, never hide failure. If full CI GREEN, checkpoint exact commit/tree, raw ZIP SHA256, remote bytes and next command, then continue next canonical package.

No paid provisioning or native model downloads. The already verified GGUF/runner archive prerequisite ZIPs are independently backed up in private Library; they are not native inference proof. Remaining platform budget UNKNOWN.
