# Vorregistrierung WP-Z2f: B2-Zeiger auf schweren Aufgaben, mit Kontext-Budget, das die alte Regel hält (2026-10-26)

Vor jeder Inferenz committet und gepusht. Skript `code/scripts/step2_z2f_context.py` (nutzt `step2_z2e_pointer_hard.py` als private Modulkopie),
Tests in `code/tests/test_step2_z2e.py`.

## Warum
WP-Z2e (`../../continuation-20261022/step2-z2e-pointer-hard/BEFUND.md`) war für den Zeiger nicht aussagefähig: in 288/288 B2-Angeboten fehlte die
Kickoff-Notiz mit den Regeln in B2s Kontext, weil `b2_context_chars` = 768 (serialisiert, inkl. Hypothesen) vom jüngsten Zug her füllt.
Rauchtest vor dieser Registrierung (Seed 99, zählt nicht): mit 1536 steht die Kickoff-Notiz bei Altair und Electra im Kontext; B2-Prompt ~800–870 Tokens.

## Was gleich bleibt
Die zehn Z2e-Episoden (4 LONG, 4 REVISED, 2 DETAIL), Arme CQ (aus) / CQP (Zeiger) / DQP (ein Körper, Zeiger), Z2b-Frage, Werkzeug-Replay, Metriken,
Entscheidungsregel und Sicherheitsbedingungen von Z2e (`PREREG.md` dort), Schwelle .60.

## Was sich ändert
- `b2_context_chars` = **1536** in allen drei Armen (vorhandene Einstellung, Bereich 0..4096; Live-Standard bleibt 768).
- Seeds **23, 24, 25** (neu).
- **Gültigkeitsprüfung zuerst:** Anteil der B2-Angebote auf schweren Episoden, deren früher Kontext die Kickoff-Notiz in voller Länge enthält, je Arm.
  Liegt er in einem Arm unter **.90** → `Z2F_NOT_TESTABLE` (kein Urteil über den Zeiger). Sonst gilt die Z2e-Regel mit Präfix `Z2F_`:
  `Z2F_POINTER_HOLDS` (CQP-Quote ≥ .60 und CI(CQP − CQ) > 0, sicher) · `Z2F_POINTER_PARTIAL` · `Z2F_POINTER_FAILS` · `Z2F_UNSAFE_OR_INVALID`.
- Sekundär wie Z2e (je Typ LONG/REVISED, STEP2-Kriterien mit DQP als Kontrolle, überholte Werte in Zitaten, falsch festgelegte Entscheidungen, Prompt-Tokens).

## Erwartung vor dem Lauf
- LONG: im Rauchtest wählte B2 die lange Kopfzeile → die Erweiterung trägt nur das Budget. Ein FAIL oder PARTIAL bei LONG ist gut möglich und wäre ein
  echter Befund gegen „Zeiger reicht“ (dann müsste B2 mehr als zwei Sätze wählen dürfen oder die Erweiterung bis zur ganzen Notiz gehen).
- REVISED: B2 muss geänderte und unveränderte Regeln aus zwei Notizen holen, mit zwei Plätzen knapp.
- Sicherheit: Werkzeug sagt bei Widerspruch nur zum aktuellen Text UNKNOWN; zitiert B2 alte und neue Regel zusammen, kann es falsch festlegen.

## Grenzen
Linux Cloud, 4 CPUs, kein Redmi; dieselben zehn Episoden wie Z2e (dort für den Zeiger ungelesen, da die Regel nie ankam). Diagnose, kein Kanon-PASS.
Schalter `b2_quote_select` bleibt aus; `b2_context_chars` live unverändert.
