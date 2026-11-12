# Perception RAW EAR PCM feature extractor – 2026-11-12 07:55 CET

Owner: research/perception. Parent: PR #1827, stacked; do not merge independently.

## New executable slice
- `v13/code/v13/raw_ear_pcm.py`: mono signed PCM16LE frames, RMS, peak, zero-crossing rate, relative timestamps. Explicit 60s bound, full-frame validation, no microphone or transcript.
- `v13/code/tests/test_raw_ear_pcm.py`: four deterministic synthetic tests.
- Equivalent isolated local source was executed using `python -m unittest -v test_raw_ear_pcm`: 4 tests PASS on Linux Python; exact GitHub head, full repo suite and native Android remain UNVERIFIED.
- Repo test command: `PYTHONPATH=v13/code python -m unittest -v tests.test_raw_ear_pcm` may depend on test package layout; preferred `PYTHONPATH=v13/code python -m pytest -q v13/code/tests/test_raw_ear_pcm.py`.

## Limitations and next integration
- This module does not yet feed the canonical A5 PerceptPacket or the A3 timed-source bridge. Next step: persist PCM-derived measurements in authorized Store source, bind capture timestamps/provenance externally, and route to A3/A5 without treating heuristic zero crossings as ASR or speech confidence.
- No Android mic permission, live recording, speaker identity, full-duplex, C7 speech effector, quantization or B/C model inference evidence. GATES unchanged.
- Android Redmi RAM (~5.84GB total, historically ~1.78GB available) is historical only, no measurement.
- Source/license: original stdlib-only Python implementation, no external model, data or dependency license.
- This is host-only nonsemantic feature processing, not a full perception pipeline or an AGI claim.
