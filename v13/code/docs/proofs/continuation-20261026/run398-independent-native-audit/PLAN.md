# Run398 — independent postflight of Run395's exact-head native artifact

2026-10-26. Owner: GPT continuation; **source-only preparation**, no competing native job. Base Run397 checkpoint `32fd1402f39cc89bde95ecfec48df3921dd9da3d`, stacked review. Own files: `.github/workflows/run398-step2-independent-native-audit.yml` and this proof directory. Run395/PR390 actual Linux-native 42-row pilot remains a separately owned serialized job at planning time.

**Goal:** Once Run395 completes, fetch its exact workflow artifact (run `40247992605`), verify ZIP/manifest raw SHA256 and every expected raw JSON, then execute unchanged Run396 read-only audit against **actual** 42 native rows, not synthetic stand-ins. Preserve failed/incomplete raw, distinguish current-rule override from accurately quoted old rule, calculate paired P−O/P−S differences. No model download or native inference in Run398. Artifact must be bound to Run395's exact head `48d2119dbbc7077da10b625ca4ff5819bfc74730` as printed in `RUN395_HEAD.txt`; PR merge SHA is not accepted as the checkout source SHA.

**Launch guard:** Do not open a PR/trigger this workflow until Run395 job is completed and its artifact ID/digest have been observed. If Run395 is RED, still preserve and independently diagnose raw, never silently promote or fabricate missing rows. GitHub Actions requires read-only `actions: read` for artifact retrieval; no secrets, paid provisioning, private model weights or personal data uploaded.

**Negative gates:** STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA/jepa_weight=0, Age0/approval unchanged, no Redmi proof, Run389 full-suite RED, V13 incomplete. Even a structurally valid pilot is only 2 fixtures/seed20, not the registered 378-row full cohort or a canonical STEP2 pass.

**Next:** After Run395 completed, inspect artifact, pin artifact ID and digest into workflow before triggering PR. Run source-only Run394+Run396 controls and privacy, independently verify 42 rows, close SHA and private Library mirror. If the pilot fails, preserve RED and diagnose rather than changing the frozen cohort.
