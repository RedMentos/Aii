# Aktueller Fortsetzungsstand — Codex, 2026-10-11, 23:21 Berlin

Der vorhandene Drive-Plan bleibt verbindlich; neue Zukunftsideen werden getrennt gesammelt. Ziel sind belastbare längere Menschentests und belegter fortgesetzter Lernnutzen, kein vorzeitig behauptetes AGI-/RSI-Ergebnis.

- Autoritative Code-/Test-/Proof-Quelle: GitHub `RedMentos/Aii`, Branch `codex/authority-live-comparisons`, https://github.com/RedMentos/Aii/tree/codex/authority-live-comparisons . Zuletzt verifizierte Basis: `ef46ddbbe2cc2b694ccb0c74275a86a78f0ae2aa`, Tree `0bd3babb9d8f0777f8b772f377829d5e7b3e4c36`. Vor jedem Wechsel tatsächlichen Remote-HEAD neu lesen; diese Notiz ist ein datierter Checkpoint.
- Code liegt im Repo unter `v13/code`; Roadmap `v13/ROADMAP.md`; aktueller Status `v13/code/BUILD_STATE.json`, `docs/completion-ledger.json`, `docs/CONTINUE_20261011_PROGRESS.md`, Proofs `docs/proofs/continuation-20261011/`. Drive-Roadmap-Originale, Canon und frühere Fehlschläge erhalten.
- Aktuell gesicherter Source-ZIP Version4, Phone-ZIP Version2. Phone-ZIP SHA `477593e79a6069210258d91500ca9a42b0dfeaadf696d9788b09c3a63679a88a`: tatsächlich entpackt1125 Tests PASS,0Skips,495 Datei-Hashes unverändert. Ausschließlich Linux-Softwaretest; Redmi-RAM/Thermals/Laufzeit nicht gemessen. Eine fehlerhafte RSS-Probe wurde verworfen und separat korrigiert.
- Workspace-Bereinigung entfernte zweimal lokale Caches/ungesicherte Resultate. Original736 native Tap-Zeilen/46Rohbatches sind als geschlossenes ZIP dauerhaft gesichert. Die erste vollständige1875-Erfassung hat dauerhaft erhaltene terminale11Worker-Belege, ihre großen Rohbytes wurden vor erfolgreichem Upload entfernt. Metadaten-Dataset wurde aus bereits angelegten Git-Blobs gerettet; dadurch fehlen weiterhin die nativen Zustände. Nicht aus Metadaten als vollständig rekonstruierte Rohdaten ausgeben.
- Native3Modelle+Launcher+19Bibliothekseinträge jetzt wieder bytegleich;121Source-Handoff-Quellen eingefroren. Neue Night-Capture-Preregistrierung `f348d9ca38c728c8b7a5074b25ce1a74aac7fd924e15da9406c3912146590c80` ändert nur Wiederherstellungsordner, keine numerischen Einstellungen oder Gates. Erst nach Git-VerifikationInference starten. Neue geschlossene Belege in<=1MiB Teile mit Teil-/Gesamt-SHA sichern; `scripts/sealed_storage_parts.py` rekonstruiert exakte Originalbytes.
- Nächste Reihenfolge: begrenzte tatsächliche Capture mit zwei frischen Invarianzkontrollen und kontrollierten8BatchWorker-Grenzen, vollständige1875Rohdaten plus originale3NumPySeeds13/21/34; danach unveränderte16FallSource-Handoff-Ablation; danach Dream2 exakt40BSteps×3Seeds×5Arme (2/15dauerhaft abgeschlossen; unvollständigerB10Arm vonBase neu). Alle schweren Modelljobs seriell unter8GiBLinux-Cgroup. Danach isolierteAG6Reader/FiringFixes integrieren und Paket erneut testen, dann weitereOriginal-Gates.
- Original STEP2:70/70UTILITY_FAIL, kein neuer Nutzen-PASS. B3L1:alle8TasksFAIL, L2–L4gesperrt. Gist nativeReadoutConsumer fehlt, aktuelletextbasierte Gruppierung ist kein gelerntesGist-Ziel. NativeFiringdiagnostik bleibtSHADOW,keineSelective-Auslassung. `canonical_architecture_complete=false`, `user_full_scope_complete=false`, aktuellerHandyqualitätsnachweisoffen.
- Bei parallelem Codex/Claude-Wechsel: erst Remote-HEAD und diese Drive-Datei neu lesen; geschlossene Belege/Gates weiterführen; eigene Branches oder Hash-CAS für Schreibzugriffe. Keine Force-Pushes und keine Änderungen an aktiven gefrorenen Quellen. Kein direkter Claude-Kanal ist hier verfügbar; GitHub/Drive sind die gemeinsame Übergabe.

## Historische ursprüngliche Drive-Übergabe (unverändert erhalten)

# V13 / Inquisition-JEPA – Übergabe für eine andere KI (Stand 2026-10-11)

Projekt: brain-inspirierte, kontinuierlich lernende KI-Runtime für ein Redmi-Handy (Android/Termux, 6 GB RAM). Nutzer schreibt Deutsch, arbeitet nur am Handy. Leitfrage des Projekts: braucht AGI mindestens 8 GB RAM; Zwischenergebnisse für Tests und exakte Werte sind erlaubt.

## Wo was liegt (Drive-Ordner https://drive.google.com/drive/folders/1dEAaqlWvdsU8hciVBNfVVPV1f5CjucZv)
- ROADMAP_Teil1von3.md, Teil2von3.md, Teil3von3.md: alle Arbeitspakete mit Status (zusammen die komplette ROADMAP.md)
- SICHTUNG.md: Sichtung der ganzen Übergabe, Widersprüche, verlorener Code
- NUTZER_ENTSCHEIDUNGEN.md: verbindliche Nutzerentscheidungen
- Code, Tests und Bench-Ergebnisse liegen NICHT als Text auf Drive. Sie stecken in ZIPs im Claude-Projekt (V13_2_Code.zip ca. 1,7 MB, V13_1_Doku.zip, V13_3_Bench.zip, V13_4_Archiv_ohne_Chat.zip, V13_5_Proofs.zip). Wer sie braucht, bittet den Nutzer, die ZIPs hierher in den Ordner hochzuladen.

## Kernpunkte
- Code in `code/v13/` (ca. 104 Module), Tests `code/tests/` (zuletzt ca. 940 grün, `test_bodies.TightBudget` sporadisch flaky), Befehl: `cd code && PYTHONPATH=.:tests python -m unittest`.
- Nutzerentscheidungen: viele verschiedene Modelle (B1 und B2 echt verschieden), Englisch zuerst, konstantes Lernen als Endziel, Ziel ist eine heruntergebrochene Gehirn-Simulation. Age-Hülle startet bei 0.
- Fertig laut ROADMAP: WP-A bis E, WP-V1 bis V9, WP-N1 bis N14, WP-T1 bis T16, WP-U1 bis U10, WP-AG (AG0 bis AG13), Abdeckung ca. 56 %.
- Offen: B3 LATENT unavailable (L1-Gate FAIL), STEP2 two-body FAIL, viele SHADOW-Flags brauchen Redmi-Messung (WP-R, nur der Nutzer), WP-T17 Dream-Lauf 2 (`--b-steps 40 --seeds 13,21,34`).
- Arbeitsregel: jedes Paket aktualisiert ROADMAP.md und schreibt eine Übergabenotiz; Status-Zeile „in Arbeit“ vor Beginn setzen.
- Nutzer-Pause bis Montag 2026-10-12 04:00 Berlin war angesetzt; der Nutzer lässt jetzt eine andere KI bis Montag weiterarbeiten.
