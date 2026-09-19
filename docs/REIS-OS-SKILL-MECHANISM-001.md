# REIS-OS-SKILL-MECHANISM-001

## Estado

`PLANNED_INCREMENT`  
`IMPLEMENTATION = NOT_STARTED`  
`AUTHORITY_EXPANSION = NONE`

## Objetivo

Provar um mecanismo institucional mínimo de skills reutilizáveis, sem
confundir skill com OCS, handoff, memória privada ou autoridade.

## Piloto

`OCS = SOFIA`  
`SKILL_ID = SOFTWARE-TEST-QUALIFICATION`  
`VERSION = 1.0.0`

## Componentes do mecanismo

- `SkillRecord`;
- `SkillRegistry`;
- `CapabilityResolver`;
- `SkillSelector`;
- `AuthorityCheck` separado;
- `SkillReceipt`;
- `SkillCandidate`;
- persistência e readback após restart.

## Experimentos obrigatórios

### Skill existente

Localizar, carregar, verificar autoridade separadamente, executar, produzir
evidência, reiniciar o runtime e localizar novamente sem depender da memória
do processo.

### Skill inexistente

Retornar `NOT_FOUND`, gerar `SkillCandidate`, não registrar automaticamente,
validar em fronteira separada e somente depois permitir estado `AVAILABLE`.

## Limites

- não criar catálogo grande;
- não ativar as 72 OCS simultaneamente;
- não alterar a fisiologia universal;
- não conceder autoridade por meio do registry;
- não criar conhecimento institucional silenciosamente;
- não integrar imediatamente todas as skills ao CUPUWA.

## Sequência de governança

`SOFIA IMPLEMENTA → TESTES LOCAIS → COMMIT/PUSH → ÁGORA QUALIFICA → SÝNESIS ASSURA SE NECESSÁRIO → NÓESIS RECONCILIA`

`OCS != SKILL OWNER`  
Skills são patrimônio institucional versionado da REIS OS.
