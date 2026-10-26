# Run412 — actual Run401 archive inventory contract (2026-10-26)

Base: Run411 PR406 head `1e5d04fd8cbe6615b0a35811c8a366961e8e4e67`; review branch only, not main. Do not change frozen model/cohort hashes, runner, age or V13 gates.

## Pre-edit observation
Run410 actual archive postflight Actions `40254485022` at `1faa880330a19f4a3fd049d94f41d2664786fb04` completed its 1.46GB ZIP SHA, per-member SHA/CRC, frozen 42-row native receipt audit successfully: `FILTERED_STAGE1_VERIFIED_NO_PROMOTION`. Its *separate* independent assertion failed because it expected **64** unlisted bin entries. Actual closed raw artifact `12621997626`, ZIP SHA256 `46dd3c4d20c5d71d52540e01401f1411cb1fbb1584afdc03d77de9acd420e364`, `RUN410_ACTUAL_REPORT.json` SHA256 `48a2a070182ac801515a55a49d67f278fc39dc32c0bfbd531c1f53901306324c`, reports **63** unlisted bin members with SHA, **7** omitted catalog-verified model members, **107** non-manifest ZIP members, **42** native rows. Previous 64 count was a prediction from Run406 inventory; retain its historical observation rather than rewriting it.

## RED-first contract and acceptance
Add independent pure-Python report gate and adversarial synthetic tests before wiring actual workflow. Gate must require exact 63 bin paths and their unique SHA/byte records, 7 registered omitted model entries, disjoint paths, 107 total members and frozen original ZIP SHA, exact 42-row status, no native inference, no Redmi or V13 promotion. Invalid or missing values fail closed. Then replace stale inline count with the new contract and rerun actual GitHub Actions audit at the exact new head. Do not call actual Run410 GREEN until that run and raw artifact are observed. Never reupload original model-bearing ZIP.

## Continuation
After a verified checkpoint, continue independent canonical implementation; native P_s20 Run411 remains blocked until Run410 actual GREEN, installed pinned models/runner, exclusive native owner, and safe export verification. Any failure remains recorded; do not promote STEP2, B3, Body-JEPA, jepa_weight, Age or whole V13.
