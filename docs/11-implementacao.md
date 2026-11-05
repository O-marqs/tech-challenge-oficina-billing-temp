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
