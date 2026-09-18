# CUPUWA P0 Core Finance — Material Mission Contract

MISSION_ID = CUPUWA-P0-CORE-FINANCE-MATERIAL-001
PROGRAM = CUPUWA
MISSION_CLASS = MATERIAL_PRODUCT_BUILD
CONDUCTOR = NÓESIS
AUTHORITY = FOUNDER
FAIL_CLOSED = TRUE

## Mission
Construir e qualificar o primeiro núcleo financeiro material, robusto e utilizável do CUPUWA para Android, usando a infraestrutura existente da REIS OS e composição dinâmica das OCS necessárias.

## Product objective
Entregar um aplicativo financeiro local-first capaz de manter estado financeiro consistente, sobreviver a reinícios e oferecer experiência suficientemente completa para operação financeira pessoal cotidiana.

## Required product capabilities
- onboarding local sem conta obrigatória
- perfil local
- múltiplas contas financeiras
- saldo inicial
- receitas e despesas
- transferências entre contas
- categorias
- histórico de movimentações
- busca e filtros
- edição e exclusão seguras
- recorrências básicas
- dashboard financeiro consolidado
- calculadora monetária brasileira
- persistência local e funcionamento offline
- recuperação integral após reinício
- tratamento de erros e estados vazios
- acessibilidade básica
- inteligência financeira local determinística
- resumo financeiro do período
- identificação de padrões/tendências
- insights explicáveis

## Financial integrity
O saldo deve ser derivável de ledger consistente, não um número independente. Transferências preservam relação origem/destino. Alterações não podem criar ou destruir valor silenciosamente. Valores monetários exigem representação segura. Persistência e reconstrução devem produzir estado financeiro observável equivalente.

## Architectural requirements
Local-first; offline-first; separação domínio/persistência/apresentação; banco local versionado; migração explícita; estado reconstruível; componentes testáveis; nenhuma dependência externa obrigatória; evolução posterior de IA; nenhuma duplicação de COI, Orchestrator, Factory ou runtime.

## REIS OS execution path
FOUNDER → NÓESIS → COI → capability discovery → dynamic OCS composition → governed runtime → Orchestrator → specialized workers → Factory → material Android effect → receipts/evidence → qualification.

## OCS policy
POOL_AVAILABLE = 72.
A missão não fixa antecipadamente quantidade de OCS. COI seleciona somente OCS elegíveis por capacidade. Seleção não concede autoridade. Workers recebem envelope limitado à operação atribuída.

## Economic policy
FREE_FIRST = TRUE
CREDITS_FIRST = TRUE
ZERO_NEW_SPEND_BY_DEFAULT = TRUE
EXECUTION_PRIORITY = Render → CodeMagic para mobile/build Android → GitHub Actions somente quando necessário.
Nenhum gasto novo, upgrade ou overage é autorizado implicitamente.

## Material exit criteria
Em ambiente Android limpo: instalar/abrir; onboarding; perfil; múltiplas contas; saldos iniciais; receitas/despesas; transferência; categorização; edição; exclusão sem corrupção do ledger; recorrência; histórico/filtros; dashboard; resumo/insights; encerramento completo; restart; recuperação equivalente; continuidade offline.

## Qualification requirements
Testes de domínio financeiro; invariantes monetárias; transferências; edição/exclusão; recorrências; persistência; restart/reconstruction; migração do banco; regressão Android; evidência da seleção das OCS; receipts da execução governada; evidência do artefato material; APK instalável; AAB quando requerido pela distribuição.

## HOLD conditions
Inconsistência financeira; perda de estado; corrupção após restart; capability sem OCS elegível; autoridade insuficiente; receipt ausente/inválido; efeito material não verificável; gasto não autorizado; evidência insuficiente.

## Out of scope P0
Integração bancária real; custódia financeira; movimentação de dinheiro real; Google Sign-In obrigatório; WhatsApp; publicação definitiva Play Store; compra automática de infraestrutura; expansão de autoridade; alteração do GICA.

## Success semantics
P0 não obtém PASS porque o código existe ou o APK compila. PASS somente após produto material + invariantes financeiras + persistência/restart + evidências do runtime + qualificação correspondente.
