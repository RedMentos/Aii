# WP-N11 Router-Stabilität und Pre-Router-Vergessen mit echtem MoE-Körper (2026-10-12)

**Evidenzstufe:** Linux-Cloud-CPU (4 Kerne, 16 GB), HF transformers 4.57.3 / torch 2.8.0 fp32 als Referenz; Router-Parität zusätzlich mit llama.cpp b10964 (Quelle SHA `4c96d72c…`, selbst gebaut, Binär-Hashes nicht an die Codex-Registrierung gebunden). **Kein Redmi-Nachweis, keine Laufzeit-Integration, keine Beförderung.** Eingefrorene Runtime/Specs unverändert.

Körper: `utter-project/EuroMoE-2.6B-A0.6B-Instruct-2512` @ `96e19829`, 24 Schichten, 64 Experten, top-8, d=1024, Apache-2.0. Safetensors-SHA = HF-LFS-OIDs (geprüft). Eigene GGUF: F16 `d9e1feb6…`, Q4_K_M `8720d054…` (1,6 GB).

Befehle:
```
python3 scripts/moe_router_bench.py --model <euromoe> --model-id utter-project/EuroMoE-2.6B-A0.6B-Instruct-2512 \
  --revision 96e19829c2fe57c4d5d484ecbd6b0ad6b950cac6 --hash --out moe-router.json --steps 25   # 10 947 s, RSS 13,6 GB
python3 scripts/moe_router_parity.py prepare --model <euromoe> --out ids.jsonl
native-moe-router-tap euromoe-{f16,q4_k_m}.gguf ids.jsonl tap-<q> 4
python3 scripts/moe_router_parity.py compare ... --out runner-parity.json
```
Dateien: `moe-router.json` (alle Werte), `moe-router.log`, `runner-parity.json`.

## 1. Kalibrierung aus Empfänger-eigener Basis-Schwankung (B3-H6)

48 Texte (24 EN, 24 DE), identische Text-Token nach drei neutralen Vorspännen, 96 Vergleiche, p95, Marge 1,0:

| Regler | Wert |
|---|---|
| B3.max_router_kl | 0,0222 |
| B3.max_expert_flip_rate | 0,165 |
| B3.max_router_input_shift | 0,0380 |
| B3.max_residual_norm_shift | 0,0651 |
| (Bericht) expert_hist_shift / shared_drift / router_input_drift | 0,042 / 0,047 / 0,069 |

Status `TUNE_CALIBRATED` für diesen Körper/Runner/Datensatz – nicht universell, nicht in `specs/` geschrieben (eingefroren).

## 2. Latente Nachricht in den Empfänger-Residualstrom (B3-H6-Raster α)

Nachricht = mittlerer Residualvektor (Schicht 8) des Sender-Satzes „X was born in the town of Y.“ (L1-artige Mean-Pool-Nachricht) bzw. Zufallsrichtung gleicher Norm, skaliert auf α·‖h‖. Aufgabe: „In which town was X born?“ (8 fiktive Fakten je Seed). Nutzen = NLL-Senkung der Antwort-Token gegenüber NONE; EXACT = Satz als Text im Prompt. Mittel über Seeds 13/21/34:

| α | Sender: Router-Gate | Sender: Nutzen (nats) | Zufall: Router-Gate | Zufall: Nutzen | Alt-Text-Verlust Δ (Sender) |
|---|---|---|---|---|---|
| 0 | 3/3 PASS | 0 | 3/3 PASS | 0 | 0 |
| 0,01 | 3/3 PASS | +0,23 | 3/3 PASS | −0,14 | +0,018 |
| 0,025 | 0/3 (KL .021–.025, Flip .16–.17) | +0,26 | 3/3 PASS | −0,11 | +0,069 |
| 0,05 | 0/3 | −0,05 | 0/3 | −0,05 | +0,21 |
| 0,10 | 0/3 (KL .32–.47, Flip .67–.76) | +1,34 | 0/3 | +2,00 | +4,95 |

EXACT-Text: **+8,6 bis +10,2 nats**. Ergebnis: Innerhalb der Router-Stabilitätsgrenze (α ≤ 0,01) trägt die Mean-Pool-Nachricht +0,2 nats (Zufall −0,14), also ~2 % des EXACT-Kanals; die großen „Gewinne“ bei α = 0,1 entstehen bei zerstörtem Routing und gelten genauso für Zufallsrichtungen (kein Inhalt). Deckt sich mit B3 L1 FAIL: LATENT bleibt `unavailable`, SOURCE_EXACT bleibt Detail-Kanal. K-Slots/Rang aus dem B3-H6-Raster sind hier **nicht** gemessen (braucht den gelernten Selektor aus `b3bridge`).

