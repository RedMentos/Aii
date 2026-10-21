# WP-Z5b Vorregistrierung: Fokus-Koalition unter echtem Platzmangel (G-FOCAL-CAPACITY-003)

Geschrieben und committet **vor** jedem Modelllauf, 2026-10-21. Folgepaket zu WP-Z5 (`../z5-focal-controls-20261021/`):
dort griff die Platzgrenze nie (höchstens 3 Kandidaten bei 4 Plätzen), also konnten Kapazitätsgrenze, Ersetzung und
Interrupt gar nicht vorkommen. Gate-Text (Blueprint §85.3) und §99-Kontrollen wie in Z5, Original-Gate wird nicht aufgeweicht.

## Aufgaben (neu, `scripts/z5b_capacity.py: tasks(seed=11)`, 4 Arten × 15)
Jede Aufgabe legt vor dem Turn in einer eigenen Sitzung **6 gespeicherte Nutzernotizen** an (Fakt-Korrekturen, je eigener
Schlüssel, damit keine die andere ersetzt). Geprüft ohne Modell: alle 6 bestehen den lexikalischen Recall bei
`memory_top_k = 6` (60/60). Mit ca. 3 Körper-Angeboten (Effort `max`) sieht die Fokus-Schleife also ca. 9 Kandidaten für 4 Plätze.
- `update`: drei datierte Budget-Notizen (die neueste ist richtig) + drei Neben-Budgets als Ablenker; Frage nur nach dem Budget.
- `combine`: neueste Budget-Notiz minus Ausgaben-Notiz (zwei Notizen nötig), vier Ablenker (alte Budget-Notiz, Reise-Budget, Reise-Ausgaben, Hardware).
- `correction`: Nachricht enthält eine Fahrrad-Zählung, eine gespeicherte Korrektur ersetzt sie; fünf Umfrage-Ablenker.
- `distract`: Antwort steht in der Nachricht (Spesen-Summe wie WP-T3b), alle sechs Notizen sind Ablenker.
Bestanden = richtige Zahl in der Endantwort (Regex wie WP-T3b). Nebenmaß `clean` = keine veraltete/ablenkende Zahl in der Antwort.

## Aufbau
- Modelle und Bench-Modus wie Z5 (C3 LFM2.5-350M, B1, B2; Temperatur 0, gierig, Frist 600 s, Observer 180 s), Effort `max`,
  `focal_slots = 4`, `memory_top_k = 6`, `history_turns = 0`, frisches Home je Lauf.
- Ausgelieferter Laufzeitpfad: abgerufene Notizen gehen **immer** in die Antwort (Schicht ACTIVE_VIEW), die Koalition filtert nur
  Körper-Angebote. Der Live-Turn ist Arm `shipped_live`.
- Wiedergabe im selben Turn aus denselben abgerufenen Notizen und Angeboten an dasselbe antwortende Organ (wie Z5); nur die
  Notiz- und Hypothesen-Schicht unterscheiden sich:
  - `shipped` = Wiedergabe des Live-Kontexts (Treue-Prüfung)
  - `coalition_gated` = nur Notizen **und** Körper-Angebote, die in der Live-Koalition sind (B4 als Engpass für die Antwort)
  - `full_context` = alle abgerufenen Notizen + alle Angebote des Turns
  - `fixed_slots` = die ersten 2 abgerufenen Notizen + je Körper das neueste Angebot (4 feste Plätze, kein Wettbewerb)
  - `retrieval_only` = die ersten 4 (`focal_slots`) abgerufenen Notizen, keine Körper-Angebote
  - `no_context` = keine der beiden Schichten
- 5 Läufe × 60 Aufgaben. Rauschband = größte Differenz der Bestanden-Zahl von `shipped_live` zwischen zwei Läufen.

## Messgrößen
Wie Z5: Bestanden gepaart je (Lauf, Aufgabe), exakter Vorzeichentest, je Art; Kontextgröße; die 7 Eigenschaften aus der
echten Telemetrie. Neu: Eigenschaft 1 = Anteil Turns mit mehr Kandidaten als Plätzen (größte Kandidatenzahl im Turn);
Zahl der CAPACITY-Ablehnungen; Mischung der Koalition (Notizen vs. Körper).

## Entscheidungsregeln (vorab festgelegt)
- **„Schlägt Voll-Kontext“ PASS** nur wenn gepoolt `coalition_gated` mehr Aufgaben besteht als `full_context`, Vorzeichentest
  p < 0,05 **und** mittlerer Vorsprung je Lauf > Rauschband.
- Bindet die Platzgrenze in < 50 % der Turns, ist das Ergebnis „nicht prüfbar“ (kein PASS).
- Nicht schlechter als `retrieval_only` / `fixed_slots` = nicht signifikant schlechter (p ≥ 0,05 oder besser).
- Wiedergabe-Treue (`shipped` = `shipped_live`) unter 95 % → Ergebnis nur mit Vorbehalt.
- Zusätzlich berichtet (ohne Gate-Wirkung): `shipped_live` gegen `full_context` und `coalition_gated` gegen `shipped`.
- **G-FOCAL-CAPACITY-003 wird nur grün**, wenn der Gate-Teil PASS ist, beide „nicht schlechter“ gelten **und** alle 7
  Eigenschaften auftreten (> 0). Sonst bleibt es PARTIAL.

## Grenzen (vorab)
Generierte englische Aufgaben, eine Saat, Regex nur auf der Endantwort, lexikalischer Recall statt Embedding, gierige
Bench-Dekodierung, Cloud-CPU statt Redmi, `coalition_gated` ist eine Wiedergabe (im ausgelieferten Pfad gehen Notizen an der
Koalition vorbei). Ein Probelauf mit 4 Aufgaben × 1 Lauf zählt nicht; Änderungen danach nur als Nachtrag vor dem Hauptlauf.

## Nachtrag nach dem Probelauf (2026-10-21, vor dem Hauptlauf, keine Regeländerung)
Probelauf 4 Aufgaben × 1 Lauf (zählt nicht): in allen 4 Turns 9 Kandidaten für 4 Plätze, 4–5 CAPACITY-Ablehnungen je Turn,
Koalition 2–3 Notizen + 1–2 Körper; Wiedergabe-Treue 4/4. Ersetzung (Verdrängung) und Salienz-Interrupt traten im Probelauf
nicht auf. Hauptlauf 5 × 60 mit unveränderten Aufgaben, Armen und Entscheidungsregeln gestartet.
