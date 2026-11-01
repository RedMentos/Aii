# WP-Z11 Vorregistrierung: STEP4 Referenz-Lehrer (stärkeres Modell, nur Cloud) + §24.28B

Geschrieben und committet **vor** dem ersten Lauf (2026-10-22, Thread „Offene Ziel-Pakete Z6 bis Z12“).

## Frage
STEP4 (Blueprint §96 / STEP 4): Teacher läuft **nach** dem Self-Candidate, Ausgabe getrennt in der REFERENCE-Lane,
Mensch wählt self/teacher/Spans, Teacher ist eingefroren und keine Faktenquelle. **Exit: Dataset/Experience-Records sind
sauber getrennt und reproduzierbar.** Bisher waren die Lanes gebaut, aber nie mit einem stärkeren Referenz-Lehrer an
echten Aufgaben geprüft (ZIELABGLEICH: STEP4 🟡).

## Aufbau
Lehrer: `unsloth/Qwen3-4B-Instruct-2507-GGUF` `Qwen3-4B-Instruct-2507-Q4_K_M.gguf` (Apache-2.0, Repo-Revision a06e946b),
über `ModelManager.import_model('TEACHER', …)` als eigene TEACHER-Rolle (nur Cloud, nie im Handy-Paket). Self = echter
V13-Turn mit `effort=disabled` (C3 allein, deterministisch; R4 zeigte C3 allein 60/60 reproduzierbar). Bench-Modus wie
WP-T3b (Temperatur 0), RECORD_ONLY. Aufgaben `utility_bench2.tasks(seed=23)` (60).
Arme: `off` (Teacher aus, 60), `on` (Teacher an, nach jedem Self-Turn `teacher`-Job, 60), `on_repeat` (wie `on`, frisches
Home, erste 20 Aufgaben). In `on` und `on_repeat` je Aufgabe 1–10: Mensch-Auswahl `teacher` als `fact` (record) und
`self` als `preference` (record), über `memory.select` wie `:choose`.

## Kriterien (STEP4_EXIT_PASS nur wenn T1–T6 gelten, sonst STEP4_EXIT_FAIL mit Angabe)
- T1 Self vor Teacher festgehalten: in allen `on`-Aufgaben `own_answer_hash_before_teacher` = sha(Self-Text) =
  `self_candidate_hash`, Teacher-Nachricht nach Self-Nachricht, ExperienceRecord `teacher_seen_before_commit=false`.
- T2 Teacher-Text nie in USER/SELF-History: `native_history` der Sitzung enthält in keiner Aufgabe Teacher-Text
  (kein gemeinsames Stück ≥ 40 Zeichen, das nicht schon im Self-Text oder in der Aufgabe steht).
- T3 Teacher an/aus ändert Self nicht: Self-Ausgaben `on` = `off` in 60/60.
- T4 Mensch-Präferenz und Fakt-Korrektur getrennt: je ausgewählter Aufgabe zwei HumanDecision-Pakete mit `kind` fact bzw.
  preference, Teacher-Auswahl trägt `fact_authority = HUMAN_SELECTED_NOT_AUTOMATIC_TRUTH`, `teacher_truth_authority=false`.
- T5 reproduzierbar: STEP4-Experience-Fingerprint `on` = `on_repeat` in 20/20.
- T6 RECORD_ONLY verändert keine Parameter: Brain-Generation vor = nach, keine neuen Komponenten-Generationen.
Beschreibend: Lehrer-Nutzen als Referenz (Regex wie WP-T3b auf Teacher-Text: Teacher besser / schlechter / gleich), Lehrer-Zeit.
Nicht Teil dieses Pakets (STEP5): „Teacher-besser-Fälle verbessern später SELF ohne Teacher im Kontext“.

## Grenzen (vorab)
Cloud-CPU, ein Seed, generierte englische Aufgaben, Lehrer-Prompt ist der eingebaute deutsche Prüf-Prompt. Ein FAIL bleibt FAIL.