## 3. Kontinuierliches Update auf neue Fakten (§16.2.1, §24.19, §91)

16 fiktive Fakten (Geburtsort), Adam lr 3e-4, Fenster Schichten 8–9, bis neuer Verlust ≤ 10 % des Starts oder 25 Schritte. Alt-Aufgabe = die 48 EN/DE-Texte. Volle Batch → die drei Seeds sind **identisch** (Seed ändert nur die Reihenfolge innerhalb der Batch); effektiv **ein** Lauf.

| Arm | Schritte | neu: Verlust | Alt Δ (nats) | Pre-Router-Drift | Router-Input-Drift | Route-KL alt | Top-k-Flip alt | Urteil |
|---|---|---|---|---|---|---|---|---|
| shared (Attention+Norms) | 25 | 5,29→0,73 | **+5,98** | 0,269 | 0,445 | 0,591 | 0,49 | einzige Gruppe geändert |
| router (Gate) | 25 | 5,29→4,24 | +0,015 | 0,018 | 0,026 | 0,066 | 0,22 | NO_FORGETTING |
| experts | 14 | 5,29→0,47 | +0,35 | 0,031 | 0,052 | 0,013 | 0,11 | einzige Gruppe geändert |
| all | 13 | 5,29→0,44 | +1,57 | 0,141 | 0,216 | 0,055 | 0,27 | **PRE_ROUTER_BOTTLENECK** |

Restaurations-Ablation im Arm „all“ (Gruppe auf alte Gewichte zurück, Alt-Verlust neu messen): shared zurück holt **81 %** des Vergessens zurück, experts 72 %, router 13 % (nicht additiv). Gegenfaktische Route in Schicht 8: Router-Gewichte allein KL .008/Flip .08, Eingangsdrift allein KL .007/Flip .08.

Befunde:
- Vergessen entsteht hier **vor dem Router**: Updates der geteilten Attention/Norms verschieben die Router-Eingänge stark (Drift .45 bei Δ +6 nats), Experten-Updates lernen die neuen Fakten schneller (14 statt 25 Schritte) bei 1/17 des Vergessens. Genau der in §16.2.1 beschriebene Fall: Reparatur nur an Experten/Router wäre falsch.
- Router-Updates allein lernen fast nichts Neues, verschieben aber die alte Route über die Basis-Schwelle (KL .066 > .022, Flip .22 > .165) **ohne** messbares Vergessen (+0,015) – Route-Stabilität und Retention sind getrennte Größen, beide müssen gemessen werden.
- Stützt die §91-Reihenfolge (Router + shared trunk zuerst eingefroren, Experten-Deltas vor Router, shared nur bei bewiesenem Pre-Router-Engpass).

## 4. Runner-Parität HF fp32 ↔ llama.cpp (gleiche Token, 48 Texte, alle 24 Schichten)

| Runner | Router-KL p95 | Top-k-Flip mittel / p95 | Router-Input-Drift p95 | innerhalb Basis-p95 |
|---|---|---|---|---|
| llama.cpp F16 | 0,0001 | 0,009 / 0,025 | 0,001 | ja |
| llama.cpp Q4_K_M | 0,018 | 0,118 / 0,159 | 0,069 | ja (knapp: Flip .159 vs .165, Drift .069 vs .069) |

Der native Abgriff liefert dieselben Router-Größen wie HF (F16 praktisch identisch). **Q4-Quantisierung allein** kippt im Mittel 12 % der Experten-Plätze – fast so viel wie die gesamte natürliche Kontext-Schwankung. Folge: Schwellen für das Handy müssen auf dem Q4-Runner selbst kalibriert werden, und Latent-/Update-Vergleiche immer innerhalb desselben Runners.

## Offen
- Redmi: RSS/Latenz von EuroMoE Q4_K_M (+ zweite Hälfte) und dieselbe Kalibrierung auf dem Gerät (WP-R).
- Zweite, verschiedene MoE-Hälfte (SmallThinker-4B-A0.6B) messen; Body-Wechsel nur als separat gebundener Vergleich, nicht in laufender Kohorte.
- Integration von `moe_router_monitor` in AG6/Homeostasis/b3bridge erst nach Ende des SourceHandoff-Freeze.

---

# Teil 2: zweite, verschiedene MoE-Hälfte und Handy-Runner (2026-10-12, später)

