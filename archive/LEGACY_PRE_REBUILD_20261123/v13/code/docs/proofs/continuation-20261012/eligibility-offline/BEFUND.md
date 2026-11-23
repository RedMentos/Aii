# WP-W2c Regel-verankerter Wächter + Werkzeug `eligibility` — Befund (Thread H, 2026-10-12)

Evidenzstufe: **Software + Offline-Nachrechnung exponierter, aufgezeichneter Antworten** (keine neue Inferenz). Report SHA256 `9d95a663cdf914e0fd077ef4f94ec1cd7e6e44f646a8bd86c21a8ccfc67e36bb`, Skript `scripts/eligibility_offline_recompute.py`, Eingaben digest-geprüft (WP-W2 + WP-W2b, 120 Zeilen mit Extraktion).

## Was jetzt im Code ist
- `v13/agi/eligibility.py` (`eligibility-v2-anchored`): Rezept (günstigste geeignete Option, A bei Gleichstand, fehlende Regel → UNKNOWN) und deterministischer Wächter: Regelwert zählt nur, wenn die Evidenz ihn direkt nach seinem Regelwort nennt („budget 61 euros“, „deadline 8 days“, „local-only requirement: false“); ein Wert, der einer in der **aktuellen** Quelle genannten Regel widerspricht, gilt als nicht verfügbar; Optionswerte nur im eigenen Options-Satz. Analysten-Hypothesen sind nie Evidenz. Das Modell muss nichts zitieren.
- `ToolRegistry` kennt `eligibility` als READ_LOCAL-Werkzeug, **aus, bis der Nutzer es aktiviert** (IH-H29). Neuer Argumenttyp `text` (Quelltext mit z. B. `;`, Länge ≤ 4000, ohne Shell-Prüfung) ist nur für READ_LOCAL-Specs erlaubt (`ToolSpec` wirft sonst).
- Noch **nicht** im Live-Turn: kein Vorschlags-/C5-Pfad ruft das Werkzeug, kein Extraktions-Pass im Konsumenten. SHADOW-Infrastruktur, kein gelernter Nutzen.

## Ergebnis Nachrechnung (120 Zeilen)
- Token-Wächter-Zeilen (extract_tool): **keine exakte Zeile verloren** (C3/B2/B1 alt 7/8/7, neu 6/8/8 unverändert).
- **Falsche festgelegte Entscheidungen 3 → 0** (C3 Umber NONE, C3/B1 Pelt): überholte Regeln werden jetzt als Konflikt erkannt und abgelehnt (UNKNOWN statt falscher Aktion). Das ist Ablehnung, keine Korrektur.
- extract_span-Zeilen mit dem neuen Wächter (Modell-Zitate ignoriert): B1 neu 8/8, B2 6/8, C3 5/8 statt je 4/8. Die Werte waren meist richtig, nur die Zitate unbrauchbar.
- Die erfundenen Budgets (100, 80, 50) werden alle verworfen; die Kollisionsfalle (Budget = Kostenwert) ist jetzt per Test abgedeckt (`tests/test_eligibility_tool.py`), da das Regelwort fehlt.

## Grenzen
Exponierte Antworten, Regel-Muster an das Textformat dieser Fälle gebunden (englisch, „euros“/„days“). Andere Formulierungen (deutsch, „€“, „Frist“) werden bisher abgelehnt → nur UNKNOWN, nie falsch. Live-Anschluss und frische, anders formulierte Fälle sind eigene Schritte. Volle Suite 1296 OK.
