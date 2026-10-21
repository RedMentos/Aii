# WP-Z5c Vorregistrierung: Aktualitäts-Term für Notizen in der Fokus-Koalition (G-FOCAL-CAPACITY-003)

Geschrieben und committet **vor** jedem Modelllauf, 2026-10-21. Folgepaket zu WP-Z5b (`../z5b-capacity-20261021/`):
dort griff die Platzgrenze in 300/300 Turns, aber die Koalition behielt oft veraltete Notiz-Versionen, weil die
Fokus-Priorität keinen Term für Aktualität oder „ersetzt“ hat. Gate-Text (Blueprint §85.3) und Entscheidungsregel
„schlägt Voll-Kontext“ wie in Z5/Z5b, das Original-Gate wird nicht aufgeweicht.

## Der Schalter (Code, `v13/focal.py`, `v13/config.py`)
- Neuer Knopf `focal_note_recency` (0/1, **Standard 0 = aus**). Bei 0 ändert sich keine Priorität (die neuen Gewichte wirken
  nur, wenn die Terme gesetzt sind; Test `test_off_leaves_priority_unchanged`).
- Bei 1: abgerufene Notizen, deren Schlüssel nach Entfernen von Entity-Name, Entity-Label (Project/Projekt …),
  Kalenderwörtern (Monate, Wochentage, EN/DE) und Zahlen gleich sind, gelten als Versionen eines Platzes. Die zuletzt
  **gespeicherte** Version bekommt `recency = 1` (Gewicht +0,10), ältere `superseded = 1` (Gewicht −0,30).
  Einzige Aktualitätsquelle ist der Speicher-Zeitstempel, nicht der Text. Gewichte sind ENG-Werte, vorab festgelegt, nicht getunt.
- Bekannte Grenze vorab: Korrekturen gegen eine Zahl **in der Nachricht** (Art `correction`) erfasst der Term nicht (die
  Korrektur hat keinen älteren Notiz-Zwilling). „may“ als Modalverb in einem Schlüssel würde als Monat entfernt.

## Aufgaben
Z5b-Vorlagen (`scripts/z5b_capacity.py: tasks`), **drei Aufgaben-Saaten: 11 (= die Z5b-Aufgaben), 12, 13**, je 60
(update / combine / correction / distract × 15). Einzige Änderung gegenüber Z5b: die Notizen werden in realer
Reihenfolge gespeichert (datierte Notizen älteste zuerst, letztjährige Zählung vor der Korrektur); die übrigen Notizen
behalten ihre gemischten Plätze. In Z5b war die Speicher-Reihenfolge zufällig, ein Zeitstempel-Term wäre dort sinnlos.
Modellfrei geprüft (Tests): Inhalt von Saat 11 gleich Z5b, alle 6 Notizen werden abgerufen, Zeitstempel steigen in der
Speicher-Reihenfolge.

## Aufbau
- Modelle, Bench-Modus, Effort `max`, `focal_slots = 4`, `memory_top_k = 6`, `history_turns = 0`, frisches Home je Lauf wie Z5b.
- Live-Turn mit `focal_note_recency = 1` (= Arm `shipped_live`). Nach der Fokus-Schleife wird die **letzte Aufnahme**
  (`admit`) auf Kopien derselben Kandidaten zweimal wiederholt: mit den Termen (muss die Live-Koalition reproduzieren,
  Treue) und mit auf 0 gesetzten Termen (Koalition, die der Schalter-aus-Pfad aus denselben Kandidaten gebildet hätte).
- Wiedergabe-Arme wie Z5b an dasselbe antwortende Organ, nur Notiz- und Hypothesen-Schicht unterscheiden sich:
  `shipped` (Treue), `coalition_recency` (Notizen + Körper-Angebote der Live-Koalition), `coalition_plain`
  (der kontrafaktischen Koalition ohne Term), `full_context`, `retrieval_only` (erste 4 Notizen), `no_context`.
- 3 Saaten × 2 Läufe × 60 = 360 Turns. Rauschband = größte Differenz der Bestanden-Zahl von `shipped_live` zwischen den
  zwei Läufen einer Saat (Maximum über die Saaten).

