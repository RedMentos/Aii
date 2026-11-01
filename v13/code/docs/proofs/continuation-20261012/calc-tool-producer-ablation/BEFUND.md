# WP-W2d Eignungs-Werkzeug mit echtem Produzenten — Befund (Thread H, 2026-10-12)

Status **RECORDED_DIAGNOSIS** 96/96, 0 Strukturfehler, Artefakte unverändert. Prereg `2cf00ea6…2110` (vor Inferenz gepusht, `9556654`), Report SHA256 `8e78e284885fb07b25fc8205abd71df2f7a6008e2825e037a3837d404281184c`. Eingaben: byte-gleich die aufgezeichneten Konsumenten-Nachrichten der Regel-Weiterreichung mit **echtem B2-Produzenten** (Arme `current`, `earlier_quotes`). C3/B2/B1, W1-Draht, Linux-Cloud, kein Redmi, `canonical_gate_pass=false`, STEP2 UTILITY_FAIL bleibt.

| Konsument | Übergabe | Modell entscheidet: exakt / falsch festgelegt | Werkzeug: exakt / falsch festgelegt | Urteil |
|---|---|---|---|---|
| C3 350M | current | 0 / 1 | 6 / **0** | sicher + nützlich |
| C3 350M | earlier_quotes | 0 / 3 | 6 / **0** | sicher + nützlich |
| B2 0.8B | current | 0 / 8 | 6 / **0** | sicher + nützlich |
| B2 0.8B | earlier_quotes | 0 / 8 | 6 / **0** | sicher + nützlich |
| B1 1.2B | current | 0 / 8 | 6 / **0** | sicher + nützlich |
| B1 1.2B | earlier_quotes | 1 / 7 | 6 / **0** | sicher + nützlich |

## Befund
1. **Vorab festgelegte Regel erfüllt:** in allen 6 Modell/Übergabe-Armen 0 falsch festgelegte Entscheidungen und mehr exakte Zeilen als „Modell entscheidet“. Ohne Werkzeug legen B1/B2 sich in 7–8 von 8 Fällen falsch fest (meist NONE).
2. **Was die 6 exakten Zeilen sind (wichtig):** 4 davon sind richtiges UNKNOWN (fehlende/korrupte Regel), 2 sind Lumen/Pelt, wo die aktuelle Quelle alle Regeln selbst nennt (B). Die beiden Fälle, die frühere Regeln brauchen (Mira, Orrin, richtig A), werden in **allen** Armen abgelehnt (UNKNOWN), weil die echte Übergabe die Regel nicht vollständig trägt (z. B. „Deadline 6“ ohne „days“, oder gar kein Zitat). Das Werkzeug ersetzt keinen Transport; es entscheidet nur, was belegt ist, und lehnt den Rest ab.
3. Alle drei Konsumenten verhalten sich mit Werkzeug identisch: Die Rest-Leistung hängt am Transport (B2-Produzent), nicht mehr am Konsumenten.

## Was das ändert
- Die Konsumentenseite ist mit Extraktion + `v13.agi.eligibility` gelöst, so weit die Evidenz reicht; Engpass ist wieder der Regel-Transport früherer Quellen (BEFUND Regel-Weiterreichung). Nächster Hebel dort: deterministische Übergabe von Regel-Sätzen (ganze Sätze mit Regelwort statt freier Kurz-Zitate), getrennt vorregistrieren.
- Live-Anschluss des Werkzeugs (Extraktion im Konsumenten, Aufruf über C5/IH-H29, SHADOW-Vergleich) bleibt offen.
