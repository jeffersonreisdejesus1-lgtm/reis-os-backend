# W06 — OCS Operationalization

PROCEDURE_ID: CUPUWA-OCS-OPERATIONALIZATION-001
PROGRAM: REIS OS / CUPUWA
BASE_CLOSED_PROCEDURE: CUPUWA-OCS-INDIVIDUAL-QUALIFICATION-001
BASE_HEAD: 61e6933469a7ea9fa0dfb9a9ed52bc1c1fc0ca81
BRANCH: cupuwa/ocs-operationalization-001
STATUS: OPEN / P01_NOT_STARTED

## Objetivo

Transformar evidência parcial de identidade e perfil em prova operacional específica, sem reabrir W05 e sem considerar o conjunto de 72 OCSs operacional por herança coletiva.

## Sequência

### P01 — Fisiologia individual

Para cada OCS selecionada, definir e provar:
- identidade fisiológica;
- especialidade;
- estado e memória próprios;
- limites;
- política de parada;
- recuperação;
- entrypoint material;
- receipt de execução.

### P02 — Host availability

Verificar se o host disponibiliza os primitives exigidos à OCS:
- leitura de contexto;
- execução autorizada;
- persistência;
- observação de estado;
- retorno de resultado;
- limites de autoridade.

### P03 — Runtime binding

Ligar fisiologia e capabilities ao fluxo COI/Orchestrator:
mission → authority → capability → OCS → runtime.

### P04 — Runtime enforcement

Provar que o runtime exige os vínculos e falha fechado quando:
- autoridade falta;
- capability não pertence à missão;
- OCS não é compatível;
- entrypoint não existe;
- evidência não pode ser produzida.

### P05 — Execução material

Executar uma tarefa real e limitada por OCS, com:
- entrada;
- ação;
- resultado;
- receipt;
- readback;
- ausência de efeito não autorizado.

### P06 — Worker/agente externo

Somente após P01–P05:
- executor externo real;
- identidade do worker;
- estado observável;
- resultado;
- recovery;
- idempotência;
- receipt de dispatch.

### P07 — Efeito material no CUPUWA

Uma missão concreta deve atravessar o runtime e produzir alteração verificável no CUPUWA, com qualificação e assurance próprias.

## Governança

- uma OCS ou família por vez;
- não ativar as 72 simultaneamente;
- resultado de uma OCS não é herdado pelas demais;
- capability não concede autoridade;
- receipt não concede autoridade;
- Skill não é OCS;
- nenhum efeito externo sem autoridade e evidência;
- nenhum merge ou promoção automática.

## Critério de conclusão

W06 só pode ser encerrado quando os incrementos aplicáveis tiverem:
- contrato;
- implementação;
- testes;
- evidência;
- qualificação da ÁGORA;
- assurance da SÝNESIS quando exigida.

## Próximo objeto

W06-P01 — Fisiologia individual da primeira OCS selecionada.

A primeira OCS deve ser escolhida por capacidade e necessidade da missão, não por ativação do roster inteiro.

W05 permanece fechado:
ASSURED_WITH_BOUNDED_SCOPE