## Messgrößen
Bestanden gepaart je (Saat, Lauf, Aufgabe), exakter Vorzeichentest, je Art und je Saat; Kontextgröße; `clean` (keine
veraltete Zahl). Mechanismus ohne Modell-Urteil: Anteil benötigter Notizen in der Koalition mit/ohne Term (update: neueste
Budget-Notiz; combine: neueste + Ausgaben; correction: Korrektur), Anteil veralteter Versionen in der Koalition,
Wieder-Aufnahme-Treue, Zahl der Turns, in denen sich die Koalitionen unterscheiden.

## Vorhersage (vorab)
Der Term hilft bei `update` und `combine` (veraltete Budget-Notizen fallen heraus), nicht bei `correction` und `distract`.
`combine` blieb in Z5b in allen Armen bei 0, dort wird auch mit Term kaum ein Bestehen erwartet (Rechnen der Modelle).

## Entscheidungsregeln (vorab festgelegt)
- **„Schlägt Voll-Kontext“ PASS** nur wenn gepoolt `coalition_recency` mehr Aufgaben besteht als `full_context`,
  Vorzeichentest p < 0,05 **und** mittlerer Vorsprung je Lauf > Rauschband. Bindet die Platzgrenze in < 50 % der Turns:
  „nicht prüfbar“.
- **„Term hilft“ PASS** nach derselben Regel für `coalition_recency` gegen `coalition_plain`.
- Mechanismus-Erfolg (ohne Gate-Wirkung): benötigte Notiz bei update in der Koalition mit Term häufiger als ohne.
- Nicht schlechter als `retrieval_only` = nicht signifikant schlechter.
- Wiedergabe-Treue oder Wieder-Aufnahme-Treue < 95 % → Ergebnis nur mit Vorbehalt.
- **G-FOCAL-CAPACITY-003 wird nur grün**, wenn „schlägt Voll-Kontext“ PASS ist, „nicht schlechter“ gilt und Eigenschaft 4
  (Salienz-Interrupt, in Z5b nie) auftritt. Dieses Paket misst Eigenschaft 4 nicht neu; ohne neuen Beleg bleibt das Gate PARTIAL,
  auch bei PASS im Gate-Teil.
- Schalter-Standard: bleibt 0. Ein Vorschlag „Standard 1“ erst bei „Term hilft“ PASS **und** keiner Verschlechterung bei
  `correction`/`distract` (nicht signifikant schlechter je Art), und dann als Nutzerentscheidung.

## Grenzen (vorab)
Generierte englische Aufgaben derselben Vorlagen (drei Saaten ändern Namen und Zahlen, nicht die Struktur), Schlüssel mit
Monatsnamen als Versionsmerkmal, Regex nur auf der Endantwort, lexikalischer Recall, gierige Dekodierung, Cloud-CPU statt
Redmi, `coalition_*` sind Wiedergaben, die kontrafaktische Koalition ersetzt nur die letzte Aufnahme (frühere Zyklen,
Re-entry und ausgewählte Körper-Angebote stammen aus dem Lauf mit Schalter an). Ein Probelauf (4 Aufgaben × 1 Lauf) zählt
nicht; Änderungen danach nur als Nachtrag vor dem Hauptlauf.

## Nachtrag nach dem Probelauf (2026-10-21, vor dem Hauptlauf, keine Regeländerung)
Erster Probelauf (4 Aufgaben × 1 Lauf, Saat 11, zählt nicht): Wieder-Aufnahme-Treue nur 1/4. Ursache: die Wiederholung hat
die Priorität aller Kandidaten aus ihren Termen neu berechnet, die Live-Aufnahme sortiert aber nach dem Prioritätswert, den
sie vorfindet (nach Inquisitions-Schritten nicht für alle Kandidaten neu berechnet). Korrektur (Messfehler, keine Regeländerung):
die Wiederholung übernimmt die Sortierwerte unverändert und berechnet ohne Schalter nur die Kandidaten neu, die einen
Aktualitäts-Term trugen. Zweiter Probelauf: Treue 4/4, in 3 von 4 Turns unterscheiden sich die Koalitionen mit/ohne Term,
Platzgrenze bindet 4/4. Hauptlauf 3 Saaten × 2 Läufe × 60 mit unveränderten Aufgaben, Armen und Entscheidungsregeln gestartet.
