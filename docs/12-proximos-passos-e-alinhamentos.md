# O que falta, responsáveis e primeira integração

Atualizado em 05/11/2026. Este documento é o ponto de entrada para Lucas revisar o trabalho
e conversar com o grupo. Estado técnico detalhado em [11-implementacao.md](11-implementacao.md).

## O que já está pronto para revisão

- Billing executável: orçamento, consulta, aprovação/recusa pelo cliente, cobrança e compensação.
- JWT RS256 compatível com as claims do Auth, com verificação de dono do orçamento.
- PostgreSQL dedicado, migrations, inbox/outbox, workers SQS FIFO e operações idempotentes.
- Adapter Mercado Pago Orders e webhook assinado, verificados com HTTP mocks.
- Docker, ambiente local, CI e documentação para outra IA continuar.
- Fluxo entre API/workers/PostgreSQL/LocalStack já passou no CI com provider fake explícito.
- Revisão adicional: aprovação exige ID real da transação; estorno confere moeda, dono, valor,
  transação e evidência de reembolso integral processado antes de liberar a compensação.
  A URL de retorno configurada agora é enviada em config.online na criação da order.

Não houve validação autenticada na conta Mercado Pago, teste completo OS/Billing/Execution,
merge ou deploy. O repositório oficial não recebeu estes commits; usar o PR #2 do temporário.

## Separação de responsabilidades

| Pendência | Tipo e responsável | Próxima ação concreta |
|---|---|---|
| Conta/aplicação Mercado Pago e configuração protegida | Lucas; desenvolvimento acompanha | Disponibilizar acesso ao painel de desenvolvimento no modo Teste; configurar credencial e assinatura fora do chat/Git |
| Callback HTTPS | Grupo/infra; Billing conecta | Definir endereço acessível para POST /api/v1/webhooks/mercado-pago e cadastrá-lo no painel Teste |
| Cobrança, recusa, espera e estorno no sandbox | Desenvolvimento Billing + Lucas no checkout | Executar roteiro abaixo e guardar apenas IDs/status/valores sanitizados |
| Fonte dos preços | Decisão Lucas/grupo | Confirmar catálogo Billing com carga sintética para demonstração, ou contratar outra fonte de preço |
| Campos de SolicitarPagamento/IniciarExecucao | Hélio/Luís, integração com Lucas/Sophia | Persistir total e itens no OS e montar comandos completos conforme schemas |
| Perfil atendente e tokens do teste | Hélio/Lucas, alinhar com Luís | Definir emissor/claims do atendente e usar token cliente distinto para aprovação Billing |
| Conclusão/falha/cancelamento Execution | Sophia, integração com Luís/Hélio | Confirmar branch executável, cenários e mensagem final; não substituir por fake Billing |
| BDD real | Luís + responsáveis dos serviços | Corrigir abertura/IDs/tokens, executar checkout e disparar execução/falha pelos caminhos combinados |
| Traces New Relic | Desenvolvimento Billing + Luís/infra | Instrumentar spans e comprovar o trace distribuído; transporte W3C sozinho não prova exportação |
| Sonar, proteção e CD/K8s | Hélio/Sophia + desenvolvimento Billing | Confirmar destino e padrão; conectar templates e verificar pipeline/deploy autorizado |
| Migração para o repo oficial | Lucas/Hélio liberam integração; desenvolvimento migra | Resolver o 403 de escrita e transportar commits por branch/PR, sem sobrescrever trabalho novo |
| Vídeo/PDF e entrega acadêmica | Lucas e grupo | Coletar evidências depois da integração e combinar quem grava/consolida cada parte |

O que depende pessoalmente do Lucas é acesso/configuração de conta, decisões e coordenação.
A implementação, testes de integração, instrumentação e ajustes de código continuam sendo desenvolvimento.

## Mudanças do grupo reconferidas

| Repo/ref | Evidência | Consequência |
|---|---|---|
| OS main 1bfaafaaa3575c803582f642e02b60f73f3e97fc | _payload_comando copia IDs, sem recuperar total/itens para os próximos passos | A-01/A-02 continuam abertos; ver função em os_service/application/saga/orquestrador_v1.py |
| Saga main 3a5c61f7cb1c9625834a17efe4fa748e15d359b0 | Compose agora fornece SAGA_BILLING_QUEUE_URL e SAGA_EXECUTION_QUEUE_URL separadas | A-07 foi corrigido upstream; não pedir a mesma correção novamente |
| Auth main a9761dfd5a1d7a539661789ec952c51369294de8 | Perfil atual emitido é cliente | Identidade de atendente ainda precisa de acordo |
| Execution main a6321a2ead03bc7b07e6bcc3ea6c1fdcc322b103 | Main contém configuração inicial; compose referencia feat/execution-service | Confirmar a branch com Sophia; não inferir ausência de implementação apenas pela main |

Os 14 schemas Billing permanecem fixados no SHA anterior do Saga. O commit novo de roteamento
não os alterou. O override local já contempla workers/migration Billing e DB_HOST; não prova a stack.

## Perguntas prioritárias ao grupo

1. Hélio/Luís: conseguimos fechar os payloads do OS? SolicitarPagamento precisa também de
   valorTotalCentavos; IniciarExecucao precisa de orcamentoId, servicos e pecas recuperados do estado.
2. Podemos manter preços no Billing, com dados sintéticos de demonstração, e link/estado por GET?
   Aprovação/recusa preservam requestId e usam OrcamentoGerado como causationId; confirmar esse acordo.
