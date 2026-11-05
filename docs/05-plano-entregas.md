# Plano de entregas do Lucas

Data base: 05/11/2026. Entregas pequenas, sem substituir trabalho dos outros responsáveis.
O plano abaixo foi criado antes do código. Estado atualizado da entrega acelerada:
Os números abaixo são rótulos de planejamento, não números reais de PR no GitHub.
O código está no PR real #2, branch feat/billing-mvp-local.

| Área do plano | Estado da implementação atual |
|---|---|
| PR-01 | Documentação publicada |
| PR-02 | Esqueleto/API/configuração/build e CI executados |
| PR-03 | Persistência, inbox/outbox e SQS implementados; PostgreSQL/containers validados no CI |
| PR-04 | Orçamento e autorização de cliente implementados; catálogo sintético configurável |
| PR-05 | Fluxo fake explícito, retry, confirmação e compensação implementados e demonstrados |
| PR-06 | Adapter Orders e webhook com mocks; teste na conta Mercado Pago ainda pendente |
| PR-07 | JWT cliente implementado; identidade atendente e ajustes Auth/OS pendentes |
| PR-08 | Billing em containers validado; stack completa do grupo e BDD pendentes |
| PR-09 | CI/build e templates K8s; sem CD/deploy ou proteção alterada |
| PR-10 | Evidências técnicas atualizadas; vídeo/PDF do grupo pendentes |


| Entrega | Conteúdo | Critério de aceite | Dependências |
|---|---|---|---|
| PR-01 Documentação | Auditoria, escopo, arquitetura, contratos, backlog, continuidade e AGENTS | Links verificados, sem prometer código/testes/deploy inexistentes; publicação em branch do repo temporário e índice no Confluence | Autorização recebida; acesso de escrita confirmado no temporário |
| PR-02 Esqueleto executável | pyproject/lock, camadas, config, health, Docker, env example, CI build/lint/test/cobertura | Instalação reproduzível, testes úteis >=80%, readiness testa banco, sem AWS/MP real | Não depende das decisões de preço/atendente; iniciar após esta documentação |
| PR-03 Persistência e mensageria | Migrations PostgreSQL, inbox/outbox, consumer FIFO, relay, shutdown e retry | Teste em PostgreSQL de atomicidade/conflito/restart; SQS local confirma só após commit | Contratos e env names fixados; recursos locais |
| PR-04 Orçamentos | Gerar/cancelar, consulta, aprovar/recusar, validade e preço snapshot | Mensagens validadas contra schemas, ownership e concorrência aprovação/cancelamento testados | Escolher preço, causa HTTP e regras pendentes |
| PR-05 Pagamentos isolados | Operação durável, idempotência, GET link, status e estorno com provedor fake | Duplicatas/timeout desconhecido/reconciliação não duplicam cobrança/estorno | Contrato, regras de valor zero e eventos tardios |
| PR-06 Mercado Pago testes | Checkout escolhido, credenciais externas, webhook assinado, consulta e refund | Evidência sanitizada de criação/pagamento/recusa/estorno no provedor | Conta/app/credenciais e endpoint HTTPS; sem dinheiro real |
| PR-07 JWT e integração Auth | Validador RS256 e ownership Billing; PRs de ativação/rotas nos repos necessários | Tokens válidos/expirados/assinatura/aud/iss/cliente errado testados; sem DB alheio | Contrato atendente e origem de identidade; ler AGENTS de cada repo |
| PR-08 Integração da stack | Wiring com Saga/OS/Execution, compose corrigido e BDD | Fluxo e compensação observados no histórico, logs e IDs; nenhum fake apresentado como MP real | A-01/A-02/A-07/A-08/A-09/A-10; ciclo Execution |
| PR-09 Entrega e K8s | Manifests, workload API/consumer/relay, pipeline CD, Swagger e runbook | Build e checks, deploy K8s automatizado e evidenciado; main protegida | Hélio CI/CD/review; Sophia infraestrutura; destino autorizado |
| PR-10 Evidências finais | Matriz cumprida, cobertura, roteiro Billing, links para PDF/vídeo | Documentação reflete resultados reais e limites; artefatos finais acessíveis | Stack e coleta de evidências do grupo |

É possível antecipar o validador JWT cliente do PR-07 durante PR-04; não precisa esperar Mercado Pago.
Não prometer prazo por PR antes de conhecer disponibilidade do Lucas/ambiente e alinhamentos.

## Primeira tarefa executável

**PR-02: esqueleto local do Billing.** Usar o repo temporário
`O-marqs/tech-challenge-oficina-billing-temp` e partir da documentação em
`docs/fase4-lucas-planejamento`; registrar essa dependência até sua integração.
O repo temporário já tem acesso de escrita verificado. Não é necessário resolver a escrita
no destino do Hélio para implementar e testar aqui. Migrar conforme `10-migracao-github.md`.
Começar com health/config/ports e estrutura de banco, testes reais desses comportamentos,
sem implementar preço, atendente ou integração financeira pendentes.
Publicar comandos efetivamente utilizáveis no README junto com o código.

## Verificação funcional que precisa existir

| Caso | Resultado esperado |
|---|---|
| Comando repetido após reinício | Mesmo orçamento/pagamento/resposta; nenhum efeito novo |
| Mesmo messageId com body diferente | Recusa observável; não sobrescreve resultado |
| Queda após commit antes do ack | Reentrega não duplica estado/intenção; outbox recuperável |
| Queda após send antes de marcar publicado | Reenvio preserva messageId/corpo e correlação |
| Dois workers na mesma Saga | Constraints/locks evitam cobrança/eventos contraditórios |
| Aprovar após validade/cancelamento | Rejeita sem emitir aprovação |
| Cliente diferente do dono | 403; não expõe link ou dados do orçamento |
| Token inválido/algoritmo/aud/iss errado | 401; não cai em modo anônimo |
| Webhook falso ou valor/moeda divergente | Não confirma pagamento |
| Checkout criado ou redirect de sucesso | Continua aguardando pagamento verificado |
| Timeout de cobrança/estorno | Mantém estado desconhecido e reconcilia com chave estável |
| Falha transitória do refund | Não publica PagamentoEstornado; permite retry/reconciliação |
| Falha após pagamento confirmado | Compensação só termina quando estorno e cancelamento confirmados |
| Logs e traces | IDs consistentes; ausência de tokens, CPF, cartões e credenciais |

Cobertura mínima de 80% é gate, não substituto desses testes. SQLite ou fakes não provam locks,
constraints e transações PostgreSQL. BDD de referência não substitui stack real.

## Coordenação externa necessária

Lucas apresenta A-01/A-02 e ajustes de stack para Hélio/Luís; Sophia mantém a conclusão/cancelamento
Execution e a infraestrutura. Esta sessão não envia mensagens a ninguém nem cria tarefas atribuídas
sem instrução do usuário. Registrar resposta/acordo quando houver e atualizar decisões.
