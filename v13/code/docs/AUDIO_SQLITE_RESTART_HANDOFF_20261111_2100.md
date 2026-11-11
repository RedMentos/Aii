# Perception handoff — 2026-11-11 21:00 Europe/Berlin

Owner: research-perception. Parent: research-perception/audio-store-runtime-20261111-2000 (PR #1795).

## Implemented
Added `tests/test_audio_sqlite_restart.py`: unlike the prior fake Store.one fixture, this uses **real V13 Store**, creates actual session/EventEnvelope/A0 descriptor and A5 PerceptPacket, closes and reopens SQLite, replays the stored acoustic evidence into B1/B2/JEF SHADOW views, checks null unmeasured voice evidence and revokes the original A0 source to ensure subsequent replay fails. Second test checks provisional RAW EAR never reaches the real packets table.

## Verification
Code persisted on GitHub. **Test execution NOT verified**; no native Android benchmark, no permissioned microphone and no live B/C model call. Execute from repository checkout:
```
cd v13/code
python -m unittest tests.test_audio_sqlite_restart tests.test_audio_store_bridge tests.test_audio_e2e_smoke -v
```
The real Store uses `fcntl`, SQLite WAL and expected home subdirectories. This test is Linux/Termux-oriented; CI host success is not Redmi hardware proof. On failure, fix Store setup/contract compatibility before promotion.

## Integration and gates
Core: wire replay result into real read-only B/C observation path; keep independent Android OS permission boundary. JEPA: null evidence is masked, SHADOW replay not learning approval. QA: run full regression and actual Redmi Termux validation. A3 projector, audio teacher, Android mic, full-duplex and trainable speech effector remain OFF/UNAVAILABLE. No authority or weight gate promoted.
