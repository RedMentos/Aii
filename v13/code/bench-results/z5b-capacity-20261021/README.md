# WP-Z5b: Fokus-Koalition unter echtem Platzmangel (G-FOCAL-CAPACITY-003), 2026-10-21

Vorregistrierung: `PREREGISTRATION.md` (vor dem Lauf committet, Nachtrag nach Probelauf, Regeln unverändert). Skript
`code/scripts/z5b_capacity.py`, Tests `code/tests/test_z5b_capacity.py` (5, ohne Modell). Rohdaten `z5b.json`, Protokolle `run_*.log`.

Aufbau: 60 neue Aufgaben (update / combine / correction / distract, Saat 11), je 6 gespeicherte Notizen (alle abgerufen),
Effort `max`, 4 Plätze, 5 Läufe, echte Modelle (C3 LFM2.5-350M, B1 LFM2.5-1.2B, B2 Qwen3.5-0.8B), Cloud-CPU.
Antwortendes Organ (C5): B1 in 225, B2 in 75 von 300 Turns, nie C3. Wiedergabe-Treue 300/300.

## Die Platzgrenze greift jetzt
In **300/300 Turns 9 Kandidaten für 4 Plätze** (Z5: 0/300). 2992 CAPACITY-Ablehnungen, 1489 von 2700 Kandidaten abgelehnt.
Koalition im Mittel 2,46 Notizen + 1,54 Körper-Angebote. Damit ist die Frage aus Z5 jetzt wirklich prüfbar.

## Ergebnis

| Arm | bestanden (300) | je Lauf | Kontext (Zeichen) | ohne veraltete Zahl |
|---|---|---|---|---|
| shipped (live = Wiedergabe) | 68 (0,227) | 13 12 16 15 12 | 1946 | 0,44 |
| coalition_gated | 60 (0,200) | 16 10 11 13 10 | 1497 | 0,44 |
| full_context | 54 (0,180) | 9 13 13 10 9 | 2693 | 0,43 |
| fixed_slots | 55 (0,183) | 9 7 12 15 12 | 1549 | 0,47 |
| retrieval_only | 64 (0,213) | 12 13 13 13 13 | 560 | 0,49 |
| no_context | 47 (0,157) | 9 9 9 10 10 | 0 | 0,53 |

Gepaart, `coalition_gated` nur / Kontrolle nur (Vorzeichentest): vs. full_context 33:27 p = 0,52 (Vorsprung 1,2 je Lauf);
vs. fixed_slots 31:26 p = 0,60; vs. retrieval_only 32:36 p = 0,72; vs. no_context 38:25 p = 0,13; vs. shipped 26:34 p = 0,37.
**Rauschband** (shipped_live zwischen Läufen) = 4 Aufgaben.

Nach Art (shipped / coalition_gated / full / fixed / retrieval / none):
update 0,23 / 0,16 / 0,21 / 0,15 / 0,07 / 0; correction 0,25 / 0,16 / 0,05 / 0,01 / **0,53** / 0;
distract 0,43 / 0,48 / 0,45 / 0,57 / 0,25 / **0,63**; combine überall 0.

**Verdikt (vorregistrierte Regeln):** „schlägt Voll-Kontext“ **FAIL** (p = 0,52, Vorsprung 1,2 < Rauschband 4).
Nicht schlechter als Retrieval und feste Slots: ja. **G-FOCAL-CAPACITY-003 bleibt PARTIAL.**

## Die 7 Eigenschaften (300 echte Turns)

