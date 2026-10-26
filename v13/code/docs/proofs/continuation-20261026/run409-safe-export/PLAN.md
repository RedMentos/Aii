# Run409 — prevent model-weight republishing in future native checkpoint exports (2026-10-26)

Owner: GPT scheduled continuation. Base Run408/PR403 `989b37e`, stacked review not main. New standalone `run409_safe_export.py` and adversarial tests/workflow only; no frozen Run394/Run397 model, fixture, seed, runner or active native owner changes.

Run401 native stage1 succeeded but public artifact 12620379581 is 1.46GB and Run406 exact SHA-bound inspection RED on model weights. The native harness intentionally creates `models`/`bin` symlinks into the installed pinned model home. The broad `actions/upload-artifact` glob likely dereferenced those symlinks. Do not repeat that pattern.

Build an explicit export of every actual regular file from the native work tree, without following any symlink. Only arm-home `models`/`bin` symlinks pointing to an operator-supplied installed home may be omitted; all other symlinks, unexpected regular model weights, missing/unsafe files, failed-attempt loss, path traversal or destination collision fail closed. Hash every exported regular file, record omitted symlink paths and SHA closure; use atomic no-clobber install to a fresh staging directory. No native inference, no upload in this package; later native workflows must upload only the vetted export and preserve original negative evidence. No model weights or private data in git.

Acceptance: adversarial source-only tests, compile/privacy, exact-head CI; no claim of actual native export until exercised on owned native work. Original Run401 ZIP remains untouched and all STEP2/B3/Body-JEPA/jepa_weight/Age/Redmi/whole V13 negative gates stay negative.
