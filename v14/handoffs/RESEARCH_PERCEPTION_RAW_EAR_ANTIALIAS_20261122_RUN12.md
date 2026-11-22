# Research/Perception handoff — RAW EAR anti-alias decimation

Date: 2026-11-22  
Branch: `research-perception/v14-raw-ear-antialias-20261122-run12`  
Base: `c03ff0aa9e18b5ffebd1109f3c078105f53c6afe` (current release-development HEAD at run start)

## Concrete defect and change

The existing RAW EAR feature path used block-average reduction before pitch/voicing estimation. That boxcar is not a sufficient anti-alias filter: high-frequency periodic input can fold into the 65–400 Hz F0 search band and be reported as `VOICED`. A synthetic 44.1-kHz, 8.62-kHz tone was previously interpreted as approximately 200.45 Hz. Similar alias cases exist at 16, 22.05 and 48 kHz.

The branch replaces that reduction with a cached, centered 21-tap Hamming-windowed low-pass FIR followed by integer decimation. Cutoff is 0.45 × the resulting feature sample rate. Symmetric centered filtering avoids a timestamp shift; edge samples are replicated to preserve bounded window geometry. It uses only the Python standard library.

**Scope limit:** this is a low-cost RAW EAR pitch/voicing feature decimator only. It is not a calibrated VAD, not a speaker-embedding resampler, not a playback-quality resampler and not a learned model. The separate FASTDIAR 44.1→16-kHz feature-view question remains open.

## Changed paths and commits

- `v13/code/v13/audio_voice_cues.py` — cached FIR coefficients and anti-alias decimator are now used by the existing `extract_voice_cues()` consumer.
- `v13/code/tests/test_audio_speaker_evidence.py` — adds four sample-rate alias negatives, four low-F0 preservation positives and a real synthetic A5→A4→C3 Runtime-consumer regression.
- No shared Boss-owned board/workplan/coverage/next-action file or historical Canon bytes were edited.

## Exact evidence

### LOCAL_LINUX

Environment: CPython 3.13.5, x86_64 Linux, isolated algorithm reproduction (the full Aii checkout is not mounted).

- `python3 -m py_compile /tmp/raw_ear_antialias_check.py` — PASS.
- `python3 /tmp/raw_ear_antialias_check.py` — PASS, 4/4:
  - high-frequency alias rejection at 16,000 / 22,050 / 44,100 / 48,000 Hz;
  - 140-Hz positive control preserved at all four rates;
  - old block-average negative control reproduces false `VOICED` at 44.1 kHz / 8.62 kHz;
  - one-second 44.1-kHz algorithm budget stays below 0.75 s on this host.
- Nine-run median prototype benchmark at 44.1 kHz:
  - 140-Hz voiced tone: 0.1683 s FIR vs 0.1522 s boxcar (+10.6%);
  - 8.62-kHz alias case: 0.0209 s FIR vs 0.1489 s boxcar (-86.0%), because the false pitch path is no longer run.
- These are isolated prototype timings, not a full repository test, native model timing or Redmi measurement.

### CI

The changed paths trigger `.github/workflows/v14-raw-ear-fastpath.yml`: Python 3.13 and 3.14, compile, RAW EAR speaker/A5-A4-C3 tests, input tests, deterministic benchmark and public-content privacy scan. Exact-head CI is pending until GitHub Actions reports it; no PASS is claimed yet.

### DEVICE / RELEASE

- Full local Aii repository tests: BLOCKED (no checkout available in this execution environment).
- Termux/Redmi: REDMI_UNVERIFIED; no connected handset or microphone capture was used.
- No AudioRecord permission/provider, model, weight, dependency, Age, learning authority, updater, user data or device setting was changed.
- NOT_RELEASED. GitHub push/PR is not deployment.

## Canon mapping

A0/A5 timed RAW EAR acoustic input → A4 voice/temporal attention → C3 bounded percept admission; supports the open STEP9/G10C/G10D voice/audio scope. The regression is specifically about preventing out-of-band tones from being mislabeled as voiced input. It does not complete Android microphone input, ASR, speaker identity, full duplex, trainable speech output or cross-organ latent learning.

## Research note for shared ledger

SciPy's official `signal.decimate` reference explicitly defines downsampling after anti-alias filtering and documents a Hamming-window FIR option and zero-phase filtering: https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.decimate.html . The implementation here uses a smaller 21-tap standard-library filter to avoid adding SciPy/NumPy to the Android path. This is an engineering adaptation, not a claim of SciPy numerical parity.

## Next action

Wait for exact-head `v14-raw-ear-fastpath` CI on this branch. If green, request Boss review and merge only onto the current release-development head. Keep microphone capture OFF until the companion's permission, route/silence, cancellation, zeroization and revocation contracts pass. Only then collect consented Redmi latency/RSS and acoustic fixtures.


## Follow-up — comparator integration correction (2026-11-22)

The first push-triggered RAW EAR VAD comparison run (Python 3.13 and 3.14) exposed an existing AST-isolation consumer that selected `extract_voice_cues` but did not include its newly required FIR helper or `lru_cache` dependency. This was a real downstream consumer failure, not a filter numerical failure.

Fixed on this branch:
- `v14/experiments/raw_ear_vad_compare.py` now includes `_voice_decimator_coefficients` and `_anti_alias_decimate` in the isolated AST selection and supplies `lru_cache` in its namespace.
- `.github/workflows/v14-raw-ear-vad-comparison.yml` now pins the exact new `audio_voice_cues.py` Git blob `34dfd39728161b4659afc21298476cd732d08792` rather than the pre-change blob.

Additional LOCAL_LINUX CPython 3.13.5 check: isolated AST-loader smoke PASS; the helper and cache dependency resolve when the comparator loads the producer in isolation.

Initial push evidence at code commit `44aadc4`: RAW EAR fastpath Python 3.13/3.14 PASS (run `45001440422`), prosody/attention Python 3.11/3.13 PASS (run `45001440362`), pre-lease revocation QA PASS (run `45001440342`), privacy scan PASS (run `45001440401`); VAD comparison failed in both Python versions because of the AST dependency omission (run `45001440340`). The omission and source pin were corrected in subsequent commits. Exact PR-head reruns on the updated branch were queued at last read: fastpath `45001598137`, comparator `45001695523`, prosody `45001695396`, pre-lease QA `45001695463`, staged/integrated `45001695356`, privacy `45001695367`, model-lab `45001695513`. Do not inherit the earlier push PASS as exact PR-head acceptance; wait for these updated-head results.
