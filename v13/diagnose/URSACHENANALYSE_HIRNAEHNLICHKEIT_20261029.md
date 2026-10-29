# Warum wirkt V13 noch nicht wie ein Hirn? Ursachenanalyse (2026-10-29)

Anlass: Der Nutzer will keine Vereinfachung, sondern wissen, was am System falsch ist oder fehlt.
Auslöser sind mehrere Messungen, in denen das Zusammenspiel der Teile nicht hilft.

Grundlage: Blueprint v10.16.1 (`blueprint/V13_v10.16.1_WORK_HANDOFF_SINGLE_SOURCE_B3_HARDENED.md`),
`ROADMAP.md`, `ZIELABGLEICH.md` und die Befunde der Pakete Z2 bis Z12, LP2/LP3, BP2a, BP7, BP8, BJ1.
Kein neuer Modelllauf in dieser Analyse. Alle Zahlen stammen aus schon vorhandenen Messungen.
Was Beleg ist und was meine Deutung ist, steht jeweils dabei.

## 0. Kurzfassung

Ein Hirn ist ein System, in dem die Teile **zusammen gewachsen** sind, ständig **Vorhersagen** austauschen und **am Ergebnis** lernen.
V13 ist heute eine **Steuerung um eingefrorene, fremde Modelle**. Sie sprechen nur über kurzen Text miteinander,
und kein Lernsignal sagt ihnen, ob das Zusammenspiel genutzt hat.

Daraus folgen sieben Ursachen. Die ersten drei sind die wichtigsten:

1. **Die Teile wurden nie gemeinsam trainiert.** Die Kopplung ist nachträglich angeklebt (Ursache A).
2. **Der Empfänger kann die Funde nicht verwerten.** Das kleine Modell C3 liest Zahlen, entscheidet aber nicht danach (Ursache B).
3. **Kein Lernsignal am echten Ergebnis.** Gelernt wird an Ersatzzielen, die nicht zur Antwortqualität führen (Ursache C).
4. Neues Wissen im Gewicht überschreibt anderes, und der Schlaf ist noch kein echtes Trainieren (Ursache D).
5. Aufmerksamkeit wird nie unter Platzmangel geprüft, also kann sie keinen Vorteil zeigen (Ursache E).
6. Es gibt keine Rückkopplung durch Vorhersage im Körper, nur Text-Vorwärtsfluss (Ursache F).
7. **Die Messaufgaben sind zu leicht für das Zusammenspiel.** Ein kleines Modell schafft sie allein (Ursache G).

Wichtig und ehrlich: Die **einzelnen Teile funktionieren meist**, wenn man sie allein prüft. Das Zusammenspiel versagt.
Das ist das typische Zeichen für fehlende gemeinsame Anpassung, und es passt zu den Messungen.

## 1. Das Muster in den Messungen

| Messung | Zahl | Was sie zeigt |
|---|---|---|
| Z6e Wake (60 Aufgaben) | C3 allein 40, jede Variante mit Körpern 31 | Teile mitlesen lassen macht schlechter |
| Z6m Halten (60) | C3 allein 35 in 4,8 s, Körper-Varianten 27 bis 33 in 28 bis 50 s | dasselbe, dazu 6 bis 10 mal teurer |
| R4 Wake-Kopf (60, 12.10.) | C3 allein 42, immer A+B 38, **Orakel nur 45** | selbst perfektes Wecken rettet nur 3 Aufgaben |
| Z6 §24.25 Beobachter (75) | ohne 48, A 42, B 35, A+B 40, adaptiv 36 | Beobachter erkennen Konflikte (B 45 von 45), die Antwort wird trotzdem schlechter |
| Z3 C3 als Konsument (117) | direkt 0 von 117 | C3 sagt immer "UNKNOWN", auch wenn die Lösung im Prompt steht |
| Z3b | C3 gibt bei Ja/Nein-Regeln **immer** `true` zurück (234 von 234) | Das Modell liest die Regel nicht, es rät eine Konstante |
| Z6g | Block mit Hypothesen ausblenden: C3 41, mit Block schlechter | der Block selbst stört |
| Z5, Z5e Fokus | Koalition 181, feste Slots 183, kein Kontext 169 | Auswahl bringt nichts gegenüber einfachen Slots |
| B3 L1 (Versuch 7, 2 Saaten) | Latent schlägt "Attribut-Wörter" (+2,6 bis +6,8), **Latent = SCALAR (±0,4)** | Die Brücke trägt nicht mehr als eine Zahl |
| Z2d STEP2 | zwei Körper .88 gegen ein Körper .58 (+.30), aber **ein Körper mit zwei Zuständen** reicht (Z2l) | Vorteil kommt aus der Kombination von Sichten, nicht aus zwei verschiedenen Modellen |

