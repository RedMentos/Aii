# Run410 — actual observed Run401 native stage1 filtered postflight (2026-10-26)

Owner GPT scheduled continuation; base Run408/PR403 at `c4648d2228cc9df35e984b84dd18f8e13cb754de`, review branch not main. Only own workflow and proof files; no frozen source/model/seed changes. No model inference, no native stage2 in this package.

Run406 third read-only inventory Actions `40253489055` observed exact original ZIP SHA256 `65ac00a8cd2013ebab76828ed3bc25dee5433d1d55a995573387f19de29b530a`, artifact `12620379581`, 108 ZIP members, 37 original sha-manifest entries, 71 unlisted symlink-dereferenced installed files (7 model files under original arm-home models, 64 binary/library files under bin), 0 manifest entries missing, uncompressed bytes `1591344395`. The original ZIP remains immutable and has not yet passed CRC/member SHA/native receipt independent audit. Original upload incorrectly included model weights; never upload ZIP copy.

Run410: download original observed ZIP once, enforce exact artifact metadata and SHA, run Run408 streaming member SHA/CRC and frozen Run402 native receipt validation in read-only mode; allow only exact registered model files omitted from temporary stage and original arm-home bin bytes preserved but never executed. Assert 107 verified non-manifest members, 7 exact catalog model exclusions, 64 unlisted bin members, 42 real native O_s20 rows, 8 remaining arms, no gate promotion. Preserve raw report/hashes even on RED. No Redmi claim.

If GREEN, next separate package may use verified restored work and Run409 no-model exporter for opt-in Run404 P_s20 native continuation under exclusive native owner. If RED, preserve failure, do not bypass or infer.
