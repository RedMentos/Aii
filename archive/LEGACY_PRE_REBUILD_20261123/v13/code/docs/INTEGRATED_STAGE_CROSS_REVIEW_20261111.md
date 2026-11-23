# Gegenprüfung der Stage-/Runtime-/JEPA-Parallelbranches — 2026-11-11

Ausgangspunkt eigener PR #1716: `ebf32205d91d0b1f2cdb097b193d72a0cd023f76`. Die nachstehenden parallelen Commits werden nicht pauschal als integriert oder grün bezeichnet. Gefrorene produktive Quellen bleiben unverändert.

| PR / genauer geprüfter HEAD | Befund / Übernahme |
|---|---|
| #1738 `982f554955c899f993e6d2576d6cf38d16207bb6` | Echten hashgebundenen Stager übernommen und im gemeinsamen Kandidaten weitergeführt: Builderprüfung vor Import, sichere Ausgabepfade, Ausschluss von Daten-/Modelldateien, Linux-No-Clobber-Publish, vollständige anfängliche Dateihashes. |
| #1740 `f780c798000a5c82fb37e69a9bf526ce0adfe222` | Echter QA-Smoke erwartete ausschließlich `v13/`-Ersetzungen, obwohl der Builder auch Tests erzeugt. Erwartung auf die tatsächlich erlaubten Roots `v13/tests/specs` korrigiert, Syntax und Dateihashes weiter geprüft. |
| #1742 `c20cf04ecaf712cdb10e21cdd3493cffeba8adab` | Exakter gezielter Lauf **3 PASS / 1 FAIL**: vorhandener Stage-Testordner wird ohne `exist_ok=True` erneut angelegt; die zwei Runtime-Fälle starten noch nicht. Kleine Reparatur übernommen, nicht benötigten synthetischen History-Shim aus diesem echten Runtime-Smoke entfernt. |
| #1744 `83d148749554b6ead475e86cc7820f3a6962e9cf` | Workflow-Kind von #1742. Originaljob `42969652114 / 130354888636` scheitert ebenfalls am vorhandenen Testordner. Eigenen Workflow auf dem reparierten gemeinsamen Kandidaten ergänzt; kein grünes Originalergebnis behauptet. |
| #1745 `7585bf80dfaab16c8b081e14c7496032d5b04bd8` | Unabhängige QA-Reparatur desselben `exist_ok`-Fehlers gesichtet; eigener Fix war bereits vorhanden. Keine zusätzliche Funktionsintegration oder grüne CI zugeschrieben. |
| #1741 `2157e0538fc452eecdc98954704e978b916d1553` | Nutzer-Nachtrag und Cross-Organ-Vertrag bytegleich übernommen. Verbindlicher zusätzlicher Langzeitumfang, kein Implementierungsnachweis. |
| #1737 `d00d6717b5b2619b55d648d533938a4053a7a209` | Tatsächliche synthetische Runtime/SQLite-, datendisjunkte Holdout-, Save-/Restart-/Readback-Prüfung übernommen; Testkörper bytegleich, äußerer Wrapper auf den aktuellen echten Stager umgestellt. Original-Spezial-CI `42960032697 / 130324113421` grün. Keine Verbesserungsschranke, daher kein Nutzennachweis. Vollsuite separat, nicht aus Spezial-CI abgeleitet. |

## Exakte Original-Vollsuiten

Unveränderte `git archive`-Kopien, `PYTHONPATH=.:tests /tmp/v13-online-review-venv/bin/python -m pytest -q tests`, Python 3.12 mit den dokumentierten lokalen Testabhängigkeiten. Kein geänderter Staging-Quellbaum und kein selektiver Testfilter.

### #1742

**109 FAIL / 5485 PASS / 51 SKIP / 94 ERROR / 3027 Untertests PASS**, 671,23 s. Originalquelle `c20cf04ecaf712cdb10e21cdd3493cffeba8adab`.

- Unverändertes entpacktes Rohlog SHA-256: `b565fa74ab7637ba996000d5702947eb51f7fb2282b7299415cf4d1cdfcc1726`.
- Verlustfreies `gzip -n` SHA-256: `dc0e50d482653f04f124a137c3fc38ca75dfa4fe52bcba52291c0ad9977ea502`.
- Datei: `proofs/integrated-stage-review-20261111/pr1742-exact-full-suite.log.gz`.
- Rohlog vor Kompression in der geplanten Veröffentlichung vollständig durch den Repository-Privacy-Scanner geprüft: CLEAN. Diese Zahlen gelten genau für #1742, nicht für #1737 oder die reparierte Kopie.

### #1737

**108 FAIL / 5483 PASS / 51 SKIP / 94 ERROR / 3027 Untertests PASS**, 738,86 s. Originalquelle `d00d6717b5b2619b55d648d533938a4053a7a209`.

- Unverändertes entpacktes Rohlog SHA-256: `a788fd1bbed8aef67e0a8c1cc4081b183ed7fecd10e2a7918ca2b633c4b6a292`.
- Verlustfreies `gzip -n` SHA-256: `37f573c48c04e56525681732d09c0a8e68facb2e12b25c5a8a29ed9c59525f16`.
- Datei: `proofs/integrated-stage-review-20261111/pr1737-exact-full-suite.log.gz`.
- Rohlog vor Kompression in der geplanten Veröffentlichung vollständig durch den Repository-Privacy-Scanner geprüft: CLEAN. Die Original-Spezial-CI ist davon getrennt; der reparierte neue gemeinsame Stager wurde in dieser Original-Vollsuite nicht eingesetzt.

## Eigener reproduzierter Endpfad

`INTEGRATED_CONTEXT_SOURCE_RECALL_20261111.md` bindet die neue Kontextnaht, exakten Builder, Staging-Befehl, lokale Testzahlen und Einschränkungen. Bereits bestehende Body-/C3-/World-/Archiv-/Feedback-Tests laufen zusammen in einer erzeugten Kopie. Mock-/fake-row-Alttests behalten ihren ausdrücklich ausgewiesenen Test-Shim; echte Runtime-/Kontexttests verwenden echte SQLite-Quellenprüfungen. Ein synthetischer Fit bleibt von nativer Qualität, unabhängiger Retention und Redmi-Evidenz getrennt.

Keine Änderung negativer Gates, produktiver Quellen oder fremder Branches. Kein Drive-Erfolg behauptet (bestehende Quota-403). Fremde Koordinationsnotizen unter `v13/coordination/` wurden als historische Ausgangsnotizen übernommen; ihre damaligen offenen/ungeprüften Aussagen werden durch diesen getrennten Review ergänzt, nicht rückwirkend umgeschrieben.
