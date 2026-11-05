# Auditoria inicial dos repositórios

Data: 05/11/2026, horário de São Paulo. Auditoria por leitura de código, árvores Git,
branches e resultados de Actions. Nenhuma suíte dos serviços foi executada nesta sessão.
Os repositórios são públicos e recebem alterações da equipe durante o levantamento.

## Referências verificadas

Todos os repositórios abaixo pertencem a `helyomendesdev`.

| Repositório | Referência auditada | Situação observada |
|---|---|---|
| [oficina-billing](https://github.com/helyomendesdev/tech-challenge-oficina-billing) | Sem commit/branch; bootstrap recusado com 403 | Vazio; Lucas confirmou que não começou código local ou remoto |
| [oficina-os](https://github.com/helyomendesdev/tech-challenge-oficina-os) | `main`: `01072762c2369df56ee2dcd35805243d6eaacbe4`; atualização relevante conferida em `1bfaafaaa3575c803582f642e02b60f73f3e97fc` | Django/DRF, modelos, APIs, Saga, consumidor de respostas, timeout, K8s, CI/CD |
| [oficina-saga](https://github.com/helyomendesdev/tech-challenge-oficina-saga) | `main`: `ed3a8345ba684fc442193084ed7b8cbf72c3cdb9` | AsyncAPI 1.1.0, schemas wire v1, aprovação OpenAPI, BDD referência e driver real, compose local |
| [oficina-execution](https://github.com/helyomendesdev/tech-challenge-oficina-execution) | `main`/`develop`: `a6321a2ead03bc7b07e6bcc3ea6c1fdcc322b103`; `feat/execution-service`: `34fa9a67859f63123e3a51eefa1699026279ec61` | Main só com configuração/README; implementação está na feature branch |
| [oficina-auth](https://github.com/helyomendesdev/tech-challenge-oficina-auth) | `main`: `a9761dfd5a1d7a539661789ec952c51369294de8` | Lambda Python, JWT RS256, regras de claims, API Gateway, Terraform e testes da Fase 3 |
| [oficina](https://github.com/helyomendesdev/tech-challenge-oficina) | `main`: `10586ebc2fc3e6bfe51606ba3798d5a08006be70` | Monólito de referência; regras e exemplos reaproveitáveis, sem integração Mercado Pago identificada nos arquivos lidos |
| [oficina-k8s](https://github.com/helyomendesdev/tech-challenge-oficina-k8s) | `main`: `25acf2354ececf45045515a06de0ce66f9080f1b` | Infraestrutura compartilhada da Fase 3; existência de Terraform não prova ambiente provisionado |
| [oficina-database](https://github.com/helyomendesdev/tech-challenge-oficina-database) | `main`: `a741d25565eefd628491a830fa2634b543723e3a` | RDS/infra da Fase 3; não é o banco exclusivo do Billing já provisionado |

As branches foram consultadas inclusive fora de `main`; não havia PRs abertos nos oito
repos no primeiro inventário. Isso é um retrato do momento, não uma garantia futura.
`develop` de Auth, legado, K8s e Database existe e não foi integralmente auditada.

Atualização na mesma data: criado `O-marqs/tech-challenge-oficina-billing-temp`, público,
para o Lucas publicar documentação e desenvolver sem depender da escrita no destino.
Commit de bootstrap `cf141eb2bc6e41f7782bee638c8f4d1fcb68bbab`, branch documental
`docs/fase4-lucas-planejamento`. O destino do Hélio não foi modificado.
Leitura dos HEADs main de OS/Saga/Auth/Execution reconfirmada antes desta publicação:
respectivamente `1bfaafaaa3575c803582f642e02b60f73f3e97fc`,
`ed3a8345ba684fc442193084ed7b8cbf72c3cdb9`,
`a9761dfd5a1d7a539661789ec952c51369294de8` e
`a6321a2ead03bc7b07e6bcc3ea6c1fdcc322b103`.

## O que já existe e o que falta

| Área | Existente | Falta / limite da evidência |
|---|---|---|
| OS e Saga | Orquestrador, consumidor, timeout, consulta de Saga e correlação | Validar contratos dos comandos gerados, integração com participantes e implantação |
| Execution | Consumer SQS, persistência global DynamoDB, outbox/relay; domínio/use cases por serviço na feature | Ligar ciclo individual à persistência/consumer; conclusão global, falha e compensação operacionais ainda incompletas |
| Billing | Apenas este planejamento após o bootstrap | Toda implementação, banco, API, consumer, relay, Mercado Pago, testes, Docker/K8s/CI |
| Auth | Emissor e verificador RS256 existentes | Integração nos serviços novos, identidade atendente e separação da fonte de clientes |
| BDD | Cenários e driver de referência; driver e workflow para stack real | Execução integrada comprovada; os dados de falha do driver real ainda são marcadores |
| Qualidade | Workflows e resultados remotos em OS/Saga/Execution | Cobertura do Billing inexistente; qualidade completa e CD não são comprovados por badges |

## Achados de integração

| ID | Achado | Evidência | Encaminhamento |
|---|---|---|---|
| A-01 | `SolicitarPagamento` precisa de `valorTotalCentavos`; o construtor de payload do OS só repassa IDs nesse passo | OS `orquestrador_v1.py::_payload_comando`, inclusive no SHA atualizado; schemas de `SolicitarPagamento` e `OrcamentoAprovado` | Hélio/Luís precisam carregar o total de `OrcamentoGerado` na Saga e montar comando válido; Billing não deve afrouxar schema |
| A-02 | `IniciarExecucao` também precisa dos itens/`orcamentoId` que não vêm de `PagamentoConfirmado` | Mesmo construtor; schemas compartilhados e payload de confirmação | Corrigir retenção/montagem no OS e validar todas as saídas com schemas |
| A-03 | `GerarOrcamento` leva IDs/quantidades, mas não preços | Schema do comando e definições `itensServico`/`itensPeca` | Escolher fonte de preços; não consultar banco do OS |
| A-04 | OpenAPI da aprovação descreve `sub` igual a `clienteId`, mas Auth emite `sub=cliente:<id>` e `cliente_id` inteiro | `billing-aprovacao.openapi.yaml`; Auth `jwt_tokens.py` | Preservar JWT vigente e propor alinhamento da descrição; verificar ownership via `cliente_id` |
| A-05 | Auth existente não emite perfil de atendente | `Rs256TokenIssuer.issue` só emite `principal_type=cliente` | Não inventar papel; decidir com o grupo como validar credenciais de funcionário no Billing |
| A-06 | Classe RS256 existe no OS, mas configuração global lida usa apenas SimpleJWT; a chave pública do cliente também não aparece definida nesse settings | OS `authentication.py`, `app/settings.py`, views da interface | Auditar ativação efetiva e testar token real do Auth; classe existente não prova integração |
| A-07 | Compose usa `SAGA_QUEUE_URL` única, embora OS já tenha roteamento separado | Saga `stack/docker-compose.yml` e `stack/variaveis.md`; OS `saga_adapters.py`, `settings.py` | Passar `SAGA_BILLING_QUEUE_URL` e `SAGA_EXECUTION_QUEUE_URL` ao OS/worker |
| A-08 | Compose envia `POSTGRES_HOST`; OS lê `DB_HOST` | Mesmo compose e OS `settings.py` | Ajustar nomes e provar readiness com PostgreSQL real |
| A-09 | Driver real supõe corpo/resposta de abertura diferente da API lida | Saga `driver_stack_real.py::_corpo_abertura`; OS serializer/exemplos da view | Luís/Hélio alinham fixtures, corpo aninhado e ID retornado; hoje não comprova E2E |
| A-10 | Driver usa um token para abrir OS e aprovar orçamento; abertura nega principal cliente, aprovação exige dono/atendente | Driver `_cabecalhos`; OS `DenyClientPrincipalPermission`; OpenAPI Billing | Separar identidades/tokens no driver após decisão sobre atendente |
| A-11 | Driver real não realiza checkout nem aciona trabalho mecânico; dados de falha são placeholders | `DADOS_DO_CENARIO` e métodos do driver | Criar estratégia de testes com provedores controlados e validação Mercado Pago separada, sem sucesso automático escondido |
| A-12 | README do Execution ainda menciona grupo FIFO `os-{osId}`; publisher atual do OS usa `sagaId` | Execution README versus OS `SQSSagaPublisherV1` | Tratar como documentação desatualizada, não como bug ainda aberto do publisher |
| A-13 | README OS exibe Sonar; CI lido não invoca scanner/quality gate | OS `.github/workflows/ci.yml` | Hélio deve comprovar análise automática externa ou incluir verificação; badge não basta |
| A-14 | CD OS não está comprovado e workflow tem pontos suspeitos: registry só no outro job, apply de manifests com placeholders e erro ignorado em set-image | OS `.github/workflows/cd.yml`; última execução remota consultada falhou | Hélio audita CD; não copiar cegamente o template para Billing |
| A-15 | Auth Fase 3 consulta `atendimento_cliente` no RDS do monólito | Auth README/handler e composição Postgres | Decidir migração da identidade por API/projeção própria; não apontar Auth para banco privado do OS/Billing sem resolver fronteiras |

Achados estáticos não equivalem a incidentes reproduzidos em runtime. Corrigir em PRs
dos respectivos responsáveis; não atribuir ao Billing a responsabilidade exclusiva por destravar a stack.

## Evidências de CI consultadas

- OS: [CI success](https://github.com/helyomendesdev/tech-challenge-oficina-os/actions/runs/42096507153)
  e [CD failure](https://github.com/helyomendesdev/tech-challenge-oficina-os/actions/runs/42096504993),
  ambos no SHA `1bfaafaaa3575c803582f642e02b60f73f3e97fc`.
- Saga: [contrato success](https://github.com/helyomendesdev/tech-challenge-oficina-saga/actions/runs/42062735870)
  no SHA `ed3a8345ba684fc442193084ed7b8cbf72c3cdb9`. Não prova stack real.
- Execution: [CI success na feature branch](https://github.com/helyomendesdev/tech-challenge-oficina-execution/actions/runs/41263934787)
  no SHA `34fa9a67859f63123e3a51eefa1699026279ec61`. Não prova funcionalidade integrada.
- Metadata da branch `main` do OS indica `protected=true`; regras específicas de review/checks
  não foram verificadas via administração. Não foi feita alteração de proteção.

## Como reproduzir a auditoria

Abra os repos nas referências acima; leia árvore, READMEs, arquivos apontados e Actions.
Exemplo de referência imutável:
[payloads do OS](https://github.com/helyomendesdev/tech-challenge-oficina-os/blob/1bfaafaaa3575c803582f642e02b60f73f3e97fc/os_service/application/saga/orquestrador_v1.py),
[contratos da Saga](https://github.com/helyomendesdev/tech-challenge-oficina-saga/tree/ed3a8345ba684fc442193084ed7b8cbf72c3cdb9/contrato),
[código Execution](https://github.com/helyomendesdev/tech-challenge-oficina-execution/tree/34fa9a67859f63123e3a51eefa1699026279ec61),
[JWT Auth](https://github.com/helyomendesdev/tech-challenge-oficina-auth/blob/a9761dfd5a1d7a539661789ec952c51369294de8/src/oficina_auth/infrastructure/jwt_tokens.py).

Fontes privadas fornecidas por Lucas: enunciado da Fase 4 e histórico técnico do grupo.
Só os requisitos e a divisão de tarefas foram resumidos; os anexos e o histórico não serão republicados.
