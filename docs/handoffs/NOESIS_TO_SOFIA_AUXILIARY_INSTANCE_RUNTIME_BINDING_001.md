# Handoff — Auxiliary Instance Runtime Binding 001

`HANDOFF_ID = NOESIS-TO-SOFIA-AUXILIARY-INSTANCE-RUNTIME-BINDING-001`

## Origem e destino

- `SOURCE_OCS = NÓESIS`
- `TARGET_OCS = SOFIA`
- `HANDOFF_CLASS = RUNTIME_GAP_REMEDIATION_IMPLEMENTATION`
- `IMPLEMENTATION_OWNER = SOFIA`
- `QUALIFICATION_OWNER = ÁGORA`
- `ASSURANCE_OWNER = SÝNESIS`
- `FOUNDER_RESERVED_AUTHORITY = PRESERVED`

## Missão

Materializar o menor caminho governado que permita a uma OCS solicitar,
observar e recuperar uma instância auxiliar real, reutilizando a infraestrutura
existente da REIS OS.

`MISSION_ID = AUXILIARY-INSTANCE-RUNTIME-BINDING-MISSION-001`

## Classificação da lacuna

`GAP_CLASSIFICATION = D + B + A`

- **D — PARTIAL_EXISTING_PRIMITIVE:** existem mecanismos de instâncias,
  workers, handoffs, receipts e recovery, mas não há um contrato único de
  spawn/replay/recovery cobrindo o caminho completo.
- **B — RUNTIME_BINDING_GAP:** os mecanismos do repositório não estão ligados
  ao fluxo real da OCS conversacional.
- **A — HOST_EXPOSURE_GAP:** nesta execução, o host não expôs à OCS a
  primitive de criação/observação/resultado.

Não classificar como `C — MISSING_PRIMITIVE` sem demonstrar que a infraestrutura
existente não pode ser adaptada.

## Infraestrutura existente a reutilizar

| Objeto | Localização | Reuso esperado |
|---|---|---|
| Fisiologia e gerações | `app/cognitive_physiology/runtime.py` | validação de geração e commit |
| Binding institucional | `app/cognitive_physiology/binding.py` | identidade, namespaces e autoridade referenciada |
| Contratos de instância | `app/ocs_instances/contracts.py` | `InstanceBinding`, estados e hashes |
| Store de instâncias | `app/ocs_instances/store.py` | persistência, transições e idempotência existente |
| Serviço de binding | `app/ocs_instances/service.py` | preparação/ativação/recovery |
| Recovery | `app/ocs_instances/recovery.py` | reentrada e validação de continuidade |
| Bridge externo | `app/ocs_instances/work_bridge.py` | anexar receipt externo; não simular spawn |
| Worker material | `app/distributed_runtime/worker.py` | processo separado, snapshot, checkpoint e lifecycle |
| Pair/pipeline workers | `app/distributed_runtime/pair.py`, `pipeline.py` | handoff e execução entre OCS autorizadas |
| Receipts | `app/universal_kernel/contracts.py`, `app/cognitive_validation/*` | proveniência, ação, missão e handoff |

## Estratégia arquitetural

`IMPLEMENTATION_STRATEGY = ADAPTER`

Criar um adaptador governado sobre os mecanismos existentes. Não criar COI,
Orchestrator, Factory, ledger ou worker paralelo.

Interface conceitual mínima:

```text
spawn_instance(
  parent_mission_id,
  requesting_ocs,
  target_capability,
  bounded_task,
  authority_context,
  operation_id,
) -> SpawnResult
```

O resultado deve conter `instance_id`, `parent_mission_id`, `execution_state`,
`result_reference` e `receipt_reference`.

## Invariantes obrigatórios

- `CAPABILITY != AUTHORITY`.
- A autoridade da instância filha nunca excede o escopo autorizado.
- Não existe autoautorização nem amplificação de autoridade.
- `operation_id + parent_mission_id + authorized_scope` identifica uma única
  operação canônica.
- Replay idêntico retorna a operação existente; não cria segunda instância.
- Payload divergente com a mesma identidade falha fechado como conflito.
- Após restart, a decisão vem de estado durável, não de cache de processo.
- Resultado incerto exige reconciliação antes de qualquer retry.
- Nenhuma transição relevante fica apenas em memória.
- Nenhum sucesso é declarado sem receipt verificável.

## Estados e receipts

Estados mínimos: `CREATED`, `RUNNING`, `SUCCEEDED`, `FAILED`.

Quando aplicável: `INTERRUPTED`, `RECOVERING`, `RECONCILED`.

Receipts mínimos:

- `SPAWN_RECEIPT`
- `EXECUTION_RECEIPT`
- `RESULT_RECEIPT`
- `RECOVERY_RECEIPT`

Cada receipt deve vincular `instance_id`, `operation_id`, `parent_mission_id`,
`requesting_ocs`, autoridade, transição de estado, evidência e timestamp.

## Testes de aceitação

### Positivos

`P01` primeiro spawn cria exatamente uma instância.  
`P02` `instance_id` material é retornado.  
`P03` estado é consultável.  
`P04` resultado é recuperável.  
`P05` receipts são persistidos.  
`P06` estado é reconstruído após restart.

### Negativos e idempotência

`N01` spawn sem autoridade: fail-closed, sem instância.  
`N02` child scope superior: fail-closed, sem instância.  
`N03` replay idêntico: mesma instância canônica.  
`N04` mesma operação com payload divergente: `IDEMPOTENCY_CONFLICT`.  
`N05` replay após restart: recuperação canônica, sem duplicata.  
`N06` interrupção entre efeito e confirmação: reconcile-first.  
`N07` instância desconhecida: sem resultado sintético.  
`N08` falha do worker: `FAILED` persistido e failure receipt.  
`N09` concorrência duplicada: uma instância e um efeito canônicos.

## Proibições

- Não alterar a fisiologia universal.
- Não promover Skills.
- Não criar subsistema paralelo.
- Não fazer merge ou promoção automática.
- Não usar CodeMagic como ambiente de desenvolvimento; build/rebuild permanece
  separado da implementação e qualificação.
- Não declarar PASS.

## Pacote de retorno SOFIA → ÁGORA

SOFIA deverá retornar:

- exact implementation HEAD;
- arquivos e símbolos alterados;
- decisão `REUSE`, `ADAPTER` ou `NEW_PRIMITIVE` justificada;
- resultados individuais `P01–P06` e `N01–N09`;
- evidências de persistência, replay, concorrência e recovery;
- receipts e hashes;
- prova de não amplificação de autoridade;
- claims provados, não provados e riscos residuais.

Após isso: `SOFIA → ÁGORA → SÝNESIS`.

## Estado deste handoff

`HANDOFF_STATUS = ISSUED`  
`IMPLEMENTATION = PENDING_SOFIA`  
`QUALIFICATION = NOT_STARTED`  
`ASSURANCE = PENDING_SÝNESIS`  
`NO_SELF_PASS = TRUE`  
`NO_AUTOMATIC_PROMOTION = TRUE`  
`NO_AUTHORITY_EXPANSION = TRUE`  
`NO_PHYSIOLOGY_CHANGE = TRUE`

