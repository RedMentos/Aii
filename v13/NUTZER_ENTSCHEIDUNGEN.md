# Nutzerentscheidungen (RedMentos)

Dauerhafte Ablage, weil `code/docs/USER_DECISIONS_AND_OPEN_QUESTIONS.md` von `v13/verification.py:122` neu erzeugt werden kann.
Gilt vor abweichenden Stellen im Blueprint, bis der Nutzer etwas anderes sagt.

## 2026-10-09 (Thread „Übergabe komplett sichten“, Antwort auf SICHTUNG §5)
Wortlaut: „es sin viele modelle in einem des is eig alles definiert worden.. Sogar mehr als 2.. Au english zuerst das mans mit deutsch lernen au sehen kann später.. Worldmodel und so war au definiert. Es soll konstant lernen als end ziel.. Es soll basically eine runtergebrochene simulation eines hirns werden..“

1. **Viele Modelle, wie im Blueprint definiert** (B1, B2, C1–C5, World-Model usw., mehr als zwei). B1 und B2 sollen echt verschiedene Bodies sein, nicht dasselbe LFM2.5-1.2B. Der Ist-Stand B1 = B2 ist nur ein Harness-Zwischenschritt.
2. **Englisch zuerst.** Deutsch wird später gelernt, damit man das Lernen daran sehen kann. Folge: C3-Benchmark und System-Prompts (heute „Antworte auf Deutsch“ in `runtime.py:317,458`, `__main__.py:61`, `verification.py:138`, `proofs.py:200`) auf Englisch umstellen; Deutsch wird ein Lern-/Transfertest.
3. **World-Model gehört dazu** (Blueprint §7.2, §92.2, G-SELF-WORLD-005), braucht ein eigenes Arbeitspaket.
4. **Konstantes Lernen ist das Endziel.** Age-0-Shadow mit Freigabe bleibt der Startzustand, die Age-Hülle soll schrittweise dorthin führen, nicht dauerhaft blockieren.
5. **Ziel: eine heruntergebrochene Simulation eines Gehirns**, kein Chatbot.

## 2026-10-11: dauerhafte GitHub-Freigabe für dieses Projekt

Im Projektthread wurde konkret um Freigabe gebeten, den geprüften Stand auf den neuen Arbeitsbranch `codex/authority-live-comparisons` in `RedMentos/Aii` zu pushen. Auf die Erläuterung der Zustimmung antwortete der Nutzer um 04:35:02 Europe/Berlin: „Man so das du immer kannst“.

Dies ist die dauerhafte Freigabe, im Rahmen der beauftragten V13-Entwicklung Änderungen und nachvollziehbare Zwischenstände auf Arbeitsbranches in `RedMentos/Aii` zu veröffentlichen. Routine-Pushes dieser Projektarbeit brauchen keine erneute Nachfrage. Die Freigabe bleibt bestehen, bis der Nutzer sie ändert. Der Remote-Stand muss nach jeder Veröffentlichung geprüft werden; lokale Commits allein gelten nicht als erfolgreiche GitHub-Sicherung.

## 2026-10-11, 23:20–23:21 Berlin — Fortsetzung und agentenübergreifende Übergabe (aus Drive übernommen 2026-10-12)

- Der bestehende ausgearbeitete Drive-Plan bleibt verbindlich und muss weiter abgearbeitet werden. Zukunftsideen ergänzen ihn in getrennten Notizen und ersetzen keine offenen Arbeitspakete.
- Selbstständig bis zu einem belastbaren Stand für längere menschliche Alltagstests weiterarbeiten; in Tests entdeckte Fehler anschließend weiter bearbeiten. Kontinuierlicher Lernfortschritt/RSI- bzw. AGI-Zielrichtung bleibt das langfristige Ziel, kein bereits bewiesener Ist-Stand.
- Regelmäßig Code, Rohbelege, aktuelle Ergebnisse und Fortsetzungsnotizen sichern. Wechsel zwischen Codex, Claude und anderen Agents soll über GitHub und Drive jederzeit möglich sein. Erhaltene Fehler und ursprüngliche Gates gehören in die Übergabe.
- Fortschrittsinfos dürfen konkrete spätere Verbesserungen und Voraussetzungen nennen: lokale Handy-Tools, schrittweise Fähigkeiten/Freiheiten/Wissen und mögliche neuere Modelle. Modellwechsel brauchen gesonderte gebundene Vergleiche und ersetzen keine laufende vorregistrierte Messung.

