# A3 teacher/student research — 2026-11-10

Scope: A2 frozen teacher and A3 projector; research findings do not alter the
V13 model, original Canon, learning permissions or any runtime gate.

## JEDI — EXPERIMENT, not a V13 result

- Bhaumik et al., *JEDI: JEPA-to-Edge Distillation for Efficient Cropland
  Segmentation from Satellite Imagery*, arXiv v1 2026-09-07, preprint:
  https://arxiv.org/abs/2609.07915 . Project source pinned at commit
  `bf960b50524971420511e5c569593cdbdd1dcf60`:
  https://github.com/Kishor-Bhaumik/JEDI/tree/bf960b50524971420511e5c569593cdbdd1dcf60 .
- Authors report 68.0 mIoU for a 4.04M-parameter B0 student versus 52.0 without
  distillation and 70.0 for a 639M I-JEPA teacher, on CalCROP21 remote-sensing
  segmentation. Their multi-term alignment is maintained during later task
  training; this is one vision task, not evidence of text or Redmi utility.
  Reported tests used an RTX A6000, not Redmi; timing/RSS/thermal compatibility
  of V13 on Android is **UNVERIFIED**. This run did not reproduce the paper.
- Source-code license: repository MIT at the pinned commit. Teacher weights in
  Meta's model card https://huggingface.co/facebook/ijepa_vith16_1k are
  CC BY-NC 4.0; any fine-tuned checkpoint and dataset need separate provenance
  and license checks. The repository explicitly says it does not distribute
  pretrained checkpoints or preprocessed data. No upstream code is copied.
- **Reproducibility caution:** at the pinned revision, `train.py` sorts split
  filenames and chooses `splits[2]` for train and `splits[1]` for its variable
  called test, and selects the best checkpoint by `test_loss`:
  https://github.com/Kishor-Bhaumik/JEDI/blob/bf960b50524971420511e5c569593cdbdd1dcf60/train.py#L164
  and https://github.com/Kishor-Bhaumik/JEDI/blob/bf960b50524971420511e5c569593cdbdd1dcf60/train.py#L538 .
  **If** the directory has exactly README's `TEST_SET.npy`, `TRAIN_SET.npy`,
  `VALIDATION_SET.npy` and no other files, that code maps `VALIDATION_SET` to
  train, `TRAIN_SET` to the loader called test, and does not use `TEST_SET`.
  This is a finding about that public code and stated filename layout, not proof
  of how the paper's reported metrics were produced. Avoid deriving final-test
  claims from this script without independent source/data/run verification.
- V13 action: keep A3 alignment-vs-no-alignment ablations separate from a
  source-disjoint train/validation/final-test split. Existing A3 worker uses
  an internal source-hash train/heldout split and can use its heldout metrics
  for eligibility; that heldout is validation-like, not untouched final test.
  The new `a3_source_split_candidate.partition` reserves final test sources;
  `worker_indices` adapts the remainder to the **actual** worker's existing
  split and validates the mapping. A synthetic integration test invokes the
  real worker with synthetic teachers; no model replacement or gate promotion.
  It detects exact repeated slices and full-source groups, not paraphrases or
  overlapping near-duplicates across different sources. Provenance and
  authorization must be revalidated at use; no active runtime hook exists.

## EmbeddingGemma 2 — WAIT FOR MODEL/DEVICE TEST

- Google model card https://ai.google.dev/gemma/docs/embeddinggemma/model_card_2
  and original developer release 2026-10-06
  https://developers.googleblog.com/embeddinggemma-2-the-developer-guide/:
  Apache-2.0, 270M text-only, 740M total with modality encoders, 768-dimensional
  embeddings with supported 512/256/128 truncation. Model/revision, actual
  download format and dependency licenses still require per-artifact checking.
- This could be an A2 teacher for later research, not an automatic substitute.
  Current V13 `student_worker.TEACHER_DIM` is 3072; a 768d model needs an
  explicitly versioned adapter/objective and new heldouts. 128/256/512/768
  vector storage changes do not establish model RAM savings or equal quality.
  A historical 5.84GB total / ~1.78GB available was only a past phone reading.
- Proposed source-disjoint EN/DE heldout experiment after obtaining authorized
  model bytes and runnable backend: compare A3 teacher alignment, baseline,
  nearest-neighbour and truncation with identical inputs, then separately
  measure Redmi RSS, latency, I/O, heat and battery. No device claims yet.
