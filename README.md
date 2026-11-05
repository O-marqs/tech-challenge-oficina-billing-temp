# Billing Service — Fase 4

Responsável: Lucas Marques. Grupo 47 — Tech Challenge Oficina.

**Estado em 05/11/2026: documentação inicial; serviço ainda não implementado.**
Este conjunto registra o plano para construir o Billing e integrar a autenticação existente.
Código presente em outros repositórios não significa que a integração completa esteja validada.

Repositório de trabalho temporário: [O-marqs/tech-challenge-oficina-billing-temp](https://github.com/O-marqs/tech-challenge-oficina-billing-temp),
branch `docs/fase4-lucas-planejamento`. Criado com autorização explícita do Lucas em 05/11/2026.
Destino final: [Billing do grupo](https://github.com/helyomendesdev/tech-challenge-oficina-billing).
A escrita no destino foi recusada com HTTP 403; o destino permanece inalterado por esta sessão.
[Confluence — hub do Lucas](https://marqs.atlassian.net/wiki/spaces/~7120204dc1d32324e343dcad205794dd624c7c/pages/26247169/Tech+Challenge+Fase+4+Lucas+Billing+Mercado+Pago+e+JWT)
serve de índice; os arquivos versionados nesta branch passam a ser a referência atual de desenvolvimento.

## Por onde começar

1. [Continuidade e próxima tarefa](docs/08-continuidade.md).
2. [Auditoria dos repositórios e evidências](docs/01-auditoria.md).
3. [Escopo, responsáveis e requisitos](docs/02-escopo-requisitos.md).
4. [Arquitetura proposta](docs/03-arquitetura.md).
5. [Contratos e dependências de integração](docs/04-contratos-integracao.md).
6. [Plano de entregas e critérios de aceite](docs/05-plano-entregas.md).
7. [Desenvolvimento local e custos](docs/06-operacao-custos.md).
8. [Decisões e perguntas pendentes](docs/07-decisoes-pendencias.md).
9. [Registro de trabalho](docs/09-registro.md).
10. [Repositório temporário e migração ao destino](docs/10-migracao-github.md).

Agentes devem ler [AGENTS.md](AGENTS.md) antes de alterar qualquer coisa.

## Divisão vigente

| Pessoa | Responsabilidade |
|---|---|
| Hélio | OS Service, orquestrador, template de CI/CD e proteção das branches |
| Lucas | Billing, orçamento, pagamento, Mercado Pago, integração de JWT |
| Sophia | Execution, NoSQL, infraestrutura, Terraform e mensageria |
| Luís | Contratos da Saga, tracing distribuído e BDD ponta a ponta |

## Direção técnica inicial

Python 3.11, FastAPI, PostgreSQL exclusivo do Billing, SQLAlchemy/Alembic,
SQS FIFO compatível com o contrato existente, inbox/outbox transacionais,
JWT RS256 compatível com `-auth`. São decisões locais de planejamento, ainda sem implementação.
Pagamento antes da execução e Saga orquestrada no OS já vêm do contrato compartilhado.

Primeiro desenvolver e testar sem conta de nuvem, sem pagamento real e sem serviços contratados.
O adaptador simulado servirá aos testes; a entrega exige também integração efetiva com o
ambiente de testes do Mercado Pago, com evidências próprias.

Não há aplicação executável, dependências instaláveis, Dockerfile, migrations,
pipeline do Billing ou cobertura medida nesta entrega documental.
