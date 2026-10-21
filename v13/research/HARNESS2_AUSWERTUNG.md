# Harness² (Google) – was es ist und was V13 davon braucht

Stand 2026-10-21, Thread „Harness2 von Google“. Lesart: gemeint ist **Harness²: Recursive Agent Harnessing for an Open World**
(Google Cloud AI Research, arXiv 2610.14224, Code `google-research/harness2`, Apache-2.0, kein offizielles Google-Produkt).
Quellen: https://arxiv.org/abs/2610.14224 · https://github.com/google-research/harness2 ·
https://pasqualepillitteri.it/de/news/25398/google-harness2-ki-agenten-verbessern-sich-selbst · https://www.i-scoop.eu/harness2-google/

## 1. Was ist es, in einfach

Ein Sprachmodell allein ist noch kein Agent. Drumherum braucht es ein „Geschirr“ (Harness): Anweisungen, Regeln, Gedächtnis,
Werkzeug-Hinweise, Hilfs-Agenten, Skripte. Harness² verbessert **nur dieses Drumherum**, die Modellgewichte bleiben gleich.

Zwei Schleifen:
1. **Pro Aufgabe (Vorschlagen – Ausprobieren – Zusammensetzen):** Ein Editor schlägt Änderungen am Drumherum vor, getrennt in
   „allgemeine“ und „fachspezifische“ Änderungen. Jede Variante läuft auf **derselben Aufgabe** neben einem Referenzlauf.
   Verglichen wird das Verhalten (was tat der Agent anders?), nicht eine richtige Lösung – die gibt es bei neuen Aufgaben ja nicht.
   Übernommen wird nur, was sich an einer konkreten Beobachtung festmachen lässt. Bei mehreren Ergebnissen wählt ein
   Auswähler **blind** (er weiß nicht, welche Variante welches Ergebnis gemacht hat).
2. **Über Aufgaben hinweg (Erfahrungs-Bibliothek):** Übernommene Änderungen werden mit einer Notiz gespeichert
   (Situation, Lehre, Beleg). Ohne genug Beleg wird **nichts** eingetragen. Spätere Aufgaben schlagen dort nach.

Gemessene Gewinne (Eigenangaben, nicht unabhängig geprüft): bis +11,5 Punkte WorkBuddy-Bench, +4,5 JobBench, +11,8 LAB.
Wichtig aus den Ablationen: ohne Bibliothek, ohne Trennung allgemein/fachlich oder ohne Zusammensetzen jeweils schlechter.
**Ungeführte Änderungen ohne Referenz und Vergleich machen den Agenten deutlich schlechter** (Code 73,4 → 63,2).

Nebenbei gefunden: DeepMind „Evo2“ (arXiv 2610.13025) nutzt die Protokolle solcher Drumherum-Änderungen später als
**Trainingsdaten für die Gewichte** – also Drumherum und Modell lernen gemeinsam.

## 2. Was passt zu V13

| Harness² | V13 heute | Urteil |
|---|---|---|
| Gewichte fest, Drumherum verbessern | Vieles in V13 ist genau Drumherum: Körper-Prompts, Werkzeug-Regeln, Regel-Parser, Zitat-Zeiger, Rezepte | passt direkt |
| Änderung nur mit Vergleich gegen Referenz | AG8 `agi/self_improve.py`: Vorschlag → Sandbox → Regressionsschild → Mensch gibt frei | passt, unser Schild ist sogar strenger |
| Erfahrungs-Bibliothek mit Beleg | Nur Ledger/ROADMAP für Menschen, nichts, was das System selbst nachschlägt | **fehlt** |
| Vergleich auf derselben Aufgabe ohne Lösung | Unsere Benches brauchen meist feste Gold-Antworten | **fehlt** für offene Aufgaben |
| blinder Auswähler | Vergleiche meist mit festen Metriken | teilweise |
| kein Rollback | Generation-Manifest mit Rückkehrpunkt | wir sind besser |
| Agent hat freies Netz | V13: Module nur mit bewusster Erlaubnis | wir sind sicherer, so bleiben |

## 3. Was nicht passt

- Harness² braucht große Cloud-Modelle (GLM-5, Gemini 3.5 Flash, Editor Claude Opus) und bezahlte API. Auf dem Redmi kann ein
  1-Milliarden-Modell nicht zuverlässig sein eigenes Drumherum umschreiben. Also: **Editor in der Cloud oder fest programmiert**
  (wie die Demo von Harness² ohne Modell), am Handy läuft nur das fertige, freigegebene Drumherum.
- Sicherheitsregeln und moralische Grenzen dürfen **nie** Teil des änderbaren Drumherums sein (Harness² erlaubt Änderungen an
  „guardrails“ – bei uns ausgeschlossen, wie schon bei AG8).
- Die Gewinne sind Eigenangaben auf Büro-Aufgaben, nicht auf kleinen Modellen geprüft. Für uns erst messen, dann glauben.

## 4. Neue Pakete (eingetragen in ROADMAP.md, nach den Z-Paketen; HX1 und HX3 sind klein und dürfen parallel laufen)

- **WP-HX1 Drumherum als Vorschlagsart in AG8** (Cloud, klein, kein Modell): neue Art `harness` mit fester Erlaubt-Liste
  (Körper-Prompt-Texte, Werkzeug-Hinweise, Parser-Regelsätze, Rezept-Vorlagen). Sicherheits-/Moralregeln, Age, Kanal nie.
  Gleicher Regressionsschild, gleiche Nutzerfreigabe, Rückkehrpunkt im Generation-Manifest. Tests.
- **WP-HX2 Vergleich auf derselben Aufgabe** (Cloud, Modelle): Referenzlauf + k Varianten mit gleichem Seed, Verhaltens-Unterschied
  protokollieren (Werkzeugwahl, Zitat, Token, Antwort), allgemeine und fachliche Vorschläge getrennt. Erste Probe: B2-Regel-Zitat
  bei STEP2. Vorregistriert; Gate: Gewinn auf zurückgehaltenen Aufgaben mit Konfidenzintervall > 0 und keine Achse schlechter.
  Kontrolle: „ungeführte Änderung“ muss schlechter sein (sonst misst der Aufbau nichts).
- **WP-HX3 Erfahrungs-Bibliothek** (Cloud, klein): je übernommener Änderung ein Eintrag (Situation, Lehre, Beleg-Pfad, Generation);
  Eintrag nur mit Beleg; Nachschlagen nach Aufgabentyp; Ablation mit/ohne Bibliothek. Einträge sind Daten, nie Befehle.
- **WP-HX4 Blinder Auswähler für Benches** (Cloud, klein): bei k > 1 Ausgaben anonymisiert vergleichen, Herkunft erst nach der Wahl
  aufdecken.
- **WP-HX5 Drumherum-Protokolle als Lerndaten (Evo2-Idee)** (später, gesperrt bis HX2 PASS): übernommene Änderungen + Ergebnisse als
  Trainingsdaten für das kontinuierliche Lernen der Körper (LoRA), mit Behaltens-Gate.

Bezug zum Ziel: Das ist Selbstverbesserung mit Belegpflicht und Menschen-Freigabe – genau die Form, die das Ziel verlangt
(verbessert sich, schadet nicht, holt nichts ohne Erlaubnis).