Gegenbeispiele, die zeigen, dass die Teile einzeln arbeiten: Zweiter Versuch besser (24.1), Z12c World-JEPA auf Slots (.95 gegen .14 auf neue Kombinationen), Z6i2 Routenkopf lernt neue Hinweise (3 von 3 frische Saaten), BP2a Leck-Fix (.75 auf .19), Z2d Zeiger-Zitat (.17 auf .97).

## 2. Die Ursachen im Einzelnen

### A. Die Teile wurden nie zusammen trainiert (wichtigste Ursache)

**Beleg.** B1 ist ein LFM2.5-1.2B, B2 ein Qwen3.5-0.8B, C3 ein LFM2.5-350M. Das sind drei fertige Modelle von verschiedenen Herstellern mit verschiedenen "Sprachen" im Inneren.
Der Blueprint verlangt es so: Körper "eingefroren oder fast eingefroren", erst lernt der kleine Prädiktor (`body initially frozen or near-frozen`, `router frozen`, 1.10 "nicht jeder Prompt backpropagiert durch alles").
Die Verbindung läuft deshalb über Text (Zitate, Angebote) oder über eine kleine nachträglich gelernte Brücke (B3).
Die B3-Brücke besteht seit Versuch 7 ihre erste Stufe, ist aber nicht besser als eine einzelne Zahl (SCALAR). Latent bringt also bisher keinen Mehrwert gegenüber "sag dem anderen eine Zahl".

**Vergleich mit dem Hirn.** Zwischen den Hirnhälften, Arealen und Sinnen gibt es keine Übersetzer. Sie sind in der Entwicklung gemeinsam gewachsen (Ko-Adaption, kritische Phasen).
Der Sender lernt, das zu senden, was der Empfänger braucht, und der Empfänger lernt, das zu lesen. V13 trainiert nur einen der beiden Enden, und das nur klein.

**Meine Deutung (nicht bewiesen).** Eingefrorene Teile mit nachträglicher Brücke erreichen höchstens das, was der Empfänger schon ohne Brücke versteht.
Dass LATENT gleich SCALAR ist, kann auch heißen: Die Aufgabe braucht nur eine Zahl. Dann prüft der Test den Wert des Latents gar nicht (siehe G).

**Prüfbare Änderung.** P1 und P6 unten.

### B. Der Empfänger (C3, 350M) verwertet die Funde nicht

**Beleg.** Z3: C3 liest alle Zahlen richtig (117 von 117), entscheidet aber nie (0 von 117), selbst wenn die fertige Entscheidungszeile im Prompt steht.
Z6: Die Beobachter finden die Konflikte (45 von 45) und sehen die Korrekturen (15 von 15), die Antworten werden trotzdem schlechter (B signifikant, p = .004).
B1 und B2 als Antwort-Körper sind kein Ausweg: 72 und 63 Prozent falsch entschiedene Antworten, stets Tendenz zu "A".
Ein Werkzeug vor C3 (feste Regeln) entscheidet fehlerfrei (strict: 0 falsch). Das heißt: Die Entscheidung klappt dort, wo kein Modell lesen muss.

