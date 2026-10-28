# Prereg: merged C3+ContextOS+WorldJEPA exact-source Linux-native replay (2026-10-28)

Owner: independent native validation lane on review-only branch `assistant/v13-run11-c3-context-world-native-20261028`; primary merged software candidate #901, source integration commit `169ca27aac5d1f2336c563c3d257f631936cb44d`, workflow commit `a9a9fa1577b8aaf02dff2ded8bb512749527aa10`, audit-only docs head `2070665b23bf779ab26f62b5f2fcade3bfe06d55`. This prereg is saved **before** a native workflow is created. Do not start heavy native until #901 merged software run `40672888704` is GREEN and the native concurrency group is idle.

**Scope**: repeat the *frozen*, already preregistered native CLI fixture from #900 on the **new three-organ merged tree** to detect cross-organ regression; this is an exact-source integration replay, **not** a fresh disjoint cohort or an independent generalization result. Preserve fixture, model, seed and all historical failures:
- Frozen 2-project fixture EN Veloran 428 Euro, DE Mirava 963 Euro; JSON SHA256 `4fe0977c26f5f0d213d992b17a5a4fa0b1d5fd05fa3eaf7146116076c4414eea`.
- Seed 13; C3 revision `657e078c94084481950a2d555a941481f715536b`; GGUF SHA256 `3d10b6ab8fc91a919534b9558e266255aca0bbc7f6d015963599aa9e74e05b1d`.
- Frozen native script Git blob `ccf5b5a5e080560beab90f275f8d73af4f68eaa5`, CLI `75ca7f3f197665f665d9582b7f5c2efb1f598235`, source consumer `0edb409e5ee6674e22539713874e9a038f9cba24`, runtime `68e7ed1352800174972558f1e0b0683a42c8689a`, catalog `7af05962af41d0bc3f7dd18ef01d4eba55eabf99`.
- New merged ContextOS `fd8ea629dc565a5f27b212599f3b006bb93605fd`, WorldJEPA `87dde9c51ac9c042694870f3e15619711503a537`. No model/seed/config/learning authority change.

Acceptance: exact source pins, 2/2 actual native FINAL with exact project amount, 8/8 no-native CLARIFY negatives, exactly 2 native calls, process reaped, model hash unchanged, zero Store integrity errors; source-pinned focused software tests, bootstrap and privacy CLEAN; close all raw files with SHA256 manifest. Preserve RED attempts if any. Run native serially using existing `v13-run11-age0-native-endtoend` concurrency group, no competing native/master job. Independently audit raw ZIP, back up to private Library, verify readback before claiming GREEN.

This is isolated Linux-native C3 operator CLI, not Runtime._turn integration or a Redmi measurement. Age0 RECORD_ONLY/SHADOW, `jepa_weight=0`. Original Stage11/STEP2/B3/Body-JEPA/LP3/Age/whole-system gates remain negative. Next independent work must target functional blueprint gaps, not infer gate promotion from this replay.
