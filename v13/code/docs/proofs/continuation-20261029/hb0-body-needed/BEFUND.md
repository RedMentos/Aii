# WP-HB0 Befund: Aufgaben mit Platz für die Körper (2026-10-29)

Ergebnis nach der vorab festgelegten Regel: **`HB0_BODY_ROOM` erreicht.** Der Aufgabensatz ist geeignet, die Körper brauchen ihn.
Ein einfacher Text-Pipeline-Weg nutzt diesen Spielraum aber **nicht** (`pipe`).

Daten: `v13/code/bench-results/hb0-body-needed-20261029/` (`tasks.json`, `rows.json`), Skript `scripts/hb0_body_needed_tasks.py`, Vorregistrierung `PREREG.md` (vor dem gewerteten Lauf im Git, ein Commit davor).
Modelle roh über llama.cpp (b10964): C3 = LFM2.5-350M, B1 = LFM2.5-1.2B, B2 = Qwen3.5-0.8B, alle Q4_0, Temperatur 0, keine V13-Laufzeit.

## Zahlen (152 Aufgaben, vier Familien je 38)

| Arm | richtig von 152 | D Aufzählung | S Änderungskette | G Vergleich | C Korrektur |
|---|---|---|---|---|---|
| C3 sieht Textanfang (`c3_head`) | 0 | 0 | 0 | 0 | 0 |
| C3 sieht Textende (`c3_tail`) | 7 | 0 | 7 | 0 | 0 |
| C3 mit Wortüberlappungs-Suche (`c3_rag`) | 3 | 2 | 1 | 0 | 0 |
| B1 liest alles allein (`b1_long`) | 5 | 1 | 2 | 1 | 1 |
| B2 liest alles allein (`b2_long`) | 21 | 5 | 8 | 0 | 8 |
| **Orakel C3** mit den Goldsätzen (`or_c3`) | 48 | 8 | 38 | 2 | 0 |
| **Orakel B1** mit den Goldsätzen (`or_b1`) | **109** | 23 | 38 | 10 | 38 |
| Pipeline B1+B2+C3 (`pipe`, nur 24 Aufgaben) | 3 von 24 | 0 von 6 | 3 von 6 | 0 von 6 | 0 von 6 |

Auf denselben 24 Aufgaben: `c3_tail` 0, `c3_rag` 2, `b1_long` 2, `b2_long` 3, `or_c3` 6, `or_b1` 18, `pipe` 3.
Pipeline gegen `c3_tail`: 3 zu 0 gepaart, Vorzeichentest p = 0,25.

## Regel (aus PREREG.md) und Ergebnis

1. C3 ohne Körper höchstens 76 von 152: **erfüllt** (bester Arm `c3_tail` 7).
2. Orakel B1 mindestens 15 mehr als bester C3-Arm: **erfüllt** (109 gegen 7, +102).
3. Lücke in mindestens zwei Familien um mindestens 4: **erfüllt in allen vier** (D +21, S +31, G +10, C +38).
4. Pipeline mindestens 15 über bester C3-Arm mit p < 0,05: **nicht erfüllt** (3 gegen 0 auf 24 Aufgaben).
5. `b1_long` ≥ `pipe`: nein, `b1_long` 5/152 ist schlechter als jeder Weg mit gefundenen Sätzen.

## Was die Zahlen sagen

- **Der Spielraum ist groß.** Gegenüber R4 (Orakel nur +3 von 60) ist das ein anderer Rahmen: Der Unterschied zwischen "findet die richtigen Sätze" und "findet sie nicht" beträgt hier über 100 von 152.
- **Das Nadelöhr ist Auffinden und Auswählen, nicht Rechnen oder Entscheiden.** Gibt man B1 die Goldsätze, löst es 72 Prozent. Muss es dieselben Sätze selbst in 3000 Token finden, sind es 3 Prozent (`b1_long`). Auch die einfache Wort-Suche (`c3_rag` 3 von 152) findet sie nicht, weil die Distraktoren (andere Projekte, gleiche Satzformen) dieselben Wörter haben.
- **Die einfache Pipeline scheitert an der Extraktion.** B1 sollte pro Abschnitt Sätze wörtlich kopieren. Das gibt zu oft "NONE" oder zu wenig (z. B. "The text does not specify ..." in D). Die Lücke zwischen `pipe` (3/24) und `or_b1` (18/24) ist die Menge, die ein besserer Auswahl- und Lesepfad gewinnen kann.
- **C3 kann mit den Goldsätzen nur eine Familie.** `or_c3`: S 38 von 38 (einfache Ersetzungskette), D 8, G 2, C 0. In C scheitert C3 vermutlich auch daran, dass es nur den Tag nennt und den Grund weglässt (Formatproblem der Bewertung, nicht geprüft).
- **B2 allein liest lange Texte besser als B1 allein** (21 gegen 5), vor allem bei Korrekturen (C 8 gegen 1). Das passt zu "B2 = Überblick", ist aber ein kleiner Unterschied, den ich nicht weiter ausdeuten will.

## Folge für die nächsten Schritte

- Für P2 (Empfänger lernt Funde zu verwerten) ist dieser Satz **brauchbar**, aber der erste Engpass ist **die Auswahl der richtigen Sätze**, nicht das Verwerten. Das Gold ist im Erzeuger bekannt, also gibt es ein direktes, billiges Lernziel: ein kleiner Auswähler (Satz-Ranker) mit den Goldsätzen als Label, danach erst der Empfänger. Das ist ein neuer Vorschlag P2a, noch nicht gemessen.
- Vor jedem Training: eine zweite, unabhängige Aufgabengruppe (frische Saat, andere Satzformen) für Auswahl-Training und Test getrennt halten, sonst lernt der Auswähler nur die Satzvorlagen des Erzeugers.
- Parallel entstehen die quellengetrennten Software-Aufgaben aus PR #1047/#1048 (Gegenprüfung). Sie prüfen eine andere Frage (Quellentrennung für STEP2) und ergänzen diesen Befund.

## Grenzen

- Erzeugte englische Texte aus festen Vorlagen. Regex-Bewertung. Rohe Modelle ohne die V13-Laufzeit (kein Wake, keine Stores, keine Offer-Schemas).
- `pipe` ist eine einfache Text-Pipeline und nur auf 24 von 152 Aufgaben gemessen (Abweichung von der Vorregistrierung: auf dem 4-Kern-Rechner dauert eine Aufgabe 160 bis 600 Sekunden). Die Aussage "Pipeline gewinnt nicht" ist deshalb vorläufig.
- Ein erster Lauf des Pipeline-Arms wurde durch einen Neustart der Cloud-Maschine unterbrochen und fortgesetzt (Ergebnisse je Aufgabe zeilenweise gespeichert).
- Der B2-Server war im ersten Versuch abgestürzt und wurde mit kleinerem Fenster (6144) neu gestartet; die Zeilen von `b2_long` sind zusammengefügt.
- Die Orakel sind Obergrenzen eines Wegs, der die richtigen Sätze kennt. Sie sind keine Aussage, dass ein Körper sie so im Betrieb findet.
- Keine Runtime-Änderung, keine Gate-Änderung, kein Training. jepa_weight bleibt 0.
