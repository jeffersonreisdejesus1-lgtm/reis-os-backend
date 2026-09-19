# REIS-OS-MATERIAL-BASELINE-001

## Estado

`ACTIVE_BASELINE`  
`PURPOSE = INVENTORY_BEFORE_INTEGRATION`  
`AUTHORITY_EXPANSION = NONE`  
`GICA = FROZEN`

## Regra de classificação

- `PROVEN`: código e execução/teste/evidência vinculados ao escopo declarado.
- `PARTIAL`: existe implementação ou evidência, mas falta uma prova necessária.
- `NOT_PROVEN`: arquitetura, proposta ou evidência insuficiente para afirmar funcionamento.

## Inventário canônico

| Componente | Evidência material | Estado | Limite |
|---|---|---|---|
| GICA core contracts/gates | Código e commits recuperados | PROVEN | GA0/GA1 históricos não provados |
| GICA GA2–GA5 | Receipts e requalificações registradas | PROVEN | Escopos próprios dos gates |
| GICA GA6 | Remediação e qualificação do slice registradas | PROVEN | Não autoriza GA7 ou GA8 |
| GICA GA7 | Contratos e preparação institucional | NOT_PROVEN | Execução/qualificação não concluídas |
| GICA GA8 | Não iniciado | NOT_PROVEN | Fora do escopo atual |
| COI/substrato multi-OCS | Código, 72 OCS registradas, composição testada | PROVEN | Não prova runtime institucional completo |
| Worker material NÓESIS DR1 | Processo separado, checkpoint, isolamento, 6/6 grupos | PROVEN | Não prova 11 OCS ou cognição distribuída |
| Factory | Componentes e testes existentes; primeira camada CUPUWA | PARTIAL | Falta fechamento isolado e qualificação completa |
| Recursive Engine | Componentes existentes em runtime | PARTIAL | Falta prova consolidada de restart/replay no caminho integrado |
| MaterialPlane | Componentes e evidências parciais | PARTIAL | Falta prova vertical completa de efeito e recovery |
| Orchestrator/workers/Factory CUPUWA P0 | HEAD `b5c3405e545c84f857cfe6a6785c2aeea543d2a4`, 17 testes, Ruff/Mypy | PARTIAL | Não prova integração REIS OS ponta a ponta |
| CUPUWA Android | APK/AAB e builds CodeMagic anteriores | PROVEN | Build não equivale a produto publicado |
| CUPUWA como consumidor do runtime REIS OS | Não demonstrado | NOT_PROVEN | Requer missão vertical integrada |
| Runtime multi-OCS completo | Não demonstrado | NOT_PROVEN | DR2+ ainda não concluídos |
| Economia institucional | Especificações e arquitetura | NOT_PROVEN | Sem runtime econômico funcional |

## Próxima sequência

1. Fechar Factory isoladamente.
2. Fechar Recursive Engine isoladamente.
3. Fechar MaterialPlane isoladamente.
4. Executar `REIS-OS-INTEGRATED-MISSION-001` com uma alteração real do CUPUWA.
5. Testar interrupção, restart, reconciliação e ausência de duplicação.
6. Submeter a ÁGORA e SÝNESIS.

## Proibições

Este baseline não declara integração completa, não promove estado, não autoriza merge, não inicia GA7/GA8 e não altera o GICA congelado.
