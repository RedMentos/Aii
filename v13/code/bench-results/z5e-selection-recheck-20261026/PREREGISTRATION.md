# WP-Z5e Vorregistrierung: Verdient die Fokus-Auswahl ihren Platz? (Wiederholung nach dem Überlauf-Fix)

Geschrieben und committet **vor** dem Hauptlauf, 2026-10-26. Ein Probelauf (8 Aufgaben, 1 Lauf, Saat 71) dient nur der
Funktionsprüfung und zählt nicht.

## Anlass
WP-Z5c (`../z5c-focal-session-20261022/`): Die Koalition schlug Voll-Kontext nur über die Größe (Voll-Kontext lief 158/300 über)
und war signifikant schlechter als „ohne Hypothesen“ (19:41, p = 0,006). Der Live-Pfad lief selbst 41/300 über.
WP-Z5d (`../z5d-context-fit-20261022/`, PR #407) hat den Live-Überlauf behoben (`context_fit active`: 188/300, 0 Überläufe).
Frage jetzt: Bringt die Auswahl (Aufmerksamkeit/Koalition) auf dem reparierten Pfad etwas, oder soll sie vereinfacht werden?

## Aufbau
- Skript `scripts/z5e_selection_recheck.py` (nutzt `z5_focal_controls.run_rep(session_mode=True, fit_arms=True)`).
- **Frische Aufgaben:** Lauf i nutzt `utility_bench2.tasks(seed)` mit Saat 71, 72, 73, 74, 75 (je 60 Aufgaben, 4 Arten × 15),
  Reihenfolge mit derselben Saat gemischt. Keine dieser Aufgaben kommt in Z5/Z5c/Z5d (Saat 7) vor (Test).
- Alle 60 Aufgaben eines Laufs in **einer** Sitzung, Effort `max`, Bench-Modus (greedy), `history_turns 0`,
  `context_fit active` (ausgelieferter Standard), frisches Home je Lauf, gleiche Modelle wie Z5c/Z5d.
- Arme wie Z5c, im selben Turn aus denselben Angeboten, an dasselbe antwortende Organ:
  `coalition` (Wiedergabe der Live-Koalition), `full_context` (alle Angebote + alle gehaltenen früheren Hypothesen),
  `fixed_slots` (neuestes Angebot je Körper + 2 neueste gehaltene), `retrieval_only` (Top-4 lexikalisch aus Nachricht + gehaltenen Texten),
  `no_hypotheses` (ohne Hypothesen-Schicht). Dazu `coalition_live` (der echte Turn).
- **Neu: gleiche Größenregel für alle Arme** (`fit_arms`): Passt ein Arm nicht ins native Fenster (exakte Tokenzahl, Grenze wie
  `context_fit.budget`), werden erst gehaltene frühere Hypothesen (älteste zuerst), dann die letzten Einträge der Schicht gestrichen
  (einer bleibt). Passt es danach immer noch nicht → Overflow = nicht bestanden. Damit entscheidet die Größe allein nicht mehr.

## Entscheidungsregel (Auswahl-Frage; Entscheidungsarm = `coalition`-Wiedergabe, bei Wiedergabe-Treue < 0,95 stattdessen `coalition_live`)
Gepaarter Vorzeichentest je (Lauf, Aufgabe), α = 0,05, gegen die einfacheren Arme `no_hypotheses`, `retrieval_only`, `fixed_slots`, `full_context`:
- **SIMPLIFY** (vereinfachen): Koalition signifikant schlechter als mindestens ein einfacherer Arm.
- **KEEP** (behalten): sonst, und Koalition signifikant besser als `no_hypotheses`.
- **NO_GAIN** (kein Nutzen belegt): sonst. Auch das heißt: Die Auswahl verdient ihren Platz auf diesen Aufgaben **nicht**;
  Empfehlung dann: Hypothesen-Schicht in langen Sitzungen nicht als Standard, Auswahl auf SHADOW, bis eine Aufgabenart Nutzen zeigt.
- Nur berichtet, entscheidet nicht: alte G-FOCAL-CAPACITY-003-Regel (`analyse().verdict`), Ergebnis je Art, Intrusion,
  Anzahl Größen-Kürzungen je Arm, Vergleich nur auf Turns ohne jede Kürzung.
- FAIL bleibt FAIL: Nach dem Lauf werden keine Regeln, Arme oder Saaten geändert. Ein Neustart der Maschine setzt den Lauf
  am letzten fertigen Lauf fort (fertige Läufe bleiben, der abgebrochene wird ganz neu gestartet).

## Grenzen
Generierte englische Aufgaben (4 Arten), Regex auf der Endantwort, lexikalisches Retrieval, greedy, Cloud-CPU (nicht Redmi),
Ablenker sind frühere Aufgaben derselben Bench. Ein NO_GAIN hier sagt nichts über Aufgaben, die echte Auswahl brauchen
(z. B. lange echte Gespräche mit vielen relevanten Quellen).