**Vergleich mit dem Hirn.** Im Hirn lernt das Entscheidungsareal während der Entwicklung, genau die Signale der Zuträger zu lesen. Hier bekommt ein Modell, das auf nichts davon trainiert wurde, einen neuen Textblock und soll ihn per Prompt-Anweisung nutzen. Das kleine Modell macht das nicht zuverlässig, und mehr Text im Prompt stört (Z6g).

**Prüfbare Änderung.** P2.

### C. Kein Lernsignal am echten Ergebnis

**Beleg.**
- LP2: Der Prädiktor lernt die richtige Zuordnung (.41 auf .99), die Antwort hängt aber nicht davon ab (110 gegen 110). Man hat das Ersatzziel gelernt, nicht das Ergebnis verbessert.
- Der Beobachter-"Nutzen" im Code heißt "Antwort deckt das Angebot ab", nicht "Antwort ist richtig" (Z6 Notiz).
- Z6k: Modulatoren pro Beispiel schlagen das Pfad-Tor (+.16 bis +.21), erreichen aber nur .52 bis .56 gegen eine saubere Decke von .82. Der Lerner schwankt sogar mit sauberen Labels zwischen .63 und .98 (Z6j).
- Die Wake-Entscheidung hat keine nützlichen Lernmerkmale: 6 von 7 Signalen waren konstant, der Kopf weckt nie (R4).

**Vergleich mit dem Hirn.** Dopamin und verwandte Systeme melden "besser oder schlechter als erwartet" am Ergebnis, und genau dieses Signal steuert, was sich festigt.
V13 hat die Modulator-Bauteile, aber das Signal kommt aus Ersatzgrößen oder aus wenigen Menschenurteilen (KL-Serie: bei 8 Korrekturen kein sicheres Tor).

**Prüfbare Änderung.** P1 (Ergebnis als Trainingsziel) und P7.

### D. Neues Wissen ins Gewicht schreiben beschädigt anderes, der Schlaf ist noch nicht echt

**Beleg.**
- BP2a: Der heutige LoRA-Pfad überträgt gelernte Fakten auf andere Personen (Leck .75 bis .81) und vergisst Allgemeinwissen. Mit Anker-Fragen und Unterraum-LoRA sinkt das Leck auf .16 und die Erinnerung bleibt 1.0. Aber das Q4-Tor ist auf dem Handy-Format noch instabil (BP2D_FAIL).
- Z9: Der gemessene Nutzen des Träumens kam daher, dass der Traumtext die gespeicherte Antwort enthielt (verbotenes Faktenschreiben). Der ehrliche Test "Traum nur für Verhalten" (policy-only) zeigt keinen Gewinn (NO_GAIN).
- BP7: Schlaf-Prüfliste, Rückbildung und Wochen-Simulation laufen (PASS), aber nur als Software mit Kunstdaten. Ein Training mit echten Gewichten über Wochen gibt es nicht.
- BP8: Die Plastizitäts-Steuerung (Age) hat kein unabhängiges Rauschsignal, zwei Versuche FAIL.

**Vergleich mit dem Hirn.** Das Hirn nutzt zwei Lernsysteme: Der Hippocampus lernt sofort, der Neokortex langsam, und im Schlaf wird abwechselnd (verschränkt) wiederholt, damit Neues Altes nicht überschreibt.
V13 hat den schnellen Teil (Fast Memory, funktioniert), aber der langsame Teil mit verschränkter Wiederholung ist nur als Simulation da.

**Prüfbare Änderung.** P5.

### E. Aufmerksamkeit wird nie unter Druck geprüft

**Beleg.** Z5: Kapazität bindet auf den Aufgaben **nie** (Grenze, Ersetzung, Unterbrechung je 0; höchstens 3 Kandidaten bei 4 Slots). Z5e: Koalition 181, feste Slots 183, ohne Hypothesen 169, alles im Rauschen. Z6a: Der adaptive Aufwand weckt die Körper bei 60 von 60 Aufgaben, davon 42 von 42 überflüssig.

