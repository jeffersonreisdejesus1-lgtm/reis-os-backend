# W05 — Inventário-base de qualificação individual das OCSs

**Procedimento:** CUPUWA-OCS-INDIVIDUAL-QUALIFICATION-001  
**Branch:** cupuwa/ocs-individual-qualification-001  
**HEAD vinculado:** f3a175568be622c6f6edbee8310a45c659111b17  
**Estado:** D01 concluído; qualificação individual pendente.

## Resultado executivo

O repositório distingue corretamente três conjuntos:

| Conjunto | Quantidade | O que prova | Estado |
|---|---:|---|---|
| Pool canônico | 72 | Identidades previstas para seleção dinâmica | ARCHITECTURAL_POOL_ONLY |
| Perfis registrados | 30 | Perfis materialmente registrados no escopo da reconciliação | REGISTERED_IN_TESTED_SCOPE |
| Fisiologia documentada | 11 | Perfis locais de fisiologia explicitamente definidos | PHYSIOLOGY_DOCUMENTED_IN_SCOPE |

Essas quantidades não são intercambiáveis. Registro não prova runtime; fisiologia documentada não prova execução; presença no pool não prova qualificação individual.

## Fontes materiais

| Evidência | Arquivo | Conteúdo |
|---|---|---|
| Registro canônico | app/profile_bindings/canonical_registry.py | Compõe e valida o registro canônico; contrato exige 72 identidades |
| Perfis-base | app/profile_bindings/profiles.py | Estrutura OCSProfile, identidade, especialidade, capacidades e envelope |
| Perfis visuais | app/profile_bindings/cupuwa_visual_profiles.py | 19 perfis adicionais do pacote visual |
| Perfis mobile/fullstack | app/profile_bindings/mobile_fullstack_profiles.py | 42 especialistas adicionais, autoridade neutra |
| Fisiologia local | app/cognitive_physiology/local_profiles.py | 11 perfis locais com identidade, namespaces e papel de referência |
| Composição | app/cognitive_validation/ocs_composition.py | Regras de composição e seleção por capacidade |
| Reconciliação | docs/cupuwa/CUPUWA-OCS-RECONCILIATION-001.md | Registro institucional dos números 72/30/11 e dos limites |

## Matriz inicial de estado

| Propriedade | Resultado atual | Classificação |
|---|---|---|
| Identidade no pool canônico | Declarada pelo registro | DECLARED |
| Perfil material registrado | Demonstrado para o conjunto registrado | PARTIAL para cobertura individual |
| Fisiologia explícita | Demonstrada para 11 perfis locais | PARTIAL |
| Capability binding individual | Não qualificado para as 72 | NOT_PROVEN |
| Host disponível por OCS | Não qualificado individualmente | NOT_PROVEN |
| Runtime binding por OCS | Não qualificado individualmente | NOT_PROVEN |
| Runtime enforcement por OCS | Não qualificado individualmente | NOT_PROVEN |
| Execução material por OCS | Não qualificado individualmente | NOT_PROVEN |
| Receipts/evidências por OCS | Não qualificado individualmente | NOT_PROVEN |

## Regra de classificação

Nenhuma OCS será marcada como PROVEN apenas por:

- estar incluída no pool de 72;
- possuir um perfil no registro;
- possuir especialidade declarada;
- aparecer em documentação;
- ser selecionável por uma composição.

Para PROVEN, será necessária evidência individual vinculada a identidade estável, código/HEAD, testes, runtime entrypoint e resultado observável. Na ausência disso, o estado é PARTIAL ou NOT_PROVEN.

## Pendências D02–D06

1. Emitir a lista canônica completa das 72 identidades com fonte e namespace.
2. Associar cada identidade a fisiologia, capabilities, envelope de autoridade e entrypoint.
3. Executar testes individuais ou por família, sem transformar teste de família em prova automática de cada OCS.
4. Produzir receipts/evidências por identidade.
5. Qualificar independentemente a matriz.
6. Manter sem promoção as OCSs sem evidência suficiente.

## Conclusão do D01

O baseline material está consolidado:

72 é o pool arquitetural; 30 é o registro material reconciliado; 11 é a fisiologia local documentada. A cobertura individual das 72 permanece não comprovada.

D01 = PASS_WITH_LIMITS  
D02–D06 = PENDING  
PROMOTION = NONE  
AUTHORITY_EXPANSION = NONE
