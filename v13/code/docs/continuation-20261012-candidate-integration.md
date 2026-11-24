# Kandidaten-Integration nach SourceHandoff-Freeze — 2026-10-12 (Claude, Thread G)

Voraussetzung: 16-Fall-SourceHandoff-Kohorte abgeschlossen (RECORDED_DIAGNOSIS 16/16), Freeze aufgehoben.

## Übernommen
- **Approval-Reader + Native-Firing-Audit** in `v13/runners.py`, `memory_server.py`, `runtime.py`, `store.py`. Live-Dateien aus `scripts/native_firing_candidate_smoke.merged_sources()` geschrieben; der Diff ist bytegleich mit `docs/proofs/continuation-20261011/approval-reader-cancellation-20261012/approval-reader-and-firing-updated.patch` (inkl. 50-ms-Cancellation beim Store-Mutex). Firing bleibt opt-in/SHADOW, keine selektive Auslassung.
- **Streaming-Packager** als `scripts/package_source.py` (Dateiauswahl auf aktuellem Baum 908/908 voll, 527/527 Phone gleich). Verhalten neu: kein Überschreiben eines vorhandenen ZIPs, kein `WORKSPACE_FILES.json` mehr im Quellbaum (nur im ZIP).
- **Sealed-Storage-Streaming** als `scripts/sealed_storage_parts.py` (gleiches v1-Format; beide veröffentlichten Teilsätze stellen alt und neu bytegleich wieder her, Neu-Split ergibt identische Manifeste).

## Nicht übernommen
- Atomic-Publish für Action-JEPA-Restore: braucht zuerst die Handy-Probe `python scripts/action_jepa_delta_atomic_publish_candidate.py --probe-directory "$HOME/v13"` (renameat2 auf dem Redmi-Dateisystem).
- Source-Handoff-Kandidat: in der Ablation kein Vorteil (0,5208 vs Baseline 0,5625).

## Kandidaten-Tests
`scripts/integrated_candidates.py` beschreibt die integrierte Zusammensetzung. Die Lader von Firing- und Source-Handoff-Kandidat akzeptieren den Live-Code nur noch als exakte Baseline, exakten eigenen Kandidaten oder exakt diese Integration; alles andere scheitert weiter geschlossen. Erster Lauf nach reiner Runtime-Übernahme: 54 rote Kandidaten-Tests (Log erhalten), danach grün.

## Prüfung
Volle Suite vorher 1236 OK/4 Skips, nachher 1236 OK/4 Skips. Phone-ZIP mit neuem Packager gebaut (528 Dateien, SHA `report.json`), entpackt, volle Suite 1236 OK/4 Skips. Linux Python 3.13 ohne PyTorch, kein Redmi-Nachweis. Belege `docs/proofs/continuation-20261012/candidate-integration/`.

STEP2 UTILITY_FAIL und B3 L1 FAIL bleiben; `canonical_architecture_complete=false`.
