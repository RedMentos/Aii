# WP-T4 A-Plane Lehrer/Schüler (A1–A3, §18.1–18.4, §18.11, G9B, G10) — Übergabe

Code `v13/aplane.py`, Haken in `learning.py` (`student_route` getrennt von `compare_student_route`), `runtime._route` und `operator.py`. Tests `tests/test_aplane.py` (5). Befehl `:aplane [status|student shadow|fallback|distill [Fähigkeit]]`.

## A3-Schüler über Schatten-T1 hinaus
- `StudentEvaluation`-Pakete (Schüler-Route gegen Lehrer-Route) bilden ein Fenster aus bis zu 400 Vergleichen. `:aplane` zeigt die Übereinstimmungskurve in Blöcken zu 25.
- Gate für T2:
  - mindestens 50 Vergleiche
  - mindestens 90 % Übereinstimmung
  - Retention: Die neuesten 25 liegen höchstens 5 Punkte unter den früheren.
- T2 `fallback` schaltet nur der Nutzer ein (`:aplane student fallback`). Das Gate kann das ablehnen.
- Wirkung: Nur wenn der Lehrer-Pfad (Needle/C2-Steuerung, freigegebener Route-Kopf) ausfällt und der Schüler im Support liegt, routet der Schüler (`A3_STUDENT_FALLBACK`). Sonst bleibt die bisherige Route.
- Hält das Gate nicht mehr, fällt der Schüler automatisch auf `shadow` zurück.

## Text-Destillation (kleiner Kopf, nicht LoRA)
- Datengrundlage ist `agi/teacher.dataset`, also die Lehrer-Spuren mit Holdout-Wächter.
- Ein Ridge-Kopf bildet Prompt-Merkmale auf Antwort-Merkmale ab. Beide nutzen die A3-Rohbyte-n-Gramme, ein Modell ist nicht nötig. Die Ziele sind zentriert: Die gemeinsame Antwortschablone ist der Mittelwert, und der Kopf muss vorhersagen, was sich unterscheidet.
- Der Holdout wird über den Hash der Spur-ID gewählt (etwa ein Viertel der Spuren).
- Kennzahlen:
  - zentrierte Kosinus-Ähnlichkeit (die Mittelwert-Baseline liegt bei 0)
  - Treffer der nächsten Antwort (retrieval@1)
  - Solo-Erfolg: Kosinus ≥ 0,3 und richtige nächste Antwort
- Der Kopf schreibt nie Ausgabe (`EVIDENCE_ONLY_NO_OUTPUT`). Seine Solo-Ergebnisse gehen als `teacher.trial(..., teacher_present=False)` in die Internalisierungsschleife (L5.5).
- Läuft nur außerhalb von RECORD_ONLY. Artefakt: `checkpoints/distill-*.npz`.

## Lehrer-Entfernung als Lauf
- Derselbe Holdout wird mit 100, 75, 50 und 25 % der Lehrer-Spuren trainiert. Das ergibt die Reliance-Kurve (Solo-Erfolg und Reliance je Anteil).
- Fixture mit 30 Hauptstadt-Spuren: Solo-Erfolg 0,6 → 0,3 → 0,2 → 0,0, retrieval@1 0,8 bei einer Zufallsrate von 0,1.
- Den Lehrer wirklich zu entfernen (`teacher.remove`) bleibt eine Entscheidung des Nutzers und braucht `removal_ready`.

## Grenzen und Offen
- Die Rohbyte-Merkmale sind lexikalisch, nicht semantisch. Mit Needle-/EmbeddingGemma-Embeddings wäre der Kopf aussagekräftiger. Das ist eine spätere Option, kein heutiger Befund.
- A1 gelernte Segmentgrenzen: Der inhaltliche Teil ist erledigt (WP-N8 `text_segments`). Ein gelernter Grenz-Kopf ist offen, weil es dafür noch keine Labels gibt (keine Grenz-Korrekturen vom Nutzer). Gelernt wäre er aus Attention-`source_outcome`, sobald genug Spans bewertet sind.
- Echte Lehrer-Spuren entstehen erst mit einem registrierten Backend (`:growth teacher run local|claude`; Cloud nur mit Erlaubnis des Nutzers).