## 2026-10-21 (Thread „Zitierhilfe an, Regeln ohne Halluzination“)
1. **Zitierhilfe an.** Körper dürfen auf exakte Quellsätze zeigen statt sie abzuschreiben („Menschen können ja auch einfach direkt zitieren“). Umgesetzt als Standard: `b2_quote_select=pointer`, `offer_quote_context_chars=200` und die gemessenen Begleitwerte.
2. **Gezielte Nachfragen zu Regeln: ja.** Aber Regeln lesen und prüfen soll nicht ein halluzinierendes Sprachmodell, sondern „Jeff“ (die JEF-Ebene laut Blueprint) bzw. eine feste, nicht-generative Komponente. Sprachmodelle dürfen Regeln höchstens wörtlich zitieren.
3. **Hauptziel Regelsatz:** Die KI tut nichts, wovon der Nutzer nichts weiß, sagt vorher, was sie tun würde, und legt Verbote („bitte tu das nicht“) nie falsch aus.
4. Alte Entwürfe, deren Inhalt im gemeinsamen Stand steckt, werden geschlossen (PR #2, #3, #4).
5. Handy-Tests nur, wenn sie wirklich helfen; sonst ohne Test weiterarbeiten. Keine vorgegebenen 20 englischen Beispielsätze nötig, Testsätze selbst erzeugen (auch von anderen Modellen umformuliert).

## Offen (Stand 2026-10-21, aus dem Zielabgleich `ZIELABGLEICH.md` §7) — noch keine Entscheidung
- Age-Plastizität `age_plasticity_policy = boot | stable_reopen | noise_aware` (Messung WP-AB, offen seit 10.10.; blockiert G-AGE-REOPEN-001, Paket WP-Z8).
- ~~Zitat-Kontext-Schalter einschalten~~ → entschieden 2026-10-21: an (siehe oben).
- Redmi-Läufe (WP-Z7): ohne sie können STEP5, STEP7 und drei §100-Gates nicht grün werden.

## Offen (Stand 2026-10-21, aus dem Zielabgleich `ZIELABGLEICH.md` §7) — noch keine Entscheidung
- ~~Age-Plastizität~~ und ~~Zitat-Kontext-Schalter~~: entschieden 2026-10-22, siehe unten.
- Redmi-Läufe (WP-Z7): ohne sie können STEP5, STEP7 und drei §100-Gates nicht grün werden.
- B2-Zeiger `b2_quote_select=pointer` einschalten (WP-Z2d, 21.10.: B2-Regelzitat .17 → .97, zwei Körper +.30 über B1; braucht zugleich den Zitat-Kontext-Schalter und eine Reparatur von `analyst_context`).

## 2026-10-22 — Age-Plastizität und Zitat-Kontext entschieden
Wortlaut 09:00 Berlin: „Ig noise aware ka? Welches besser in log term yk.. Und Man ja obv an“ (Antwort auf die zwei offenen Punkte oben).
1. **`age_plasticity_policy = noise_aware`** ist jetzt Standard (`config.py` DEFAULTS). Begründung für lange Sicht: im verrauschten Teil der WP-AB-Messung bester Wert (0,073 gegen boot 0,175, stable_reopen 0,129), Preis ist langsameres Umlernen bei echtem Zielwechsel (0,079 gegen 0,053). Blockiert G-AGE-REOPEN-001 nicht mehr; der Wiederöffnen-Test (WP-Z8) steht noch aus.
2. **Zitat-Kontext an:** `offer_quote_context_chars=200`, `b2_offer_body_state=false`, `offer_quote_min_chars=90` sind Standard.
Alte Werte bleiben als `LEGACY_PRE_20261022` für eingefrorene, vorregistrierte Harnesses und Tests des alten Verhaltens. Volle Suite 1609 Tests OK, 5 Skips.

## 2026-10-22 16:33 Berlin — Eignungs-Werkzeug im Handy-Paket an (Thread „STEP2-Nutzen Engpass“)
Entscheidungskarte „Sollen die zwei neuen Schalter ins nächste Handy-Paket, eingeschaltet?“, gewählt: **„Ja, beide an im Handy-Paket“**.
1. Zitat-Kontext: war schon an (siehe oben), bleibt.
2. Eignungs-Werkzeug (`:growth enable eligibility`) ist im nächsten Redmi-Paket (WP-Z7) vorab freigegeben. Age 0 = SHADOW mit Vergleich, Rezept mit strict-Prüfung (WP-Z3), Ja/Nein-Regeln nur deterministisch (WP-Z3b), nie von C3. Ob es danach dauerhaft an bleibt, entscheidet der Nutzer nach dem Handy-Test.
