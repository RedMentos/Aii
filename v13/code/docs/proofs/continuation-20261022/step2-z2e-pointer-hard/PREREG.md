# Vorregistrierung WP-Z2e: Hält der B2-Zeiger auf schwereren Aufgaben und gegen einen Körper? (2026-10-22)

Vor jeder Inferenz committet und gepusht. Skript `code/scripts/step2_z2e_pointer_hard.py`, Tests `code/tests/test_step2_z2e.py`.
Folgepaket zu WP-Z2d (`../../continuation-20261021/step2-z2c-b2-rule/`, Zeiger: B2-Regelquote .167 → .969). Nutzerentscheidung 22.10.:
„erst härter prüfen, dann einschalten“.

## Zwei Grenzen aus Z2d, die hier geprüft werden
1. Die Regel-Notiz war kurz (~96 Zeichen). B2 wählte oft nur die Kopfzeile, die Zitat-Erweiterung (200 Zeichen) machte daraus die ganze Notiz.
2. Die Ein-Körper-Kontrolle (B2 = B1-Gewichte, zwei Zustände) mit Zeiger lief nicht → Z2b-Kriterium 4b und §99 offen.

## Zusätzlich im Live-Pfad (vor dem Lauf)
`analyst_context` nahm erweiterte Zitate nicht an („Consumer quote differs“). Übernommen ist die gleiche Reparatur wie Thread „STEP2-Nutzen Engpass“
(`e6603fc`, Branch dq33gk): das Angebot merkt sich `quote_context_chars`, akzeptiert wird nur ein exakter Quellabschnitt ≤ dieser Breite, in den ein
angebotenes Zitat zeigt (`EXACT_SOURCE_SENTENCES_POINTED_BY_QUOTE`). Gleiche Zeilen im Kettenglied `quote_context`, damit ein späteres Zusammenführen
nichts doppelt. Test in `test_b2_quote_select.py`. Der STEP2-Harness baut seinen Konsumenten-Kontext selbst; die Messung hängt daran nicht.

## Neue Episoden (10, nie gesehen)
| Typ | Anzahl | Aufbau |
|---|---|---|
| LONG | 4 | Regel-Notiz ~236 Zeichen (in B2s 240-Zeichen-Auszug): lange Kopfzeile, ein Füllsatz, dann Budget/Frist/Lokal. Kopfzeile allein + Erweiterung trägt nur das Budget (Test prüft das). |
| REVISED | 4 | Kickoff mit Regeln, dann Statusnotiz „New budget/deadline/local-only requirement …“ (eine Regel geändert), dann Datenblatt. Jede Änderung ändert die richtige Aktion (Test). |
| DETAIL | 2 | Regeln im aktuellen Text (Gegenprobe, B2 nicht nötig). |
Gleiche Regelwörter wie Z2 (Wortlaut-Robustheit ist nicht Gegenstand), gleicher Harness, gleiche Z2b-Frage, Werkzeug-Replay.

## Arme × Seeds (9 Läufe × 70 Zeilen)
CQ (zwei Körper, Zeiger aus, Kontrolle) · **CQP** (zwei Körper, Zeiger, primär) · DQP (ein Körper + zwei Zustände, Zeiger). Seeds **20, 21, 22** (neu).

## Primäre Entscheidung
**B2-Regelquote** = Anteil der Zeilen (8 schwere Episoden × 4 B2-Varianten × 3 Seeds = 96), in denen B2s verifizierte Zitate, wie C3 sie bekommt,
**alle aktuell gültigen** Regelwerte nennen (bei REVISED den neuen Wert). Cluster-Bootstrap über 8 Episoden, 10 000 Ziehungen, RNG 20261021, 95 %.
- `Z2E_POINTER_HOLDS`: CQP-Quote ≥ **.60** und CI-Untergrenze (CQP − CQ) > 0, und sicher.
- `Z2E_POINTER_PARTIAL`: CI-Untergrenze > 0, aber Quote < .60, und sicher.
- `Z2E_POINTER_FAILS`: sonst (sicher).
- `Z2E_UNSAFE_OR_INVALID`: nicht sicher. **Sicher** = 0 falsch festgelegte Entscheidungen im Werkzeug-Replay von CQP, 0 Zeilen mit erfundenem Regelwert
  (weder aktuell noch überholt) in CQP-B2-Zitaten, keine Strukturfehler, alle Angebote mit Frage, Zeiger in jedem Seed von CQP/DQP benutzt, in CQ nie.
Je Typ (LONG, REVISED) dieselbe Regel als Sekundärurteil (je 4 Episoden, schwaches CI, nur berichtet).

## Sekundär: STEP2 auf den neuen Episoden (Z2b-Kriterien, primär CQP, Kontrolle DQP)
1 `both_exact` > bester Einzelkörper, CI > 0, jeder Seed · 2 je Körper ein Episodensieg in ≥ 2 Seeds · 3 komplementäre Fehlerprofile (≥ .25 je Richtung)
· 4a > `same_policy_dual` (CI > 0) · 4b > DQP `prompt_only_dual` (CI > 0) · 5 Struktur. §99 „zwei Körper lohnen“: alle + CQP − DQP `both_exact` CI > 0.
Dazu: Zeilen mit überholtem Wert in B2-Zitaten; falsch festgelegte Entscheidungen je Arm (auch Kontrolle) mit Zeilenliste; DQP-Quote; Prompt-Tokens.

## Erwartung vor dem Lauf
- LONG: Zeiger hält wahrscheinlich, wenn B2 die Regelsätze selbst wählt (in Z2d 72/96); fällt, wenn es meist die Kopfzeile wählt.
- REVISED: offen. Der Zeiger liefert nur 2 Sätze; B2 muss den geänderten wählen. Das Werkzeug weist nur Widersprüche zum *aktuellen* Text ab — werden
  alte und neue Regel zusammen zitiert, kann C3 den alten Wert lesen und das Werkzeug falsch festlegen. Das wäre ein echter Befund (auch in CQ möglich).
- Kriterium 3 bleibt vermutlich ✗ (b2_only kann Regelfelder ohne Optionen nie richtig haben).

## Grenzen
Linux x86 Cloud, 4 CPUs, kein Redmi; 10 Episoden × 3 Seeds; feste englische Regelwörter. Diagnose, kein Kanon-PASS (`canonical_gate_pass=false`).
Schalter `b2_quote_select` bleibt im Live-Code aus, bis das Ergebnis vorliegt und der Nutzer entscheidet.
