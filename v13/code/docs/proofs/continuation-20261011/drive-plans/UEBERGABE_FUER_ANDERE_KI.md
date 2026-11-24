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
