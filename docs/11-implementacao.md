# Implementação inicial — evidências e limites

05/11/2026. Autorização do Lucas: acelerar o desenvolvimento autonomamente e deixar algo
executável para revisão ao final do trabalho. Decisões locais reversíveis foram adotadas
explicitamente; não houve alteração dos contratos/repos do grupo.

## Evidências locais iniciais

| Verificação | Resultado |
|---|---|
| Python 3.11.17 e ambiente isolado | Instalado; dependências fixadas em uv.lock |
| Domínio/aplicação/API/JWT/SQS e adapter MP mockado | 62 PASS, 3 testes PostgreSQL SKIP |
| Cobertura medida do código de serviço, sem CLI operacional | 96,98%; gate mínimo 80% |
| CLI operacional | Demonstração isolada executada via script e migrations; CLI não está no denominador da cobertura |
| Demonstração HTTP + DB + mensagens de resposta + compensação fake | PASS; não é BDD da stack real |
| Schemas normativos do grupo | 14 arquivos preservados e usados em todas as entradas/saídas Billing |
| Docker/PostgreSQL/K8s neste ambiente | Docker e PostgreSQL indisponíveis localmente; build e PostgreSQL serão verificados pelo CI |
| Auditoria de dependências local | Inconclusiva: timeout de rede PyPI; CI tem gate próprio, não declarar zero vulnerabilidades |
| Infra/cloud/MP real | Não executado; nenhuma contratação, transação ou deploy |

Há tests de rollback conjunto de inbox/estado/outbox, duplicata após reinício, messageId reutilizado
com conteúdo diferente, rejeição de JWT incorreto, ownership, schemas inválidos, confirmação verificada,
falha de provedor e chaves estáveis em retry. Há três testes adicionais de concorrência PostgreSQL,
sem substituí-los por SQLite.

## Decisões adotadas para acelerar

- Catálogo próprio local configurável; preços demo explicitamente sintéticos. Não acessar banco do OS.
- Link/estado por GET Billing, fora da Saga; sem nova mensagem incompatível.
- Aprovação/recusa têm como causa o messageId de OrcamentoGerado persistido no orçamento;
  requestId e trace context da Saga são preservados. Não inventar causationId nulo nem token de atendente.
- Total zero: rejeitar geração, emitindo OrcamentoFalhou; política pode ser revista pelo grupo.
- Provider fake é explícito e restrito a desenvolvimento/teste. Pagamento não é autoaprovado;
  simulação fica somente na CLI ou no teste, sem endpoint público de injeção de sucesso.
- Checkout Pro Orders foi escolhido para o adapter de teste; validação real ainda exige conta/credenciais.
- Resultado desconhecido de operação não gera PagamentoFalhou nem PagamentoEstornado.
- Notificações tardias e múltiplos pagamentos ficam visíveis como erro/intervenção, sem regra financeira inventada.

## Fontes primárias de implementação

- [Transações SQLAlchemy](https://docs.sqlalchemy.org/en/20/orm/session_transaction.html).
- [Testes FastAPI](https://fastapi.tiangolo.com/advanced/testing-events/).
- [Criar Checkout Pro Order](https://www.mercadopago.com.br/developers/pt/docs/checkout-pro-orders/create-order?scope=prod).
- [Consultar Order](https://www.mercadopago.com.br/developers/pt/reference/online-payments/checkout-pro/get-order/get).
- [Refund de Order](https://www.mercadopago.com.br/developers/pt/reference/online-payments/checkout-pro/refund-order/post).
- [Notificações Orders](https://www.mercadopago.com.br/developers/pt/docs/checkout-pro-orders/notifications?scope=prod).

## Não declarar concluído

Integração MP em ambiente de testes, BDD completo do grupo, envio/visualização de trace no New Relic,
identidade atendente, IAM/infra, branch protection, K8s/CD e migração ao repo do Hélio permanecem pendentes.
O compose Billing é de desenvolvimento e a demonstração exercita somente o participante Billing.

## CI já observado

- [Run 42109938228](https://github.com/O-marqs/tech-challenge-oficina-billing-temp/actions/runs/42109938228),
  commit `0a5b746c2d4e40081ab39d7eb9411122fbe72f68`: 65 PASS em PostgreSQL 16, sem SKIP,
  cobertura 96,98% (CLI ainda fora do denominador nesse commit). Ruff/Bandit, Alembic upgrade/check,
  demo, auditoria de dependências e build Docker passaram. Auditoria retornou “No known vulnerabilities found”.
- [Run 42110438914](https://github.com/O-marqs/tech-challenge-oficina-billing-temp/actions/runs/42110438914),
  commit `4a10bca5309344cad44d662525d43cc7563453f9`: além das verificações anteriores,
  `docker compose up` e smoke real entre API + workers + PostgreSQL + SQS LocalStack passaram.
  Observados OrcamentoGerado, OrcamentoAprovado, PagamentoConfirmado, PagamentoEstornado e OrcamentoCancelado,
  todos com a correlação esperada. Provider fake explícito; OS/Execution não participaram.
- Depois foram acrescentados oito testes da CLI, agora incluída na cobertura. Resultado local:
  70 PASS, 3 SKIP PostgreSQL, 96,66% sobre todo `billing_service`. Verificar run atual para resultado remoto.

Docker e PostgreSQL não foram executados no ambiente de edição; foram executados pelos runners do CI.
Não confundir auditoria automatizada de dependências com revisão de segurança completa.

- [Run 42110862161](https://github.com/O-marqs/tech-challenge-oficina-billing-temp/actions/runs/42110862161),
  commit `e7f668df37324c902a0140cc32cea73fb24d7bcf`: **73 PASS, sem SKIP**, cobertura **96,92%**,
  incluindo CLI. Os jobs tests e container passaram, incluindo migrações, auditoria de dependências
  e o fluxo entre containers com PostgreSQL/LocalStack. Este é o último commit funcional validado.

## Revisão adicional — estado atual

- Commit funcional `ebd919fb1826c088c51407d113657ec15f271377`,
  [run 42120591700](https://github.com/O-marqs/tech-challenge-oficina-billing-temp/actions/runs/42120591700):
  **93 PASS, sem SKIP, cobertura 97,25%** incluindo CLI, em Python 3.11/PostgreSQL 16.
  Tests e container passaram: Ruff/formato/Bandit, migrations/drift, demo, auditoria de dependências,
  build Docker e fluxo API/workers/PostgreSQL/SQS LocalStack. Auditoria: nenhuma vulnerabilidade
  conhecida encontrada nos pacotes consultados.
- Vinte regressões adicionais validam ID do pagamento e evidência de reembolso. Resposta
  parcial, pendente, sem evidência ou com moeda/transação/valor/ID divergente não libera compensação.
  O teste transacional confirma que não sai PagamentoEstornado nem se permite cancelar orçamento
  enquanto o provedor não comprova reembolso integral. A chave idempotente é preservada.
- Corrigido envio da URL de retorno em config.online (success_url/failure_url/pending_url).
  Webhook continua sendo configurado no painel Teste, conforme documentação oficial.
- Localmente: Python 3.12.14, 90 PASS, 3 SKIP PostgreSQL, 97,38%. Ambiente foi recriado após
  indisponibilidade do interpretador local anterior; não se atribui essa execução a Python 3.11.
- Limites anteriores permanecem. Roteiro e atribuições em
  [12-proximos-passos-e-alinhamentos.md](12-proximos-passos-e-alinhamentos.md).
