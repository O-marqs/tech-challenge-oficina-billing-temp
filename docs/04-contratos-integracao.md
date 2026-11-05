# Contratos e integração

Fonte normativa: [contratos da Saga no SHA auditado](https://github.com/helyomendesdev/tech-challenge-oficina-saga/tree/ed3a8345ba684fc442193084ed7b8cbf72c3cdb9/contrato).
AsyncAPI identifica versão 1.1.0; mensagens mantêm `version: 1`.
README ainda recomenda tag v1.0.0: não assumir equivalência entre tag e main.
Na implementação, fixar dependência por referência imutável validada; evitar URL `main` flutuante.

## Mensageria obrigatória

Entrada: `oficina-billing-comandos.fifo`; saída: `oficina-os-saga-respostas.fifo`.
Há DLQs correspondentes; fila/redrive são coordenados com Sophia.
Envelope: `messageId`, `type`, `version`, `sagaId`, `osId`, `causationId`, `requestId`,
`occurredAt`, `payload`. Preservar datas RFC3339, UUIDs e osId inteiro conforme schema.
Usar FIFO por `sagaId` e dedupe por `messageId`; W3C apenas nos MessageAttributes.
Respostas exigem `causationId` UUID; não colocar null para ações iniciadas via HTTP.

| Comando consumido | Entrada essencial | Saída prevista do Billing |
|---|---|---|
| GerarOrcamento | clienteId, veiculoId, servicos e pecas com IDs/quantidades | OrcamentoGerado (orcamentoId, valorTotalCentavos, validoAte) ou OrcamentoFalhou |
| CancelarOrcamento | orcamentoId, motivo permitido | OrcamentoCancelado |
| SolicitarPagamento | orcamentoId, valorTotalCentavos >=1 | PagamentoConfirmado quando verificado; PagamentoFalhou só para resultado terminal |
| EstornarPagamento | pagamentoId UUID interno, motivo permitido | PagamentoEstornado após confirmação do provedor |

Ações HTTP do cliente originam `OrcamentoAprovado` ou `OrcamentoRecusado`.
Campos completos estão nos schemas compartilhados; não recriá-los divergentes neste documento.
Pagamento confirmado exige UUID interno, valorPagoCentavos, mercadoPagoPaymentId e confirmadoEm.
Estorno confirmado exige pagamentoId e estornadoEm. `PagamentoFalhou.motivo` aceita
`RECUSADO`, `EXPIRADO`, `ERRO_PROVEDOR`; timeout técnico não determina falha financeira.

## HTTP

| Rota | Status | Comportamento |
|---|---|---|
| `POST /api/v1/orcamentos/{id}/aprovar` | Contrato existente | 202 com orcamentoId, osId, sagaId, aprovadoEm; 401/403/404/409 conforme OpenAPI |
| `GET /api/v1/orcamentos/{id}` | Proposta Billing | Consulta somente pelo dono ou perfil aprovado; inclui resumo e estado |
| `POST /api/v1/orcamentos/{id}/recusar` | Proposta Billing | Recusa idempotente/concorrência; publicar evento normativo |
| `GET /api/v1/orcamentos/{id}/pagamento` | Proposta Billing | Retornar estado e URL de checkout ao dono; link fora da Saga |
| `POST /api/v1/webhooks/mercado-pago` | Proposta Billing | Receber/validar notificação; só confirmar evento após persistência durável |
| `GET /health/live/`, `GET /health/ready/` | Proposta Billing | Processo vivo e banco/migrations prontos; sem vazar detalhes |

A rota de aprovação não tem barra final no contrato; evitar redirect 307 no BDD.
Repetir aprovação não deve publicar outro evento; o comportamento de resposta para repetição
deve seguir 409 do contrato, ou replay idempotente se uma extensão HTTP for aprovada.

## Compatibilidade JWT existente

Auth emite RS256 com `iss=oficina-auth`, `aud=oficina-api`, `sub=cliente:<id>`,
`cliente_id` inteiro, `principal_type=cliente`, `token_type=access`, `iat`, `exp`, `jti`.
Comparar dono com `cliente_id` validado e exigir consistência com o `sub`.
Não comparar string `cliente:7` diretamente com inteiro 7 nem confiar em documento enviado no body.
O atendimento usa identidade de funcionário do legado; não converter um cliente em funcionário.

## Dependências que impedem integração ponta a ponta

Ver A-01 a A-15 da [auditoria](01-auditoria.md). Prioridades:

1. **Preço**: GerarOrcamento não informa preços e não há API de catálogo aprovada identificada.
   Recomendar catálogo local Billing para o projeto, com carga sintética explícita; alternativa
   é snapshot de preços em nova versão/contrato aprovado ou API de catálogo do responsável.
2. **Payloads OS**: persistir total e itens no orquestrador para comandos válidos; não alterar
   eventos de aprovação/confirmado para carregarem campos que o schema proíbe.
3. **Causa de eventos HTTP**: aprovar/recusar não chega por comando SQS novo; acordar causationId
   e requestId com Luís. Proposta: ID durável da ação HTTP como causa, requestId da Saga preservado,
   sem mutar o envelope compartilhado. Não tornar isso norma antes de alinhar.
4. **Checkout**: link via GET Billing resolve a questão aberta sem mensagem `PagamentoCriado`.
   É decisão local recomendada; atualizar a questão no repo Saga por PR separado quando acordado.
5. **Auth atendente e cliente ativo**: definir emissão/verificação do atendente e necessidade
   de status ativo sem leitura de banco externo. Chave pública não resolve revogação imediata.
6. **Stack real**: mapear DB_HOST, filas separadas, migrations, worker/relay Billing e tokens
   distintos do BDD. Não marcar stack pronta ao apenas adicionar Dockerfile.
7. **Orçamento zero**: schema de orçamento permite zero, de pagamento não. Necessário decidir
   política sem fabricar cobrança. Testes devem registrar o limite.

## Mercado Pago

Usar um port de provedor para isolar fake de testes e integração real em ambiente de testes.
Referência oficial atual distingue Checkout Pro via Orders e via Preferências. Orders é a
direção recomendada pela documentação para novas integrações; validar acesso da conta,
checkout URL, notificação, IDs de transação/pagamento e refund antes de fechar o adapter.
O campo normativo `mercadoPagoPaymentId` precisa referenciar o pagamento apropriado,
não ser preenchido com orderId por conveniência.

Não supor prefixo de Access Token para distinguir ambiente: usar configuração explícita e
credenciais apropriadas, nunca registradas no repo/chat. A integração não deve aceitar cartão
real nem executar movimentação real nesta fase de desenvolvimento.
Persistir `external_reference`/identificador local conforme API suportada; verificar assinatura,
consultar status autenticado, tratar reentrega e notificações fora de ordem.
Separar prova do fluxo local com fake da prova de integração com Mercado Pago.