**Vergleich mit dem Hirn.** Aufmerksamkeit entsteht, weil Kapazität knapp ist und Reize um sie streiten. Ohne Knappheit gibt es nichts auszuwählen, ein fester Slot reicht. Der Mechanismus ist also nicht widerlegt, er wurde nie gebraucht.

**Prüfbare Änderung.** P4.

### F. Keine Rückkopplung durch Vorhersage im Körper

**Beleg.** Alle Körper arbeiten vorwärts: Prompt hinein, Text heraus. JEPA-Vorhersage gibt es nur als externen kleinen Prädiktor (Action-JEPA, NumPy, Z12c auf Slots). BJ1 (JEPA-Term auf dem B1-Adapter): NO_SIGNAL. Die Aufgabe war schon mit normalem Training bei 1.00, also nicht aussagekräftig. Das World-JEPA ist nicht in den Antwortpfad verdrahtet.

**Vergleich mit dem Hirn.** Im Kortex laufen mindestens so viele Verbindungen von oben nach unten (Vorhersagen) wie von unten nach oben. Nur der Vorhersagefehler wird weitergegeben. Das spart Energie und liefert das Lernsignal gleich mit.

**Meine Deutung.** Das ist wohl nachrangig. Erst muss die Kopplung (A bis C) funktionieren, sonst bleibt die Rückkopplung auch ohne Nutzen. BJ1 zeigt: Ohne eine Aufgabe, die das Problem wirklich hat, ist kein Signal messbar.

### G. Die Messaufgaben sind zu leicht, um das Zusammenspiel zu zeigen

**Beleg.**
- R4: Orakel (perfektes Wecken) nur 45 von 60 gegen C3 allein 42. Die Körper können auf diesen Aufgaben kaum etwas retten. Mehr als 3 Aufgaben sind nie zu gewinnen, bei einem Rauschband von etwa 7.
- Z5: Kapazität bindet nie (E).
- BJ1: Normales Training schon 1.00.
- B3: SCALAR gleich LATENT heißt vielleicht nur, dass die Aufgabe nur eine Zahl braucht.
- Gleiche Konfiguration zweimal gemessen: 8 von 60 Antworten kippen (Z6m). Kleine Unterschiede sind dann nicht zu sehen.
- Viele FAILs kamen, bevor die Voraussetzungen existierten (kein Konsument, kein Gewichtslernen, kein B1-B2-Abgriffspaar). Das ist "noch nicht testbar", nicht "widerlegt" (Blueprint-Abgleich 27.10.).

Wo die Aufgabe das Zusammenspiel **braucht**, klappt es: Z2d (B1 hat Detail, B2 Überblick): .88 gegen .58. Z6i2: neue Hinweise wirklich gelernt.

**Prüfbare Änderung.** P0 (zuerst).

## 3. Blueprint-Versprechen gegen heutigen Stand

Der Blueprint sagt selbst, dass V13 erst "funktioniert", wenn 24 Eigenschaften (§29) und zehn Tore (§100) erfüllt sind. Stand 21.10.: 0 von 10 Toren grün, 8 von 24 Eigenschaften erreicht, 14 teilweise. Nach seinem Wortlaut ist V13 ein **Harness-Prototyp**, kein Hirn. Das ist also kein Widerspruch zum Blueprint, sondern sein erwarteter Zwischenstand.
Neu in dieser Analyse: Der Blueprint verschiebt das gemeinsame Lernen (Expert-Deltas, tiefere Gradienten, Router) in die späten Stufen (STEP6C und danach), prüft aber alle Zusammenspiel-Tore (STEP2, 24.22, 24.25) **vorher**, im eingefrorenen Zustand. Diese Tore konnten kaum bestehen, weil gerade der Teil fehlt, der sie bestehen lässt. Die Reihenfolge ist also selbst Teil des Problems.

