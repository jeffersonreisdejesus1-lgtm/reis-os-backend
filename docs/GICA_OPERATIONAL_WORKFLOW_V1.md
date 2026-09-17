# GICA — fluxo operacional de desenvolvimento v1

Este documento define como usar o GICA em cada incremento de software da REIS OS.
Ele transforma o GICA em um procedimento repetível de engenharia e evidência.

## Comando de entrada

Use:

> Desenvolver este incremento usando o GICA.

O comando não autoriza merge, publicação, gasto, alteração irreversível ou expansão de autoridade.

## Fluxo obrigatório

```text
INTENT
→ SCOPE
→ PLAN
→ IMPLEMENT
→ REVIEW
→ TEST
→ BUILD
→ RUN
→ EVIDENCE
→ QUALIFY
→ NEXT_INCREMENT
```

## Registro mínimo do incremento

Cada execução deve registrar:

- `INTENTION_ID` — identificador da intenção;
- `PROGRAM` — produto ou sistema afetado;
- `BRANCH` — branch autorizada;
- `HEAD_BEFORE` — commit inicial;
- `SCOPE` — o que será alterado;
- `EXECUTOR` — responsável pela implementação;
- `REVIEWER` — responsável pela revisão;
- `TEST_RESULT` — testes executados e resultado;
- `BUILD_RESULT` — build executada e resultado;
- `RUNTIME_RESULT` — comportamento observado, quando aplicável;
- `EVIDENCE` — logs, screenshots, APKs ou relatórios;
- `HEAD_AFTER` — commit final;
- `DECISION` — `PASS`, `HOLD` ou `REPAIR`.

## Regras de promoção

```text
SOURCE_CHANGED ≠ COMPILES
COMPILES ≠ TEST_PASS
TEST_PASS ≠ RUNTIME_PASS
RUNTIME_PASS ≠ PRODUCT_PASS
PRODUCT_PASS ≠ PUBLISHED
```

Cada estado exige sua própria evidência. Teste ignorado, build não executada ou resultado presumido não pode ser declarado como sucesso.

## Papéis operacionais

- `NÓESIS`: recebe a intenção, define escopo e roteia o incremento;
- `DÉDALA`: define arquitetura e fronteiras;
- `ÍRIS`: revisa UX e interface;
- `SOFIA`: implementa o código;
- `SYNERGEIA`: executa ambiente, testes, build e coleta de evidências;
- `ÁGORA`: qualifica o resultado;
- `SÝNESIS`: realiza assurance independente quando exigido.

Para alterações pequenas, o fluxo pode ser reduzido para `SCOPE → IMPLEMENT → TEST → BUILD → EVIDENCE`. Para alterações sensíveis, o fluxo completo é obrigatório.

## Decisões

- `PASS`: critérios do incremento comprovados;
- `HOLD`: falta ambiente, credencial ou evidência;
- `REPAIR`: existe falha identificada e o incremento retorna à implementação.

Nenhum PASS promove automaticamente o produto, inicia outro gate ou autoriza merge.

## Aplicação ao CUPUWA

O CUPUWA é o primeiro caso-piloto material do GICA. Seus incrementos devem vincular intenção, alteração de código, testes, build e evidência ao mesmo HEAD. O GICA acompanha o desenvolvimento desde o início; não é utilizado apenas na etapa final.

## Limites

- não usar o GICA para criar burocracia em correções triviais;
- não substituir engenharia, testes ou build por handoffs;
- não declarar integração externa sem implementação real;
- não fazer merge ou publicação sem autorização explícita;
- preservar o histórico e registrar divergências.

