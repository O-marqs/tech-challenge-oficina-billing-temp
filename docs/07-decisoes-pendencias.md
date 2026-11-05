# Atualização de implementação

Lucas autorizou avançar autonomamente em 05/11. P-01/P-02/P-04/P-07 têm escolhas locais reversíveis
para o MVP, registradas em docs/11-implementacao.md: catálogo demo configurável, GET do link,
causa em OrcamentoGerado e rejeição de total zero. Precisam de alinhamento do grupo antes do aceite
integrado. Credenciais MP e perfil atendente continuam pendentes. Registro inicial segue abaixo.

# Decisões e pendências

Cada decisão distingue fato do contrato, direção local de planejamento e proposta que depende
do grupo. Nenhuma proposta daqui altera automaticamente um repo alheio.

## Registro de decisões

| ID | Estado | Decisão e razão |
|---|---|---|
| D-00 | Autorizada pelo Lucas | Registrar escopo/continuidade no GitHub, permitir colaboração atual e priorizar caminhos sem custos adicionais |
| D-01 | Direção local de planejamento | Python 3.11 + FastAPI + SQLAlchemy/Alembic + PostgreSQL exclusivo. Simplicidade de API/OpenAPI e compatibilidade com grupo; versões serão fixadas na implementação |
| D-02 | Contrato compartilhado existente | Saga orquestrada no OS; pagamento antes da execução; estorno separado e compensação inversa |
| D-03 | Direção local de planejamento | Inbox/outbox transacionais, intenção de operação externa durável, retry/reconciliação; evita duplicar efeitos financeiros |
| D-04 | Direção local recomendada | Disponibilizar link/estado por GET no Billing, fora da Saga, conforme alternativa A da questão aberta compartilhada; não criar PagamentoCriado |
| D-05 | Direção local de planejamento | Reaproveitar JWT RS256 e claims do Auth. Dono por cliente_id; atendente ainda pendente; nunca distribuir chave privada |
| D-06 | Direção local de planejamento | Primeiro testes locais, CI padrão e emulação; não provisionar AWS nem movimentar dinheiro real |
| D-07 | Autorizada e atualizada pelo usuário | Repositório temporário próprio `O-marqs/tech-challenge-oficina-billing-temp`; arquivos versionados são a referência atual, com índice no Confluence. Migrar commits para o Billing do grupo depois de resolver acesso |

## Questões a resolver

| ID | Pergunta / recomendação | Quem decide ou alinha | Bloqueia |
|---|---|---|---|
| P-01 | De onde vêm preços? Recomendar catálogo Billing com carga inicial sintética e snapshots; alternativa API/snapshot contratado com OS | Lucas; Hélio/Luís se mudar interface | Precificação e prova de integração de orçamento |
| P-02 | Como cliente recebe orçamento e link? Recomendar consulta/API documentada; email não é contrato explícito identificado | Lucas, validar entendimento do requisito com grupo | Notificação/experiência final; não bloqueia esqueleto |
| P-03 | Qual perfil/token atendente Billing aceita? Auth atual só emite cliente; SimpleJWT OS é outro emissor/modelo | Lucas/Hélio, alinhar com grupo | Endpoint de atendente e BDD com identidades corretas |
| P-04 | Qual causationId para aprovar/recusar via HTTP e qual requestId? Proposta em 04-contratos; não decidir silenciosamente | Lucas/Luís | Publicação dos eventos HTTP |
| P-05 | Corrigir campos ausentes em SolicitarPagamento/IniciarExecucao | Hélio/Luís | Stack real; manter Billing aderente ao schema |
| P-06 | Conta/app de testes Mercado Pago já existe? Orders está disponível para a conta e cobre os cenários? | Lucas fornece só existência/disponibilidade; IA verifica docs/adapter | Testes reais MP; não bloqueia fake/ports |
| P-07 | Como tratar orçamento zero e pagamento aprovado após cancelamento? Recomendar regra explícita/reconciliação; não simular nem perder cobrança | Lucas e grupo para efeitos na Saga | Casos de borda financeiros |
| P-08 | Onde ficam identidade ativa e cadastro no cenário distribuído? Auth legado consulta banco monólito | Lucas/Hélio | Autenticação integrada sem acesso cruzado indevido |
| P-09 | Conclusão/cancelamento Execution e atualização dos docs para contrato 1.1 | Sophia/Luís/Hélio | Fluxo integrado e compensação de execução |
| P-10 | Escrita no Billing do Hélio falhou com 403 apesar de metadata push=true. Temporário próprio já permite escrita. Resolver acesso ao destino; depois configurar proteção/checks/scanner/CD seguro | Lucas/Hélio; administração da integração quando necessário | Migração ao destino e aceite final; não bloqueia publicação no temporário |
| P-11 | Ajustes de compose e driver, fixture de preços/clientes, cenário de falha e checkout controlado | Luís/Hélio/Lucas/Sophia | BDD stack real e coleta de evidências |
| P-12 | Destino K8s, recursos gratuitos/academia, callback HTTPS e quotas New Relic/Sonar | Grupo; Sophia/Hélio na infra | Deploy e observabilidade remotos |

## Próxima pergunta ao Lucas

Primeiro confirmar P-01, pois isso define a regra central do orçamento. A recomendação é
catálogo próprio simples no Billing, inicialmente alimentado com dados sintéticos de demonstração,
sem ler tabelas do OS. Perguntar também se já há conta/app de testes Mercado Pago (não pedir tokens
no chat). Perfil atendente e contratos que envolvem o grupo devem continuar registrados até alinhamento.

Não suspender elaboração de documentação nem esqueleto independente por credencial ainda ausente.
Não implementar regras dependentes de respostas ausentes. Se o usuário direcionar outra solução,
atualizar o registro e o plano antes do código afetado.