## 4. Priorisierte, prüfbare Änderungen

Jede Änderung hat Voraussetzung, Vergleich und Erfolgsgrenze. Das folgt der Regel "vor jedem Test Voraussetzungen und möglichen Gewinn prüfen".
Alle Zahlen sind Vorschläge und gehören vor dem Lauf vorregistriert.

**P0. Aufgaben bauen, bei denen die Körper nötig sind** (zuerst, billig, ohne Training).
- Warum zuerst: Ohne solche Aufgaben ist jeder Gewinn der folgenden Schritte unsichtbar (G).
- Aufgaben: Detail und Überblick getrennt nötig (wie Z2d), lange Sitzungen mit Platzmangel und Widersprüchen, mehrere Tage Abstand.
- Vorprüfung: Ein Orakel (perfekte Hilfe) muss mindestens 15 Aufgaben mehr lösen als C3 allein, bei 150 Aufgaben. Sonst ist die Aufgabe ungeeignet.
- Aufwand: gering, nur Cloud.

**P2. Den Empfänger lernen lassen, Funde zu verwerten** (Text, ohne neue Brücke, handytauglich).
- Idee: C3 (LoRA) mit Beispielen trainieren, in denen Angebote im Prompt stehen und die richtige Antwort von ihnen abhängt, plus Gegenbeispiele mit falschen oder irrelevanten Angeboten (dann ignorieren). Lehrer: ein stärkeres Modell in der Cloud, nur als Quelle der Beispiele (REFERENCE-Lane).
- Vorprüfung: P0-Aufgaben vorhanden, Z6-Bench als Konsument vorhanden.
- Erfolg: Beobachter A+B besser als "ohne" um mehr als das Rauschband (7 von 75), mit Kontrolle "Angebote gemischt" (gleich schlecht, sonst lernt es nur Format).
- Das ist neu gegenüber Z3/Z6: Dort wurde nur per Prompt gebeten.

**P1. Brücke und Empfänger zusammen am Ergebnis trainieren.**
- Idee: B1/B2 eingefroren, aber ein kleiner Quer-Aufmerksamkeits-Adapter beziehungsweise Prefix (der L2-Prefix, nach B3-L1-Replikation wieder freigegeben) **und** die C3-LoRA gemeinsam mit dem Verlust auf der Antwort. Nicht mit einem Ersatzziel (LP2).
- Kontrollen: Prefix aus vertauschten Angeboten, nur SCALAR als Nachricht, nur C3-LoRA ohne Brücke.
- Erfolg: gemeinsam > C3-LoRA allein und > SCALAR, jeweils über Rauschband, auf frischen Saaten.
- Vorprüfung: P0-Aufgaben, die eine Zahl nicht tragen kann (sonst gleich B3-Problem), und P2 als Basislinie.

**P6. Weniger Fremdmodelle: ein Körper, zwei Zeitskalen, gemeinsam trainiert.**
- Beleg dafür: Z2l (ein Körper mit zwei Zuständen reicht), und Hirnhälften teilen denselben Grundstoff.
- Idee: ein Backbone, zwei Adapter ("fein" und "grob"), gemeinsam mit Callosum-Verlust trainiert. Spart auch Speicher (ein Modell statt zwei, wichtig bei der 8-GB-Frage).
- Erfolg: STEP2 (Komplementarität) besteht und Arbeitsspeicher sinkt.
- Vorprüfung: P0 und BP2a (Leck-Fix) als Trainingsbasis.

**P5. Zwei Lernsysteme wirklich machen.**
- Idee: BP2a/BP2e (Anker, Unterraum) als Standard, dann Schlaf mit echter Gewichts-Konsolidierung und verschränkter Wiederholung, über viele simulierte Tage.
- Erfolg: Fakten bleiben ohne Notiz im Kontext abrufbar, Leck unter .2, Allgemeinwissen auf CE-Niveau, Kontrolle "Traum nur Verhalten" bleibt ohne Faktenschreiben.
- Vorprüfung: BP2e (Retention im neuen Trainer) muss bestehen, Verhaltenstest als Konsument (Z9-Notiz).

