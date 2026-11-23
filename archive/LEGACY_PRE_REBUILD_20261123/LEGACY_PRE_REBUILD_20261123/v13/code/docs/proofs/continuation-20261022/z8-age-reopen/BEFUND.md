# WP-Z8b/Z8c Befund: Age-Wiederöffnen (G-AGE-REOPEN-001) — FAIL

Vorregistriert (`PREREG.md`, Commits `4f24fb7` vor Lauf 1, Nachtrag vor Lauf 2). Skript `scripts/z8_age_reopen.py`,
Daten `bench-results/z8-age-reopen-20261022/z8.json` (Lauf 1, Seeds 101–120) und `z8c.json` (Lauf 2, Seeds 201–220).
Echtes `AgeControl` auf echtem SQLite-Store, synthetischer linearer Strom (learn → noisy → shift → settle). Laufzeit 13 s.

## Ergebnis
**Lauf 1 `Z8_AGE_REOPEN_FAIL`** (Standard `noise_aware`): fünf von sechs Kriterien erfüllt, K2 verfehlt.
| Kriterium | Wert | Schwelle | |
|---|---|---|---|
| K1 öffnet bei echtem Wechsel | 20/20 Seeds (Plastizität .32 → .56) | ≥ 16/20 | ✅ |
| K2 Öffnen hilft | 19/20 Seeds besser, aber nur **7,4 %** weniger Fehler | ≥ 15/20 **und** ≥ 10 % | ❌ |
| K3 kein falsches Öffnen durch Rauschen | 1,249 | ≤ 1,25 | ✅ (knapp) |
| K4 schließt nach dem Umlernen | 0,59 | ≤ 0,8 | ✅ |
| K5 Neustart gleich | alle Werte identisch | gleich | ✅ |
| K6 kein Stufen-Flattern | Median 2 | ≤ 2 | ✅ |

**Lauf 2 (frische Seeds):** `noise_aware` wieder FAIL (K2 17/20, 3,8 %). Kandidat **`noise_aware_v2` `Z8C_V2_FAIL`**:
öffnet stärker (K2 9,3 %, nur 14/20), aber öffnet auch unter Rauschen (K3 1,48) und verliert den Rausch-Vorteil
(K7 +16 % Fehler in der noisy-Phase). Kandidat wird nicht übernommen; Produktcode unverändert.

## Was das heißt (einfach)
Der Age-Zustand macht technisch, was der Blueprint beschreibt: er öffnet bei einem echten Zielwechsel, schließt nach dem
Umlernen wieder, flattert nicht und übersteht einen Neustart bitgenau (Telemetrie `age_transition` 6–8 Ereignisse je Lauf).
**Aber das Öffnen bringt zu wenig.** Der größte Teil der höheren Plastizität nach dem Wechsel kommt von der Herabstufung,
nicht vom Wiederöffnen; der eigentliche Wiederöffnen-Anteil spart nur 4–7 % Fehler. Nach dem Wechsel lernt `noise_aware`
fast so langsam um wie fest konservativ (.125–.167 gegen .138–.176) und viel langsamer als `boot` (.072–.106).
Grund (dritte Bestätigung nach WP-AB): Age sieht nur den eigenen Fehler und kann Label-Rauschen nicht von einer echten
Verschiebung trennen. Jede Regel, die stärker öffnet, öffnet auch beim Rauschen (Lauf 2).

## Nächster Schritt (neues Paket, nicht in diesem Lauf)
Ein vom eigenen Fehler unabhängiges Rauschsignal (z. B. Uneinigkeit bei wiederholten/ähnlichen Eingaben, Quellen-Qualität
aus dem ModulatorPacket `source_quality`) als Eingang für `noise_aware`; neu vorregistrieren, gleiche K1–K7.
Gate G-AGE-REOPEN-001 bleibt PARTIAL/FAIL; Ablations-Basis und Neustart-Beleg liegen jetzt vor.

Grenzen: synthetischer Strom, kein Sprachmodell, `phone_measured=false`.
