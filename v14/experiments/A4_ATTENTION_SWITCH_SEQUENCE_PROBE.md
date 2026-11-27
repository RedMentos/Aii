# A4 attention-switch sequence probe

**Status:** runnable research/verification tool; not a production attention policy or a learned AAD decoder.

## Purpose

Consumes the existing **A4AttentionReceipt** emitted by
**audio_voice_cues.consume_pcm16_voice_window** plus a separately sourced later
attention-state outcome. It tests whether *causal* A4 score sequences rank a
future state transition above stable windows.

The probe deliberately does **not** infer which speaker is attended. The current
A4 score vector is a global control signal (**A4_CONTROL_SCORE_NOT_AAD**), not a
speaker posterior, calibrated probability or truth claim.

## Input and provenance

Input is UTF-8 JSONL, one record per A4 window:

- **evidence_class:** OBSERVED_LOCAL for evidence; SYNTHETIC_FIXTURE only for
  explicit non-acceptance tests.
- **a4_receipt:** final schema-1.0 A4AttentionReceipt from A4_AUDIO, including
  source_ref, provenance, start_ms, end_ms, brain_generation_id, score_vector,
  and all three authority fields set to false/zero.
- **outcome:** independent later annotation with its own source_ref, the exact
  audio timebase_source_ref, matching brain_generation_id, session_id,
  trial_id, goal_id, state_before, state_after, next_switch_at_ms,
  observed_at_ms, and both action/learning authority false.

label_kind must distinguish:

| label_kind | Interpretation |
|---|---|
| TARGET_CUE | instructed target only; **not** proof of actual attention |
| EEG_DECODER_ESTIMATE | model-estimated attended state; **not** ground truth |
| OBSERVED_ATTENDED_STATE | separately observed/annotated attended state |

The outcome source must be independent of the audio source. Its
timebase_source_ref must exactly match the audio SourceRef, so labels cannot
silently drift onto another clock or recording. A4 windows must be FINAL.
Raw PCM, waveform, samples, transcript and ASR text are rejected.

A stable/no-switch label is accepted only when observation covers the entire
configured future horizon. Shorter observation is censored, not silently counted
as a negative.

## Metrics

The probe reports:

- per-feature AUC for current A4 scores and causal history/delta features;
- macro averages stratified by session × goal;
- label permutations confined to session × trial × goal × generation;
- constant-zero AUC control (0.5) and shuffled-label null distribution;
- the current A4 interrupt operating point (precision, recall, false-positive rate);
- lead time from the A4 window end to the later state transition.

The output states the label scope and evidence class. It performs no training,
weight update, persistent write, policy change, or external action.

## Run

For a real local dataset, use evidence_class=OBSERVED_LOCAL:

~~~bash
python v14/experiments/a4_attention_switch_sequence_probe.py \
  --input /path/to/a4_outcomes.jsonl \
  --horizon-ms 5000 \
  --history-ms 5000 \
  --permutations 1000
~~~

Synthetic fixtures require an explicit --allow-synthetic and can never satisfy
an acceptance gate:

~~~bash
python v14/experiments/a4_attention_switch_sequence_probe.py \
  --input /path/to/fixture.jsonl --allow-synthetic
~~~

## Research basis and limits

Carta et al., *Competing speech streams are simultaneously represented in the
human cortex during attention switching*, PLoS Biology 24(7), e3003876
(2026-07-16), DOI 10.1371/journal.pbio.3003876, is peer-reviewed and CC BY 4.0.
The study used 24 normal-hearing adults, 20 three-minute trials per participant,
six instructed switches per trial at randomized 10–30 second intervals, two
foreground speech streams plus 16-talker babble, and 64-channel EEG at 512 Hz.
TRF-based decoding was above chance even with a 1-second window. The new stream's
neural tracking began before the old stream fully disengaged, producing a
transient overlap. The paper explicitly notes that transition latencies depend
on the sliding-window length and are not absolute neural timings.

The data and analysis files are on Zenodo record 20569817; the full archive is
large (about 12.4 GB; source-data bundle about 634.7 kB). This run did not
download or process that dataset. The study motivates separate transition and
overlap measurements, but it does not validate this A4 probe or imply that A4
scores decode attended-speaker identity.

Next empirical step: map an independently sourced target-cue or EEG-decoder
timeline to real A4 receipts, preserve the label-kind distinction, and run
session-held-out observed-data evaluation. Until then, all probe results from
the included fixture remain SYNTHETIC_FIXTURE.
