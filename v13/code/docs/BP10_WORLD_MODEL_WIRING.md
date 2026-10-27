# WP-BP10: Weltmodell ins laufende System (Stand 2026-10-27)

Quellen (nur Konzept, gelesen 2026-10-27): D-JEPA, Liu et al., arXiv 2609.24749 (FS1); AEWM „task-state contamination“ (FS10), beides in `research/FORSCHUNG_2026-10-27.md`.

## Wer verbraucht die Ausgabe des Weltmodells? (Blueprint-Prüfung vor dem Bau)

| Weltmodell | Ausgabe | Verbraucher heute | Befund |
|---|---|---|---|
| T8 `world_model.py` (Routen, Zählmodell) | Gegenfall-Vertrauen je Route | Sleep B Hypothesen (`sleep.py`, Etikett `SIMULATION_UNCERTAIN`), `authority.fit` | verdrahtet, Verbraucher schreibt nur Hypothesen mit Fakt-Autorität 0 |
| Z12c `world_jepa_slots.py` (Datei-Plätze) | Vorhersage-Latent, Vertrauen, Zuordnung eigen/fremd | **keiner in der Laufzeit.** Zuordnung läuft über den Z12a-Hash. GPT baut parallel die dauerhafte SHADOW-Ablage mit Kalibrierung (Branches `codex/z12c-world-jepa-persistent-shadow-*`, `codex/review-z12c-calibration-required-*`) | Anschluss in die Laufzeit gehört dorthin; hier nicht doppelt gebaut |
| Kandidaten-Zukünfte einordnen (FS1) | Rangfolge zwischen Kandidaten | Verbraucher wäre die Werkzeug-/Aktionswahl (C5/`toolstep`), die heute den Kandidaten nach Regeln wählt | erst messen, ob die Rangfolge gegenüber „nächster vorhergesagter Zustand“ überhaupt Raum hat (unten) |
| Veraltete Hypothesen (FS10) | Markierung offener Notizen | `executive.report_context` → Prompt-Schicht `LATENT_STATE` (Z5c: alte ungelöste Hypothesen schaden in langen Sitzungen) | Verbraucher vorhanden, gebaut |

## FS10 gebaut: `v13/hypothesis_stale.py`
Offene Notizen des Executive werden als veraltet markiert bei TOPIC_SHIFT (aktuelle Anfrage teilt fast keine Begriffe), ANSWERED_LATER (spätere Wiederholung mit FINAL-Antwort), CORRECTED_SINCE (Korrektur zum Thema danach gespeichert), TOO_OLD (> 6 Nutzer-Turns), SOURCE_GONE. Schalter `hypothesis_stale` off | **shadow** (Standard: nur zählen und protokollieren) | active (veraltete Notizen werden dem Modell nicht mehr als aktuell angeboten). Löscht nichts, schreibt keinen Fakt. Tests `tests/test_hypothesis_stale.py` (6). **Nutzen nicht gemessen:** dafür braucht es Modell-Läufe im Z5c-Aufbau (lange Sitzung, Stale-Markierung aus/an); Vorab-Regel dort: `active` darf die Trefferquote nicht senken und soll die Z5c-Schäden der Hypothesen-Schicht (19:41) verkleinern. Offen, Cloud mit Modell.

## FS1 vorab registriert (vor dem ersten Lauf): Rangfolge der Kandidaten-Zukünfte
Frage (D-JEPA): Ist „der Kandidat, dessen vorhergesagter Zustand dem Ziel am nächsten liegt“ schon eine gute Wahl, oder gewinnt man mit einer aus **ausgeführten** Ergebnissen gelernten Rangfolge? Aufbau `scripts/bp10_fs1_rank.py` auf dem Z12c-Aufbau (Modell und Datei-Welt von GPTs Branch `codex/review-z12c-calibration-required-20261027` @ 293ccf7d, unverändert übernommen: `world_jepa.py`, `world_jepa_slots.py`, `z12b/z12c`-Skripte und Tests). Pro Zustand 6 Kandidaten, jeweils **echt** in einer Kopie ausgeführt; Ziel = Klassenmuster (leer / Ordner / Ziffern / kurz / lang je Platz) eines erreichbaren Zielzustands; Güte eines Kandidaten = Zahl der Plätze, deren echte Klasse nach der Aktion zum Ziel passt.
Maß `skill` = (gewählt − Zufall) / (Orakel − Zufall) auf der mittleren Güte.
**Vor-Prüfung (Regel „Gewinn sichtbar?“, `--probe`):** Misst nur „Distanz“ gegen Zufall und Orakel. Ist skill(Distanz) ≥ 0,8, gibt es keinen Raum (`NO_ROOM`), der Ranker wird nicht gebaut/bewertet.
**Kriterien (wenn Raum), 3 Seeds 221–223, Mittel:** (1) skill(Ranker) ≥ skill(Distanz) + 0,10; (2) skill(Ranker) ≥ 0,6; (3) Kontrolle mit vertauschten Ergebnis-Etiketten: skill ≤ 0,15. Ranker: linear, paarweise logistisch, je Ziel-Klasse ein Gewichtsvektor auf dem vorhergesagten Platz-Latent, trainiert auf getrennten 900 Zuständen. Urteil `BP10_FS1_PASS` nur bei allen drei. Grenze: Datei-Welt mit Plätzen, Klassenziele; sagt nichts über die Werkzeugwahl im echten System.
