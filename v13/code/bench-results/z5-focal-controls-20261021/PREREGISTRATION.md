# WP-Z5 Vorregistrierung: Fokus-Koalition gegen die §99-Kontrollen (G-FOCAL-CAPACITY-003)

Geschrieben und committet **vor** jedem Modelllauf, 2026-10-21. Gate-Text (Blueprint §85.3): Kapazitätsgrenze, Wettbewerb,
Prioritäts-Ersetzung, Salienz-Interrupt, Re-entry, Quellbindung, unbeaufsichtigtes Halten/Wiederherstellen, und
„gegen einfaches *alles in den Kontext hängen* gewinnen“. §99: Kontrollen *full context only; retrieval only; fixed slots*.

## Aufbau
- Aufgaben: die 60 Widerspruchs-Aufgaben aus WP-T3b (`utility_bench2.tasks(seed=7)`), unverändert.
- Modelle: C3 LFM2.5-350M, B1, B2 wie installiert (`v13.bootstrap`), Bench-Modus aus WP-T3b (Temperatur 0, C3 gierig, Frist 600 s, Observer 180 s).
- Weckpolitik für alle Arme gleich: Effort `max` (beide Körper, Re-entry innerhalb der Grenzen). So haben alle Arme denselben Kandidaten-Pool.
- **Live-Teil:** pro Wiederholung und Aufgabe ein echter Turn mit ausgelieferter Fokus-Schleife. Die Antwort ist der Arm `coalition_live`.
- **Wiedergabe-Teil (gleicher Turn, gleiche Angebote):** Nach der Fokus-Schleife werden aus denselben Angeboten die Kontexte der Kontroll-Arme
  mit dem echten `analyst_context` gebaut; die echte C3-Nachricht wird nur in der Hypothesen-Schicht ausgetauscht und C3 gierig neu gefragt.
  C3 allein ist laut R4 (60/60) reproduzierbar, also misst der Wiedergabe-Teil nur den Unterschied der Kontextwahl.
- Arme:
  - `coalition` = Wiedergabe mit genau der live gewählten Koalition (Prüfung der Wiedergabe-Treue gegen `coalition_live`)
  - `full_context` = alle Angebote des Turns (Erst-Angebote und Re-entry), keine Auswahl
  - `fixed_slots` = je Körper ein fester Platz mit dem neuesten Angebot dieses Körpers, ohne Wettbewerb/Schwelle/Interrupt
  - `retrieval_only` = keine Körper-Angebote; stattdessen die k = 4 (`focal_slots`) Sätze der Nutzernachricht mit höchster
    lexikalischer Relevanz (`v13.memory.relevance`) zur Frage, als wörtliche Zitate
  - `c3_alone` = keine Hypothesen-Schicht (Referenz)
- Wiederholungen: 5 Live-Läufe (frisches Home je Lauf). Rauschband = größte Differenz der Bestanden-Zahl von `coalition_live` zwischen zwei Läufen.

## Messgrößen
- Bestanden je Aufgabe (Regex wie WP-T3b), gepaart je (Lauf, Aufgabe), exakter Vorzeichentest, je Art.
- Kontextgröße (Zeichen der Hypothesen-/Retrieval-Schicht).
- Die 7 Eigenschaften als Messung aus der echten Telemetrie (FocalCycle/FocalItem/Workspace):
  1 Kapazitätsgrenze: Anteil Turns, in denen Kandidaten > Slots; 2 Wettbewerb: Anteil Kandidaten, die abgelehnt werden
  (BELOW_THRESHOLD/CAPACITY); 3 Prioritäts-Ersetzung: Verdrängungen; 4 Salienz-Interrupt: SALIENCE_INTERRUPT-Aufnahmen;
  5 Re-entry: Anteil Turns mit gezielter Re-entry und Anteil, deren Angebot in die Koalition kommt; 6 Quellbindung: Anteil
  Koalitions-Elemente, deren Quell-Refs lesbar sind; 7 Halten/Wiederherstellen: nach Neustart (neuer Store auf demselben Home)
  Anteil gespeicherter Workspace-Slots, deren Inhalt wiederherstellbar ist.

## Entscheidungsregeln (vorab festgelegt)
- **Gate-Teil „schlägt Voll-Kontext“ PASS** nur wenn gepoolt über 5 Läufe `coalition` mehr Aufgaben besteht als `full_context`,
  Vorzeichentest p < 0,05 **und** der Mittelwert-Vorsprung je Lauf größer als das Rauschband ist.
- Gegen `retrieval_only` und `fixed_slots`: „nicht schlechter“ = gepoolt nicht signifikant schlechter (p ≥ 0,05 oder besser).
- Wiedergabe-Treue: `coalition` ≠ `coalition_live` bei mehr als 5 % der Turns → Wiedergabe-Ergebnis nur mit Vorbehalt.
- Wählt die Koalition in ≥ 95 % der Turns alle Angebote (Kapazität bindet nicht), ist `coalition` ≈ `full_context` per Bau:
  Ergebnis dann „auf diesen Aufgaben nicht prüfbar“, kein PASS, Folge = Aufgaben mit echtem Kapazitätsdruck (neu vorregistrieren).
- G-FOCAL-CAPACITY-003 wird nur grün, wenn der Gate-Teil PASS ist **und** alle 7 Eigenschaften in der Messung auftreten (> 0).
  Sonst bleibt es PARTIAL. Original-Gate wird nicht aufgeweicht.

## Grenzen (vorab)
Generierte englische Aufgaben, eine Saat, Regex nur auf der Endantwort, lexikalisches Retrieval statt Embedding,
gierige Bench-Dekodierung statt anti_echo, Cloud-CPU statt Redmi.
