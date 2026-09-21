# W06-P01 — Contrato de fisiologia individual da SOFIA

PROCEDURE: CUPUWA-OCS-OPERATIONALIZATION-001
INCREMENT: P01
PILOT_OCS: SOFIA
BRANCH: cupuwa/ocs-operationalization-001
BASE_HEAD: e09dc0c3312c925cdcb3efe547d27bb25560e4d1
STATUS: CONTRACT_DEFINED / EXECUTION_PENDING

## Justificativa da seleção

SOFIA foi selecionada como OCS-piloto porque sua especialidade declarada é implementação de software e seus resultados podem ser observados por arquivos, testes, commits e evidências.

A seleção não promove SOFIA, não amplia sua autoridade e não representa as outras 71 OCSs.

## Identidade fisiológica

- OCS: SOFIA
- Identity ref: identity://sofia
- Specialty: software_implementation_code_incremental_integration
- State namespace: state://sofia/r2-v0.1.0
- Memory namespace: memory://sofia/r2-v0.1.0
- Reference role: implementation_integration_adaptation_stress

Fontes:
- app/profile_bindings/profiles.py
- app/cognitive_physiology/local_profiles.py

## Capability permitida no P01

Capability de teste e implementação limitada ao escopo explícito da missão.

A capability não concede autoridade. A autoridade deve vir do envelope da missão e ser validada antes da execução.

## Entrypoint esperado

Mission
→ authority reference
→ capability resolution
→ OCS selection: SOFIA
→ physiology binding
→ bounded local executor
→ result
→ receipt

## Probes obrigatórios

P01-S01 — identidade correta:
SOFIA resolve sua própria identidade sem assumir identidade de outra OCS.

P01-S02 — namespace:
estado e memória apontam para namespaces próprios e distintos.

P01-S03 — especialidade:
a capability resolvida é compatível com implementação de software.

P01-S04 — autoridade ausente:
sem authority_ref, a execução falha fechada.

P01-S05 — capability incompatível:
capability fora da especialidade ou da missão é recusada.

P01-S06 — handoff:
handoff fornece contexto e evidência, mas não transfere autoridade.

P01-S07 — receipt:
resultado inclui OCS, missão, capability, autoridade referenciada e digest.

P01-S08 — recuperação:
estado e receipt podem ser lidos novamente sem transformar replay em nova execução.

## Critério de PROVEN

SOFIA só poderá ser marcada PROVEN no P01 se houver:

- implementação material do binding fisiológico;
- testes P01-S01 a P01-S08;
- receipt verificável;
- readback/recovery;
- qualificação independente da ÁGORA;
- assurance da SÝNESIS quando exigida.

Caso contrário, o estado permanece PARTIAL.

## Proibições

- não generalizar SOFIA para as outras OCSs;
- não criar OCS ou runtime paralelo;
- não ativar as 72;
- não promover Skill;
- não criar worker externo neste incremento;
- não produzir efeito material no CUPUWA;
- não fazer merge ou promoção.

## Próximo handoff

NÓESIS → SOFIA

Objeto: implementar e testar somente o binding fisiológico individual da SOFIA conforme P01-S01 a P01-S08.
