# REIS OS Backend — Sprint 2

Monólito modular FastAPI da REIS OS Platform.

## Baseline implementado

- Sprint 0: fundação técnica;
- Sprint 1: identidade, organizações, memberships e auditoria;
- Sprint 2: workspaces, projetos, tarefas e transições de domínio.

## Executar com Docker

```bash
cp .env.example .env
docker compose up --build
```

O container da API executa `alembic upgrade head` antes de iniciar o Uvicorn.

- OpenAPI: `http://localhost:8000/docs`
- Health: `GET /health`
- Readiness: `GET /ready`

## Contexto organizacional

Após autenticar, envie o token e a organização selecionada em cada endpoint operacional:

```http
Authorization: Bearer <token>
X-Organization-ID: <organization-uuid>
```

A API valida uma membership `active` antes de acessar workspaces, projetos ou tarefas. Recursos de outra organização são tratados como inexistentes.

## Fluxo da Sprint 2

1. `POST /auth/register`
2. `POST /organizations`
3. `POST /workspaces`
4. `POST /projects`
5. `POST /projects/{id}/tasks`
6. `POST /projects/{id}/transition`
7. `POST /tasks/{id}/transition`

Atualizações e transições geram `AuditEvent` na mesma transação da alteração principal.

## Qualidade

```bash
pytest
ruff check app tests migrations
mypy app
```

Os testes cobrem regras de transição, fluxo operacional completo, auditoria, vínculo hierárquico e isolamento multi-organização.

## Quality Gate remoto

O workflow `.github/workflows/quality-gate.yml` executa o gate da Sprint 2 em
GitHub Actions com PostgreSQL 17. Ele aplica migrations do zero, executa Ruff,
Mypy, testes unitários e de integração, inicia a API e valida `/health` e
`/ready`.

Os testes de integração são identificados pelo marcador `integration` e usam
`TEST_DATABASE_URL`. Na pipeline, esse endereço aponta para o PostgreSQL do
service container; localmente, o fallback permanece SQLite em memória.

As evidências são publicadas no artefato `quality-gate-evidence`, incluindo
JUnit XML, cobertura, log da API e metadados da execução.
