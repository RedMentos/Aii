# STEP2 four-arm native collector — operator handoff (candidate, not executed)

This review-only script is not a native proof and does not change frozen Z2/Z2b/Z2c, the Runtime, the Canon, age or learning permissions. Linux software tests use mocked run callbacks. The collector's native execution path is **unmeasured** in this workspace.

## Prerequisites
A fresh isolated installed V13 home with exact pinned B1_DETAIL and B2_GIST **different** GGUF weights, C3_LANGUAGE, llama-server and runtime libraries. Exact source/runner/model hashes must be reviewed and unchanged; the current Redmi Age-0 two-same-weight setup does not satisfy the distinct-body prereq. Confirm no active chat or native owner, exclusive installed-home `data/coordinator.lock` and cgroup/resource budget. On Redmi, `getprop ro.product.model` must prove Redmi Note 10 Pro. Do not fabricate this evidence, and do not reuse #819's stale preregistration.

## Step 1: register only, NO inference
From `v13/code`, with an existing private destination folder:
```bash
python -m scripts.step2_fourarm_native_collector_candidate \
  --installed-home "$V13_HOME" \
  --registration /private/step2-fourarm-v1.registration.json \
  --register-only
```
This writes an exclusive new registration file, prints its SHA256, and refuses missing/different B1/B2 model weights. Persist its bytes, the exact script/source hashes, installed artifacts and operator review *before* any native run. A new source revision requires a new registration.

## Step 2: opt-in native run (NOT performed here)
Only after the above registration is durably reviewed and the installed owner is actually free:
```bash
python -m scripts.step2_fourarm_native_collector_candidate \
  --installed-home "$V13_HOME" \
  --registration /private/step2-fourarm-v1.registration.json \
  --registration-sha256 "<EXTERNALLY_VERIFIED_64_HEX_SHA256>" \
  --work /private/step2-fourarm-FRESH-UNUSED-DIR \
  --device-kind LINUX_NATIVE \
  --exclusive-owner-confirmed \
  --execute-native
```
Use `REDMI_NATIVE` only on the verified Redmi device. A run creates 12 distinct native work directories, 12 sealed summaries and raw bundles, then a SHA-pinned `manifest.json`. Any interruption leaves raw partial files intact; never resume into that path or silently rerun failed rows. Expect long native runtime; serialize model jobs and stop on ownership/resource conflicts.

## Step 3: separate read-only evidence review
After #821 sealed scorer/IO is integrated with this exact collector revision:
```bash
python -m scripts.step2_longnote_fourarm_io \
  --evidence-dir /private/step2-fourarm-FRESH-UNUSED-DIR \
  --manifest-sha256 "<COLLECTOR_PRINTED_MANIFEST_SHA256>"
```
This still produces **diagnostic-only** paired utility; review source/model/runner bytes and raw records independently. Never promote STEP2, B3, Body-JEPA, jepa_weight, age or whole-system completion from this run alone. No raw user/private evidence belongs in a public PR. Save closed raw evidence privately and preserve failed attempts.

## Open technical risks
- The opt-in real native path has not been executed; CI only covers mocks and software.
- Redmi owner/cgroup and thermal/energy budgets require on-device evidence.
- The model manager must resolve the registered distinct B2 model; Age-0 shared-weight setup is insufficient.
- Native report byte closure, model identities and post-run source invariance must be independently reviewed before accepting any result.
