# Run435 — one serialized actual Linux-native P_s21, preregistered before queue

Date 2026-10-26. Owner GPT. Branch `codex/run435-native-p21-serialized-20261026` stacked on Run434/PR433 checkpoint `f436873120a60836227bc7829f7900d5cd221a8e`. Run434 source-only Actions 40265706361 SUCCESS 50/50; Run433 actual independent 168-row postflight Actions 40265361929 SUCCESS. No active native owner observed before preparing this branch. **One P_s21 attempt only.**

Actual upstream Run427 producer Actions 40263042202 head f98db0c7bca16c005bc987bcc507aa3abbdf66f4 SUCCESS; raw ID 12626041558 SHA256 3f7b66330778bd2129673c74d2917dcfe9b6ef8e2281df7f8557fd5c89bcecf5; safe work ID 12626146409 SHA256 405e62268b0314c6e852e367a4624a12508e971877afe14afebf05cb2afba6b7. Independent Run433 head c0f7769d25fa03a14bcf3c162088559da9765492 SUCCESS; verified all four native receipts and manifest SHA256 bde79cc2b97fe58e252ace1cfaa800a2bcae1482e61ec23743f6f1423238668d.

Workflow requirements: exact source/model/runner pins; independent producer/postflight GitHub metadata and ZIP SHA; isolated pinned public models, no paid provisioning; Run430 atomic import; Run434 preflight all four previous 42-row native receipts, then unchanged Run397 `max_new_arms=1` P_s21; validate 210/378 structural rows and no gate promotion; safe no-model export and small raw even on failure. Serialize with `v13-native-c3-run131-serialized`, `cancel-in-progress:false`; never parallel heavy native. If red, preserve all attempts, don't silently retry. New independent 210-row verifier needed before S_s21.

STEP2 UTILITY_FAIL; B3 FAIL; Body-JEPA UNAVAILABLE; jepa_weight=0; Redmi unmeasured; whole V13 incomplete.
