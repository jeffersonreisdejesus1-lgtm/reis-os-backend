# W05 D05 — Pacote consolidado de evidências das OCSs

Procedimento: CUPUWA-OCS-INDIVIDUAL-QUALIFICATION-001
Branch: cupuwa/ocs-individual-qualification-001
BOUND_HEAD: da1b582a61d75f221782c01f1e80c4d8eaac5bac

## Evidência de execução

| Artefato | Referência |
|---|---|
| Probes D04 | tests/test_cupuwa_d04_ocs_execution_probes.py |
| Relatório D04 | docs/cupuwa/W05-D04-OCS-EXECUTION-PROBES.md |
| D04 HEAD | da1b582a61d75f221782c01f1e80c4d8eaac5bac |
| Pytest | 2 passed |
| Ruff | PASS |
| Mypy | PASS |
| pytest.log | 9ba2778c0a4b9217578c48c9e5f2851c7a4397c2c6733cec5bd562fcb6dea5cb |
| ruff.log | 82b3e6a6c090a57601d22943bd23fca9218d1031dbe5a7b754092f9a156b4f18 |
| mypy.log | 5d4b6d285b77932e3d08212c3b4974d0a803f98ec60408ac6ccf6a063fa6c19e |
| matrix.json | fd4abdf0c07a54c93fc2e49552140b3af3204550d4f928bb2849fa7f2470b732 |

Os hashes acima são referências reportadas pelo handoff de execução. Os arquivos físicos dos logs não foram re-hashados neste ambiente.

## Resultado consolidado

| Grupo | Quantidade | Resultado |
|---|---:|---|
| OCSs no inventário | 72 | registradas |
| OCSs percorridas em série | 72 | probe de identidade/capability/envelope |
| OCSs com assignment COI | 25 | execução local controlada |
| OCSs sem assignment COI | 47 | sem prova de execução |
| OCSs PROVEN | 0 | nenhuma |
| OCSs PARTIAL | 72 | todas |
| OCSs NOT_PROVEN | 0 | não aplicável ao status agregado; lacunas individuais permanecem |

## Limite semântico

A execução controlada das 25 OCSs demonstra o caminho local COI → capability → procedimento local → receipt dentro do teste. Não demonstra:

- execução da fisiologia própria da OCS;
- worker ou agente externo;
- efeito material no CUPUWA;
- runtime institucional completo;
- compatibilidade individual das 72 OCSs;
- enforcement universal para todas as OCSs.

As 47 identidades sem assignment COI não herdam os resultados das 25.

## Estado de governança

D01 = PASS_WITH_LIMITS
D02 = PASS_WITH_LIMITS
D03 = PASS_WITH_LIMITS
D04 = PASS_WITH_LIMITS
D05 = PASS_WITH_LIMITS
D06 = PENDING

PROMOTION = NONE
MERGE = NONE
AUTHORITY_EXPANSION = NONE

## Próximo passo

D06 deve consolidar a matriz final e encaminhar o pacote para ÁGORA. A qualificação independente deve aceitar, restringir ou rejeitar cada claim sem assumir que registro ou execução local equivale a fisiologia completa.
