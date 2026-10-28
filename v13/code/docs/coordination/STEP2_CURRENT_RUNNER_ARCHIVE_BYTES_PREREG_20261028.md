# Current-catalog llama.cpp source/binary archive byte proof — prereg 2026-10-28

Distinct follow-up to B1/B2/C3 GGUF byte retrieval, still **artifact-only**. The unchanged `specs/models.json` Git blob `7af05962af41d0bc3f7dd18ef01d4eba55eabf99` pins runner tag `b10964`, source revision `b29c606e2`, source tar SHA256 `4c96d72c40cefdacf621457d8a12fe5673b8de5b640ff7fe6d342ea1c579a9fe` and Linux x86_64 release tar SHA256 `9abf88aea48a55d0f80edb1ee20220b186848cca0b4e919d71518cfd7ca67443`.

Authorized package: use the existing SHA-checked ModelManager `download_file` into a NEW isolated Linux scratch directory, independently rehash source and binary tar.gz bytes, verify nonempty safe tar headers without extracting or executing, and seal only sanitized source/archive metadata. No binary upload, no native inference, no model redistribution, no historical cohort/runner pin change, no paid provisioning. Source and binary archives are not the same as executable/library hashes; actual native collector requires the exact installed executable and library bytes separately.

Software-only local HTTP tarball fixture tests must cover successful exact-byte closure, wrong catalog pin, corrupted tarball and wrong downloaded hash. Preserve RED and GREEN raw logs, use branch-only review, no gate promotion.
