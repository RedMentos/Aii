# R4 Teil 4: Bei Unsicherheit mit `calc` nachrechnen statt Körper wecken (2026-10-13, Thread K)

**Verdikt: NOT_SUPPORTED** (Richtung positiv, nicht signifikant). Vorregistrierung `preregistration.json` (sha256 `d1db61ec…3402`, Commit `b5849ab`, vor Seed 13), Bericht `report.json`.

**Aufbau.** Echte C3 LFM2.5-350M, R4-BENCH_CFG, Beobachter aus. Je Aufgabe: (1) normaler Runtime-Turn mit Ziffern-Unsicherheit (Hook aus Teil 3), (2) C3 schreibt per JSON-Schema einen Rechenausdruck, `v13.agi.tools.calc` rechnet exakt (ein bloßer Zahlwert ohne Operator zählt nicht als Rechnung), (3) frischer Turn mit angehängtem exakten Ergebnis. Politiken: C3 allein / immer nachrechnen / nur bei Unsicherheit (Schwelle auf Seed 7+11 gewählt: `digit_min_logprob` ≤ −0,58). Prompt in drei Runden nur auf Seed 7/11 entwickelt.

**Frische Aufgaben (Seed 13, 60).**

| Politik | bestanden | summary | compare | Nachrechnen | Zeit/Turn |
|---|---|---|---|---|---|
| C3 allein | 42 | 8 | 4 | 0 | 4,6 s |
| immer nachrechnen | 40 | 7 | 3 | 25 | 7,3 s |
| **nur bei Unsicherheit** | **45** | **11** | 4 | 12 | 5,8 s |

Gepaart gegen C3 allein: 5 gewonnen, 2 verloren, netto +3, Vorzeichentest p = 0,45 → Kriterium (≥ +5, p < 0,05) verfehlt. Keine Aufgabenart verliert.

**Lesart.**
1. **Summen gehen:** C3 schreibt in 15/15 Fällen den richtigen Ausdruck (Entwicklung und frisch); mit dem exakten Ergebnis steigt summary 8 → 11. Rest-Fehler: C3 nennt die richtige Summe, sagt aber nicht ausdrücklich, dass die Zeile falsch ist.
2. **Differenzen gehen nicht:** „wie viel mehr als die trockenste Stadt“ schreibt C3 nur in 1/15 Fällen richtig (meist Summe aller Werte, in der Entwicklung sogar das Beispiel abgeschrieben). Ein falsches „exaktes“ Ergebnis verdirbt dann auch richtige Antworten → deshalb verliert „immer nachrechnen“.
3. Unsicherheit als Auslöser begrenzt den Schaden (12 statt 25 Nachrechnungen) und ist die einzige Politik mit Plus.

**Folge (Vorschlag, nicht umgesetzt).** Wie WP-W2: das Modell sollte nur typisierte Werte liefern (Zahl je Entität), ein festes Rezept rechnet (Summe, max − min). Das ist robuster als ein vom 350M-Modell geschriebener Ausdruck. Größere Fallzahl nötig, um +3 von Rauschen zu trennen. Keine Runtime-Änderung; `toolstep.py` bleibt beim BOOT-Regex.

**Grenzen.** Generierte englische Aufgaben, Regex-Prüfung (u. a. „incorrect“ muss fallen), Ergebnis als angehängter Nutzertext statt TOOL_RESULT-Schicht, Cloud-CPU. C3 allein ist hier über Läufe nicht ganz stabil (Seed 11: 41 statt 42 in Teil 3; anderer Cache-Verlauf durch die Zwischenaufrufe).
