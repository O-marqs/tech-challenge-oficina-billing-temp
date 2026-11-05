# Continuidade — estado atual do Billing

Data: 05/11/2026. Repo de trabalho: `O-marqs/tech-challenge-oficina-billing-temp`.
Branch executável: `feat/billing-mvp-local`; [PR #2 em rascunho](https://github.com/O-marqs/tech-challenge-oficina-billing-temp/pull/2).
Base documental: `docs/fase4-lucas-planejamento`, PR #1. Nenhum merge ou deploy foi feito.
Destino oficial: `helyomendesdev/tech-challenge-oficina-billing`, inalterado por esta sessão.

## Leia e execute primeiro

1. Leia README, AGENTS.md e docs/11-implementacao.md; confira HEAD/CI do PR #2.
2. `uv sync --frozen --extra dev` e `uv run python scripts/demo.py`.
3. `uv run pytest --cov=billing_service --cov-report=term-missing`.
4. Para processos separados, usar compose.yml e scripts/smoke_stack.py, conforme README.
5. Não use o antigo ZIP documental como estado atual: ele precede o código.

## Implementado

API FastAPI com JWT RS256 e ownership de cliente; catálogo local configurável; geração,
aprovação, recusa e cancelamento de orçamento; SQLite para demo/PostgreSQL para execução;
Alembic; inbox/outbox; consumer/publisher FIFO; operações de provedor duráveis, retry,
reconciliação por CLI; provider fake explícito; adapter Checkout Pro Orders e webhook
assinados testados por HTTP mocks; Docker/compose, CI e templates K8s.

Primeiro CI: 65 PASS, cobertura 96,98% com PostgreSQL; build Docker e auditoria sem vulnerabilidades
conhecidas nos pacotes consultados. CI seguinte também validou API/workers + PostgreSQL + LocalStack,
incluindo confirmação fake explícita, estorno e cancelamento. Fonte: docs/11-implementacao.md.
Depois, a CLI passou a integrar o denominador de cobertura e recebeu oito testes: resultado local
70 PASS, 3 SKIP PostgreSQL, cobertura 96,66%. No run 42110862161, o mesmo commit funcional
e7f668df37324c902a0140cc32cea73fb24d7bcf passou com 73 PASS, sem SKIP, cobertura 96,92% e
integração de containers. Próximos commits apenas documentais não substituem essa ancoragem.

## Próximos passos úteis

- Configurar conta/aplicação/credenciais de TESTE Mercado Pago e callback HTTPS; provar cobrança,
  recusa e estorno reais no ambiente de testes. Nunca solicitar tokens pelo chat.
- Alinhar com Hélio/Luís os payloads incompletos do orquestrador, os dados/tokens do BDD e o mapeamento
  de variáveis. `compose.team.override.yml` é proposta local, não comprova stack completa.
- Sophia precisa conectar ciclo de conclusão/cancelamento Execution; Billing não deve simular esse serviço.
- Definir identidade atendente e origem do cadastro ativo sem leitura direta de banco alheio.
- Validar exportação de spans New Relic; hoje há W3C no transporte e correlação persistida.
- Preparar CD/K8s somente depois de destino/configuração/review autorizados.
- Antes de migrar, ler docs/10-migracao-github.md e conferir código novo no repo do Hélio.

## Regras que precisam continuar explícitas

Preço demo é sintético, não preço corporativo. Causa HTTP de decisão é o evento OrcamentoGerado;
requestId e trace da Saga são preservados. Total zero é rejeitado com OrcamentoFalhou.
Fake não autoaprova pagamento e não possui endpoint HTTP de sucesso; simulação é CLI de desenvolvimento.
Notificação tardia/duplicada financeiramente exige intervenção; não descartar cobrança real.
Credenciais, transações reais, Terraform apply, merge, deploy e mensagens ao grupo não foram autorizados.

## Instrução para outra IA

> Continue na branch feat/billing-mvp-local do repo temporário O-marqs/tech-challenge-oficina-billing-temp.
> Leia AGENTS.md, README e docs/11-implementacao.md. Confira o PR #2 e seus checks antes de mudar.
> O serviço já executa localmente; não recomece do zero e não trate o plano inicial como implementação pendente.
> Avance nas dependências reais do grupo e no teste Mercado Pago após configuração segura do ambiente.
> Preserve schemas/JWT/bancos separados, não faça merge ou deploy e atualize este handoff com evidências.