Zweiter Körper: `Tiiny/SmallThinker-4BA0.6B-Instruct` @ `a24932bb` (ex PowerInfer; Apache-2.0; 4,27 B / 0,6 B aktiv, 32 Experten top-4, d=1536, **Router vor der Attention** auf dem rohen Residual). Safetensors-SHA = HF-LFS-OIDs; konvertiert mit `convert_hf_to_gguf.py` (b10964, **ohne** Remote-Code, `.py`/`.pt` aus dem Repo nicht geladen) → F16 `8b1b01ad…`, Q4_K_M `1f6ce1d3…` (2,6 GB). EuroMoE-Q4 aus Teil 1 (`8720d054…`) bekam nachträglich `add_bos_token=false` + Chat-Template aus `tokenizer_config.json` ins GGUF (Tensoren unverändert, neu `b07881c7…`); die Router-Messungen geben Token-IDs explizit vor und sind davon nicht betroffen.

Befehl: `scripts/moe_router_native_bench.py --pair --body euromoe:…:8:ffn_norm:q4_k_m=… --body smallthinker:…:4:layer_input:f16=…,q4_k_m=…` → `native-two-halves.json`. Router-Abgriff im llama.cpp-Runner selbst (Handy-Runner, hier Linux-CPU).

## Kalibrierung auf dem Runner selbst (48 Texte EN/DE × 3 Vorspänne, p95)

| Körper / Datei | Router-KL | Top-k-Flip | Router-Input-Shift |
|---|---|---|---|
| EuroMoE HF fp32 (Teil 1) | 0,022 | 0,165 | 0,038 |
| EuroMoE llama.cpp Q4_K_M | 0,030 | 0,200 | 0,048 |
| SmallThinker llama.cpp F16 | 0,052 | 0,252 | 0,064 |
| SmallThinker llama.cpp Q4_K_M | 0,054 | 0,255 | 0,072 |

Der Router vor der Attention schwankt bei neutralem Kontextwechsel deutlich stärker (Flip .25 vs .17–.20): er sieht das rohe Residual statt eines normierten Attention-Ausgangs. Schwellen sind je Körper und Runner verschieden → nie übertragen.

SmallThinker F16 → Q4_K_M (gleiche Token): Flip mittel .134 / p95 .169, KL p95 .020 – innerhalb der Q4-eigenen Basis-Schwankung (PASS).

## Speicher (Linux, VmHWM; kein Handy-RSS)

| | EuroMoE Q4_K_M | SmallThinker Q4_K_M | beide zusammen |
|---|---|---|---|
| Datei | 1,62 GB | 2,63 GB | 4,25 GB |
| llama.cpp Standard (CPU-Repack an) | 2,72 GB | 4,32 GB | **7,03 GB** (zwei Prozesse gleichzeitig) |
| `use_extra_bufts=false` (kein Repack-Duplikat) | 1,62 GB | 2,63 GB | ≈ 4,25 GB |

Nach 48 Texten sind praktisch alle Expertenseiten angefasst (RssFile ≈ Dateigröße): mmap spart bei diesen Routern **nichts**, alle Experten werden genutzt. Mit dem Standard-Repack liegen die Gewichte doppelt im RAM (mmap-Seiten + umgepackte Kopie). Für das 6-GB-Redmi heißt das: beide Hälften nur ohne Repack-Duplikat (oder ohne mmap) und neben C3/C2 voraussichtlich zu knapp; nur am Gerät messbar (WP-R).

## Kurze Qualitätsprobe (Q4_K_M, greedy, 4 Fragen, `quality-probe.txt`)
EuroMoE: Canberra ✓, Äpfel-Rechnung richtig (8−2) aber mit falscher Kopfzeile „3 apples“, Wien ✓, Himmel-blau-Erklärung auf Deutsch sachlich korrekt. SmallThinker: Canberra ✓, Rechnung richtig, „Vienna“ statt Wien, Himmel-blau-Satz auf Deutsch sachlich falsch. → Für die spätere deutsche Phase ist EuroMoE die stärkere Hälfte; SmallThinker ist englisch stärker im schrittweisen Rechnen. Vier Fragen sind nur ein Rauchtest, kein Benchmark.

## Vorschlag (keine Modellwahl)
B2 Gist = EuroMoE (64 Experten top-8, Deutsch), B1 Detail = SmallThinker (Router vor der Attention, mehr Gesamtparameter). Vor Produktivsetzung: separat gebundener STEP2-Vergleich gegen das heutige Paar und Redmi-Speicher.
