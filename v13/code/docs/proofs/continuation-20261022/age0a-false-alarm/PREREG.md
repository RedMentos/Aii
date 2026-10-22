# WP-AGE0c Vorregistrierung: Wie oft schlägt die späte Selbstkorrektur falsch an?

Stand 2026-10-22, vor jeder Auswertung committet. Gegenstand: `SelfSystem.late_offer` aus WP-AGE0a (`v13/selfmodel.py`),
heute Standard `shadow`. Frage: Darf `:self correction deliver` empfohlen werden?

## Was der Erkenner tut (Code-Stand 3403403)
Er bekommt ein Körper-Angebot (B1/B2: `summary`, `needs_reentry`) und die schon gegebene Antwort. Er meldet
„Möglicher Fehler“, wenn (a) `needs_reentry` gesetzt ist **oder** (b) die `summary` Zahlen enthält, die in der Antwort
fehlen. Wichtig: der Körper sieht die Antwort nie (Angebot entsteht aus der Nutzernachricht, live wie hier).

## Daten (nur vorhandene, echte Modellangebote, nichts neu erzeugt)
- **A STEP2:** alle Zeilen mit Angeboten aus `bench-results/step2-two-body-20261009/step2_utility.json`,
  `bench-results/kalibrierung2-20261009/step2-c3-{350m,230m}.json`, `docs/proofs/continuation-20261011/step2-webchat-70/report.json`
  (der `report-snapshot.json` ist ein Duplikat und wird ausgelassen). Je Zeile: echte C3-Antwort (`raw_answer`),
  echte Körperangebote, Aufgabe mit Lösung (`fixtures[].oracle`).
- **B Kalibrierung:** `bench-results/kalibrierung-20261009/{offers,offers_solve}.json`,
  `bench-results/kalibrierung2-20261009/{offers,offers_hypothesis}.json`; je Aufgabe B1- und B2-Angebot und Lösung (`gold`).
- Gleiche (Angebot, Antwort)-Paare zählen einmal (Dedup über Inhalt).

## Arme
- **A-richtig:** Antwort = die Lösung als JSON (`oracle`, genau das Format, das C3 liefern soll). Jeder Alarm ist ein Fehlalarm.
- **A-echt:** Antwort = echte C3-Antwort. In allen Zeilen ist sie falsch (0 exakt, bekannt aus STEP2). Hier wird gemessen,
  ob ein Alarm den **richtigen Grund** nennt.
- **B-knapp:** Antwort = nur die Lösung (`gold`), z. B. „10“. Jeder Alarm ist ein Fehlalarm.
- **B-mit-Echo:** Antwort = Aufgabentext + „ Answer: “ + Lösung (eine richtige Antwort, die die Frage wiederholt). Jeder Alarm
  ist ein Fehlalarm. Die echte Fehlalarmrate richtiger Antworten liegt zwischen B-knapp und B-mit-Echo.

## Messung
Primär wird der **echte Code** aufgerufen (`late_offer` im Modus shadow, frische Runtime, Rückgabe ≠ None = Alarm).
Varianten (nur hier im Messskript, kein Live-Code geändert) mit derselben Zahlenregel:
- **V0** = heutiger Erkenner (muss mit dem echten Code in jedem Paar übereinstimmen, sonst Messung ungültig).
- **V1** = nur fehlende Zahlen, `needs_reentry` allein löst nichts aus.
- **V2** = wie V1, aber Zahlen, die schon in der Nutzernachricht/Quelle stehen, zählen nicht („Echo-Filter“).
  Offenlegung: Die Idee zu V2 kam beim Ansehen der Datenstruktur an einem einzigen Beispiel (B2-Angebot wiederholt „3 + 7“).
  Ergebnisse wurden vor diesem Commit nicht berechnet.

Größen je Arm und Variante: Alarme / Paare, Wilson-95-%-Intervall, getrennt nach Rolle (B1/B2) und Auslöser.
In A-echt zusätzlich **Grundtreffer**: ein Alarm ist begründet, wenn mindestens eine genannte fehlende Zahl eine Lösungszahl
ist, die in der Antwort fehlt. Ein Alarm nur aus `needs_reentry` nennt keinen prüfbaren Grund und zählt als unbegründet.
**Trennschärfe:** gepaart in A (gleiches Angebot, einmal richtige, einmal echte falsche Antwort): Alarmrate falsch minus
Alarmrate richtig.

## Kriterium (fest, vor dem Lauf)
Eine Variante ist **lieferbar**, wenn alle drei gelten:
- **K1 Fehlalarm:** in A-richtig, B-knapp und B-mit-Echo jeweils Rate ≤ 10 % **und** obere Wilson-Grenze ≤ 15 %.
- **K2 Grund:** in A-echt sind ≥ 50 % der Alarme begründet.
- **K3 Trennschärfe:** gepaarte Differenz in A ≥ 20 Prozentpunkte.

Urteil für den heutigen Erkenner (V0): K1–K3 erfüllt → `AGE0C_DELIVER_OK`; sonst `AGE0C_STAY_SHADOW` mit Angabe, welches K
fehlt. V1/V2 erfüllt → `AGE0C_VARIANT_<V>_CANDIDATE` (nur Kandidat: Daten sind dieselben, ein Einschalten braucht einen
Nachweis auf neuen Daten, z. B. Redmi-Schattenring). Egal wie es ausgeht: Standard bleibt `shadow`, nichts wird eingeschaltet,
die Entscheidung über `deliver` bleibt beim Nutzer. FAIL bleibt FAIL.

## Grenzen
Aufgaben sind eng (Budget-Rechnungen, kleine Rätsel), englisch, kein freier Chat. Angebote kamen vor der Antwort
(Live: Angebote nach der Antwort, gleiche Eingabe, ggf. mit Peer-Nachricht). Echte C3-Antworten sind alle falsch, daher
misst A-echt nur Begründung, nicht Fehlalarm. Sprache der Meldung (deutsch) ist nicht Gegenstand.
