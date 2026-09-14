# CUPUWA — MVP Android local-first

CUPUWA é um app Android nativo de controle financeiro diário, separado do REIS OS Command.

## MVP 0.3.0

- saldo atual;
- entradas e saídas em BRL;
- resumo do dia;
- resumo e resultado do mês;
- histórico local;
- editar e excluir lançamentos;
- persistência offline no aparelho;
- interface Material;
- `applicationId = com.jsonsoftware.cupuwa`;
- sem permissão `INTERNET`.

## Build material

Workflow CodeMagic: `cupuwa-p0-material`.

A validação material deve executar testes unitários, lint e `assembleDebug`, publicar o APK e registrar SHA-256/evidência. A existência do código-fonte não equivale a build aprovada e a existência de APK não equivale a prova em dispositivo.

## Play Store

A baseline inclui artefatos preparatórios de privacidade e listing. Publicação, assinatura de produção, closed testing e produção permanecem gates externos e exigem evidência/credenciais próprias.
