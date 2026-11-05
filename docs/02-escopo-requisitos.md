# Escopo e rastreabilidade

## O que Lucas assumiu

Divisão de 07/10, confirmada pelo Lucas: Billing (orçamento/pagamento/Mercado Pago) e
JWT na frente dos serviços usando `-auth`. Em 13/10, escolha do banco atribuída ao Lucas.
Em 16/10, mensagens de pagamento e encaminhamento do link reforçados como parte do Billing.
Lucas confirmou nesta sessão que não havia iniciado implementação.

Datas informadas pelo grupo: esqueletos em 24/10, prazo interno 07/11, entrega 17/11.
Não verificamos o portal acadêmico; 17/11 é a data reportada pelo grupo, não extraída do PDF.
Em 05/11, não é realista declarar a stack integrada pronta sem resolver os bloqueios registrados.

## Matriz do enunciado

| Requisito Fase 4 | Contribuição Lucas/Billing | Dependência / aceite |
|---|---|---|
| Pelo menos 3 microsserviços, cada um em repo próprio | Billing independente neste repo | OS/Hélio e Execution/Sophia completam os três |
| Infra e banco próprios por serviço | PostgreSQL exclusivo, migrations e workload Billing | Sophia coordena infraestrutura; nenhuma leitura de banco alheio |
| Ao menos um SQL e um NoSQL | Billing SQL | OS também SQL; DynamoDB no Execution cumpre lado NoSQL quando validado |
| REST quando necessário + mensageria assíncrona | API de orçamento/pagamento; comandos/respostas SQS FIFO | Contrato Luís, recursos Sophia, roteamento Hélio |
| Saga com rollback/compensação e justificativa | Gerar/cancelar orçamento, solicitar/estornar pagamento | Orquestrador OS; compensação Execution; testes de falha integrados |
| Integração Mercado Pago | Adapter, teste de cobrança/status/webhook/estorno | Ambiente de testes e credenciais do usuário; não basta fake |
| Testes unitários e cobertura >=80% por serviço | Gate medido do Billing, testes de domínio/aplicação/adapters | Cobertura global não substitui cobertura por serviço |
| Ao menos um fluxo completo BDD | Disponibilizar Billing para cenários da Saga | Luís mantém BDD; executar contra stack real e guardar evidência |
| SonarQube ou similar no CI | Análise estática e segurança no CI; Sonar se viável sem custo | Confirmar com Hélio equivalência e checks; scanner não pode ser só badge |
| CI/CD independente com build, testes, qualidade e deploy K8s | Workflows Billing e manifests | Template Hélio; infra Sophia; CD desabilitado até destino configurado |
| Main protegida, PR e checks obrigatórios | Entregar changes por branches/PRs após bootstrap | Hélio configura regras e reviews; não comprovadas no Billing |
| Monitoramento/observabilidade da Fase 3 | Logs JSON, IDs, W3C via HTTP/SQS e hooks do agente existente | Luís valida trace entre serviços; modo local sem agente não prova New Relic |
| Dockerfile, K8s, Swagger/collection, docs e cobertura | Dockerfile, OpenAPI, runbook, evidências Billing | Só documentação entregue nesta etapa |
| Vídeo <=15 min e PDF final | Roteiro/demonstração da parte Billing, links e decisões | Responsável final pelo vídeo/PDF precisa ser combinado; não foi atribuído ao Lucas por inferência |

## Fora da implementação inicial do Lucas

Não construir frontend completo, serviço de estoque, novo produto de identidade,
orquestrador paralelo, plataforma de pagamentos ou infraestrutura AWS duplicada.
Não assumir a parte de Sophia/Hélio/Luís por silêncio. Dependências ficam visíveis no plano.

## Critério de conclusão da parte Lucas

Billing reproduzível, com persistência real, mensagens válidas, isolamento por cliente,
cobertura >=80%, retry/duplicidade testados, pagamento e estorno comprovados no ambiente
de testes Mercado Pago, build/K8s/CI/CD e documentação atualizados. Confirmar pelo menos
um fluxo BDD integrado com a equipe e rastreabilidade distribuída.
Fake, CI verde, código em branch e deploy validado são evidências diferentes.
