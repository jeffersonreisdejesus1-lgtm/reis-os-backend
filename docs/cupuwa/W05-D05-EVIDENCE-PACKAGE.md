# W05 D05 — Pacote consolidado de evidências (rebound)

Procedimento: CUPUWA-OCS-INDIVIDUAL-QUALIFICATION-001
Branch: cupuwa/ocs-individual-qualification-001
CURRENT_BOUND_HEAD: c83c78c167c184322553281ba30b41224c8ef977
EXECUTED_HEAD: c83c78c167c184322553281ba30b41224c8ef977

## Proveniência histórica (não é binding atual)

| HEAD | Papel |
|---|---|
| ad2d3036a669225a730ecc9c932d6acb69bd3ae5 | HISTORICAL — MissionContract no teste D04 |
| da1b582a61d75f221782c01f1e80c4d8eaac5bac | HISTORICAL — commit original dos probes D04 |
| 61d896ace12000db080842f3986fe3162df7c12e | HISTORICAL — pacote D05/D06 anterior |
| e3d45c4713022b61517f61fa27a672a9b4c3f9b73d218041726903f2bf7426c1 | HISTORICAL — hash órfão citado no D05 anterior; NÃO é o matrix atual |

## Evidência regenerada neste execution lineage

| Artefato | Caminho | SHA256 |
|---|---|---|
| matrix.json | docs/cupuwa/w05_evidence/matrix.json | 72ba8cb0be9647a2703fa59d97ff5f41a5037a49f627af1e71edf1aa1d4dcb49 |
| D04 | docs/cupuwa/W05-D04-OCS-EXECUTION-PROBES.md | 5a58ba5732c2d9d6216c3ed6ef62de3b6ffd81f333999a24d51283b1c660f6e5 |
| pytest.log | docs/cupuwa/w05_evidence/pytest.log | 72f696e6c515884b061dcfa255ef16592a6e9a454ad5f8f33c2a316da2da8eab |
| ruff.log | docs/cupuwa/w05_evidence/ruff.log | 82b3e6a6c090a57601d22943bd23fca9218d1031dbe5a7b754092f9a156b4f18 |
| mypy.log | docs/cupuwa/w05_evidence/mypy.log | 5d4b6d285b77932e3d08212c3b4974d0a803f98ec60408ac6ccf6a063fa6c19e |
| execution_meta.txt | docs/cupuwa/w05_evidence/execution_meta.txt | 6638df2944ac88718a23d2adec8917bd511730a56d73b3c256a90e45313d468d |

## Execução

- timestamp UTC: 2026-09-21T04:47:51Z
- command: pytest -q --noconftest tests/test_cupuwa_d04_ocs_execution_probes.py
- exit: 0
- result: 2 passed, 1 warning
- ruff check tests/test_cupuwa_d04_ocs_execution_probes.py — exit 0
- mypy tests/test_cupuwa_d04_ocs_execution_probes.py — exit 0

Ruff/Mypy são evidência suplementar e não alteram classificação de OCS.

## Classificação (inalterada)

| Grupo | n | Estado |
|---|---:|---|
| Canônicas | 72 | PARTIAL |
| COI local exercised | 25 | PARTIAL |
| Sem prova de execução COI | 47 | PARTIAL |
| PROVEN | 0 | — |

PROMOTION = NONE
MERGE = NONE
AUTHORITY_EXPANSION = NONE