| Eigenschaft | gemessen | auftreten |
|---|---|---|
| 1 Kapazitätsgrenze | 300/300 Turns mit mehr Kandidaten als Plätzen | ja (Z5: nein) |
| 2 Wettbewerb | 1489 von 2700 Kandidaten abgelehnt | ja |
| 3 Prioritäts-Ersetzung | 11 Verdrängungen (DISPLACED_BY_SALIENCE_INTERRUPT) | ja (Z5: nein) |
| 4 Salienz-Interrupt | 0 Aufnahmen über die Interrupt-Regel | **nein** |
| 5 Re-entry | 300/300 Turns, 184 von 300 Re-entry-Angeboten in der Koalition | ja |
| 6 Quellbindung | 1200/1200 Koalitions-Elemente | ja |
| 7 Halten/Wiederherstellen | 2400/2400 Workspace-Plätze nach Neustart | ja |

Zu 4: Die 11 Verdrängungen werden von einem Kandidaten mit Salienz ≥ 0,80 ausgelöst, der dann aber schon über die Priorität
aufgenommen wird (Label PRIORITY). Eine Aufnahme *nur* wegen Salienz (Priorität unter der Schwelle) kam nie vor. Vorregistriert
zählt nur das als Eigenschaft 4, also bleibt sie offen.

## Befunde
1. Unter echtem Platzmangel ist die Koalition als Engpass für die Antwort (`coalition_gated`) **nicht besser** als alles in den
   Kontext zu hängen. Der Unterschied (+6 Aufgaben gepoolt) liegt im Rauschen. Gegenüber dem ausgelieferten Pfad, in dem alle
   abgerufenen Notizen an der Koalition vorbei in die Antwort gehen, verliert sie leicht (−8, p = 0,37).
2. Die Koalition wählt die *falschen* Notizen: Bei `correction` steht die richtige Korrektur in den ersten 4 abgerufenen
   Notizen (Retrieval 0,53), die Koalition behält sie seltener (0,16). Grund im Code: Notizen konkurrieren mit lexikalischer
   Ziel-Relevanz, gleicher Quellgüte und einem Redundanz-Abzug; veraltete und neue Versionen sehen für die Priorität gleich aus.
   Es gibt keinen Term für Aktualität oder „ersetzt“.
3. Bei `distract` (Antwort steht in der Nachricht) schadet jede Notiz-Schicht: ohne Kontext 0,63, Retrieval 0,25.
   Bei `update` hilft die Koalition kaum, bei `combine` (Rechnen über zwei Notizen) schafft es kein Arm.
4. Die Auswahl spart Kontext (1497 statt 2693 Zeichen, −44 %) ohne messbaren Verlust gegenüber Voll-Kontext. Das ist ein
   Ressourcen-Argument, aber kein Gate-PASS.

## Abweichungen und Grenzen
- Lauf 5 brach zweimal ab: einmal durch einen Container-Neustart (`run_reps1-4_partial5.log`), einmal weil eine Wiedergabe das
  native Kontextfenster überschritt (`run_rep5_crash_context_window.log`). Danach wird so ein Arm als Skip `CONTEXT_WINDOW`
  gezählt statt abzustürzen (Fehlerbehandlung, keine Regeländerung); Lauf 5 wurde vollständig neu gefahren, im fertigen Lauf
  gab es keinen Skip. In `z5b.json` stehen nur vollständige Läufe.
- Generierte englische Aufgaben, eine Saat, Regex nur auf der Endantwort (eine Antwort, die die richtige Zahl neben falschen nennt,
  besteht; dafür die Spalte „ohne veraltete Zahl“), lexikalischer Recall, gierige Dekodierung, Cloud-CPU statt Redmi.
- `coalition_gated` ist eine Wiedergabe; ob die nötige Notiz in der Koalition lag, wurde nicht je Turn protokolliert.

## Nächster Schritt (neu vorzuregistrieren)
Aktualität und Ersetzung als Prioritäts-Term für Notizen (z. B. jüngere Notiz mit gleichem Entity-Thema verdrängt ältere,
Quelle: Zeitstempel der Korrektur), dann dieselben 60 Aufgaben erneut gegen dieselben Kontrollen. Eigenschaft 4 braucht
Aufgaben, in denen ein salienter Kandidat unter der Prioritätsschwelle liegt.