**P3. Wecken nach Bedarf aus dem Empfänger selbst.**
- Idee: Unsicherheit von C3 (Logit-Entropie, Antwort-Streuung) statt Prompt-Merkmalen. Nur bei hoher Unsicherheit Körper holen.
- Erfolg: gleiche oder bessere Trefferzahl wie "immer wecken" bei mindestens halber Zeit, **auf P0-Aufgaben**, weil nur dort wecken überhaupt helfen kann.
- Vorprüfung: P0. Auf den alten Aufgaben ist die Obergrenze 3 Aufgaben (R4).

**P4. Aufmerksamkeit unter Platzdruck.**
- Idee: Lange Sitzung, viele Ablenker, 4 Slots, Interrupts. Koalition gegen feste Slots, voller Kontext, Retrieval.
- Erfolg: Koalition über Rauschband besser als feste Slots. Sonst feste Slots als Standard (das vereinfacht das System).
- Vorprüfung: P0.

**P7. Ergebnis-Signal für die Modulatoren.**
- Idee: Modulatoren bekommen "Antwort richtig/falsch/vom Menschen bestätigt" statt Ersatzgrößen. Gewichte pro Beispiel (Z6k) mit den Lernregeln aus Z6i2 verbinden.
- Vorprüfung: P2 oder P1, damit überhaupt etwas Lernbares am Ergebnis hängt.

**P8. Rückkopplung durch Vorhersage in den Körper** (zuletzt).
- Erst wenn P1/P2 zeigen, dass eine Kopplung nützt. Dann Z12c-World-JEPA in den Antwortpfad und Vorhersagefehler als Wake-Signal. Auf einer Aufgabe mit echtem Bedarf (nicht BJ1-leicht).

### Reihenfolge

P0 zuerst. Danach laufen P2 und P6 parallel (beide ohne neue Brücke). Dann P1 und P5, danach P3, P4, P7, P8.
Ein Handy-Paket erst, wenn P0 bis P2 geklärt sind. Ein Gewinn auf dem Cloud-Rechner muss vorher da sein, sonst misst der Handy-Test nur Kosten.

## 5. Was ich nicht weiß

- Ob gemeinsames Training den Gewinn bringt, ist **nicht bewiesen**. Es ist die stärkste Erklärung, die zu den Belegen passt. P1 und P2 sind genau dafür da, das zu prüfen.
- Ob 350M Parameter für C3 überhaupt reichen, ist offen. Wenn P2 scheitert, ist das Argument für einen größeren Entscheider stärker.
- Ob "wie ein Hirn" bei diesen Größen messbar wird, ist unklar. Das Hirn hat 10^11 Neuronen, hier sind es etwa 2 Milliarden Parameter, die auf einem Handy laufen sollen.
- Die Neurowissenschaft hier ist Allgemeinwissen (Ko-Adaption, Vorhersage-Verarbeitung, komplementäre Lernsysteme, Aufmerksamkeit als Wettbewerb, Dopamin als Vorhersagefehler), keine neue Literaturrecherche. Aktuelle Quellen stehen in `research/FORSCHUNG_2026-10-27.md`.

## 6. Abstimmung mit laufender Arbeit

- Der Langtest im Thread "Offene Zielprüfungen grün machen" (Branch 8pfwut) wird nicht berührt. Diese Analyse ändert keinen Code.
- BP2 (Leck-Fix, Branch tfzd6v), BP7/BP8/BP10 (a667fm) und Z6i2 (h02m13) sind Grundlage für P5 und P7, nicht zu doppeln.
- Wichtig für die Roadmap: Die Pakete sollten als WP-HB0 bis WP-HB8 angelegt werden (HB = Hirn-Bau). Das ist ein Vorschlag, noch nicht in `ROADMAP.md` eingetragen.