3. Qual identidade de atendente será usada no OS e no BDD? A aprovação Billing usa token do cliente
   dono; um único token não deve representar os dois papéis.
4. Sophia/Luís: qual branch do Execution vamos integrar e como executar os cenários de conclusão,
   falha e cancelamento no BDD real? O driver atual ainda tem marcadores e não realiza checkout.
5. Quem disponibiliza o callback HTTPS, as configurações de observabilidade e o acesso da integração
   ao repo oficial? Precisamos combinar também a sessão de integração e a coleta de vídeo/PDF.

## Roteiro Mercado Pago de teste

Estado: NÃO EXECUTADO. Nenhuma conta, segredo ou transação foi criada por esta sessão.

1. Abrir a aplicação de desenvolvimento compatível com Checkout Pro Orders. Confirmar no painel
   o modo Teste e a credencial apropriada para essa aplicação/API; não escolher ambiente apenas
   pelo prefixo do token. As referências atuais de API e o guia de compra têm instruções diferentes
   sobre credenciais/usuários de teste; verificar a configuração da conta antes de habilitar o worker.
   Se houver invalid_credentials, não tentar credencial da conta pessoal produtiva para contornar.
2. Configurar Webhooks no painel **Teste**, tópico **Order (Mercado Pago)**, com a URL HTTPS
   terminando em /api/v1/webhooks/mercado-pago. Guardar a assinatura secreta no ambiente local protegido.
   MERCADO_PAGO_NOTIFICATION_URL registra a URL esperada; o código não cadastra o webhook no painel.
3. Configurar APP_ENV=test, PAYMENT_PROVIDER=mercadopago_test, banco de teste dedicado, chave pública
   do Auth, MERCADO_PAGO_ACCESS_TOKEN, MERCADO_PAGO_WEBHOOK_SECRET,
   MERCADO_PAGO_NOTIFICATION_URL e MERCADO_PAGO_RETURN_URL no ambiente protegido.
   A URL de retorno deve existir e consultar o estado do Billing; o redirect não confirma pagamento.
4. Subir migrations, API, consumer, operations e relay com o mesmo ambiente. O compose padrão e
   compose.team.override.yml fixam provider fake; não basta editar .env para mudar esses containers.
   Preparar um override privado específico para a sessão de teste antes de tentar o provedor.
5. Gerar/aprovar orçamento e entregar SolicitarPagamento válido pela integração combinada.
   Consultar GET /api/v1/orcamentos/{id}/pagamento com JWT do dono. Checkout criado deve manter
   AGUARDANDO_PAGAMENTO e não emitir PagamentoConfirmado.
6. Abrir checkout_url em janela anônima, com os cartões e cenários do guia oficial abaixo.
   O adapter aceita apenas orders ORDTST e recusa live_mode=true. Não usar cartão real.
7. Para aprovação, conferir webhook assinado, GET autenticado da order, BRL, referência local,
   valor e ID da transação. Só então observar PagamentoConfirmado no outbox/histórico OS.
   Para ausência de webhook, existe consulta manual autenticada:
   `uv run python -m billing_service.cli reconcile --payment-id UUID_INTERNO`.
   Esse comando usa a configuração corrente; não é gerador de pagamento fake.
8. Executar EstornarPagamento pelo caminho da Saga. O worker consulta a mesma order e faz
   reembolso integral com chave estável; só publica PagamentoEstornado quando a evidência do
   provedor corresponde integralmente ao pagamento. Repetir notificação/comando não deve duplicar.
9. Repetir com novo orçamento para recusa/pendência. Guardar IDs, valores, status e sequência de
   eventos sanitizados; não guardar token, CPF, dados de cartão, client_token ou payload bruto do provedor.

| Cenário | Evidência mínima de aceite | Estado |
|---|---|---|
| Checkout | Order de teste, referência/total e URL válida; nenhum evento de confirmação ainda | Pendente na conta |
| Aprovado | Consulta autenticada e evento único com ID do pagamento | Pendente na conta |
| Recusado/expirado | Resultado terminal verificado e PagamentoFalhou normativo | Pendente na conta |
| Pendente/timeout | Ausência de confirmação/falha financeira fabricada; consulta posterior possível | Pendente na conta |
| Estorno | Mesma order/transação, moeda e valor; refunds processados integrais e evento único | Pendente na conta |
| Duplicata | Mesmos IDs/efeito após reentrega e reinício | Pendente no sandbox; já testado localmente |

Fontes oficiais consultadas em 05/11/2026:

- [Criar order](https://www.mercadopago.com.br/developers/pt/docs/checkout-pro-orders/create-order?scope=prod).
- [Configurar retorno](https://www.mercadopago.com.br/developers/pt/docs/checkout-pro-orders/web-integration/configure-back-urls).
- [Configurar Webhooks Teste](https://www.mercadopago.com.br/developers/pt/docs/checkout-pro-orders/notifications).
- [Compra/cartões e cenários de teste](https://www.mercadopago.com.br/developers/pt/docs/checkout-pro-orders/integration-test/test-purchase-with-card).
- [Consultar order e requisitos da API](https://www.mercadopago.com.br/developers/pt/reference/online-payments/checkout-pro/get-order/get).
- [Refund integral e evidência da resposta](https://www.mercadopago.com.br/developers/pt/reference/online-payments/checkout-pro/refund-order/post).
