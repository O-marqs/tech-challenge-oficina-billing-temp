# Instruções para continuidade — Billing Fase 4

## Leia primeiro

Leia `README.md`, `docs/08-continuidade.md`, `docs/07-decisoes-pendencias.md`,
`docs/04-contratos-integracao.md` e o plano da tarefa em `docs/05-plano-entregas.md`.
Confira a branch e os HEADs atuais antes de implementar. Não dependa da memória do chat.
Esta documentação contém plano e evidência de leitura, não uma implementação pronta.
Repositório atual: `O-marqs/tech-challenge-oficina-billing-temp`, branch documental
`docs/fase4-lucas-planejamento`. Referência atual de desenvolvimento: arquivos Git desta branch.
Destino final: `helyomendesdev/tech-challenge-oficina-billing`; push para ele falhou com 403.
Não confundir os dois remotos. Acesso aos demais repos do grupo é de leitura nesta tarefa.
Leia `docs/10-migracao-github.md` antes de mudar remotos ou transportar commits.

## Escopo e fronteiras

- Lucas não havia iniciado Billing ou JWT da Fase 4 até esta sessão.
- Este repo será dono dos orçamentos, cobranças, resultados de pagamento e estornos.
- O OS é o orquestrador. Não implementar outro orquestrador aqui.
- Execution/estoque, infraestrutura compartilhada e contratos têm outros responsáveis.
- Não acessar banco de OS, Auth ou Execution. Referências externas são IDs sem FK entre bancos.
- Não alterar outros repos nesta tarefa; propor mudanças separadas, respeitando seus AGENTS.md.
- Não publicar export do WhatsApp, PDFs fornecidos pelo usuário, dados pessoais ou credenciais.

## Desenvolvimento

- Python 3.11; Clean Architecture com domínio e aplicação independentes de FastAPI, ORM e AWS.
- FastAPI, PostgreSQL dedicado, SQLAlchemy/Alembic são direção local inicial (ver D-01).
- Valide dependências e versões suportadas nas fontes oficiais antes de fixá-las.
- Valores monetários internos e nas mensagens em centavos inteiros; conversão externa com Decimal.
- IDs, datas, tipos, versão e nomes de fila devem seguir os schemas do repo `-saga`.
- Use `MessageGroupId=sagaId` e `MessageDeduplicationId=messageId`.
- Idempotência durável e outbox atômica com estado; não usar a janela FIFO como garantia financeira.
- Persistir intenção e chave de operação antes de chamar Mercado Pago. Resultado desconhecido exige
  reconciliação; timeout não equivale a cobrança recusada ou a estorno concluído.
- Não adicionar campos a mensagens com `additionalProperties: false` para contornar lacunas do produtor.
- Não simular integração real nem desativar JWT para fazer o BDD passar.

## Decisões pendentes

Fonte dos preços, perfil atendente, variante do Checkout e semântica de eventos HTTP precisam
do encaminhamento registrado em `docs/07-decisoes-pendencias.md`. Pode-se implementar interfaces
e fakes isolados, mas não escolher silenciosamente um contrato externo ou regra de negócio pendente.
Se surgir dúvida que altere escopo/regra/contrato, pare a parte dependente e pergunte ao Lucas.

## Git e autorização

O usuário autorizou registrar documentação no GitHub e iniciar a colaboração de desenvolvimento.
Também autorizou criar um repositório temporário próprio e levar o trabalho ao destino depois.
O nome/publicação atual não altera o nome do serviço, contratos, banco ou nomes de filas do grupo.
Não é necessário pedir de novo para atualizar os documentos deste conjunto.
Use branches pequenas; nunca faça force push nem descarte trabalho concorrente.
Não faça merge, deploy, `terraform apply`, habilitação de recursos pagos ou transações reais
sem autorização específica. Um push não deve iniciar deploy pago.
Exceção de bootstrap: repo vazio exige um primeiro README na branch padrão para permitir criar
a branch documental. Nenhum código ou workflow é introduzido nesse commit inicial.
Esta autorização não permite enviar mensagens ao grupo, emails ou convites.

## Verificação e encerramento

Não existem comandos de teste do Billing ainda. Não invente resultados nem declare 80% sem medição.
Ao criar o esqueleto, documente comandos reproduzíveis para lint, formato, testes, cobertura,
contratos, migrations, build e integração PostgreSQL/SQS local.
Depois de cada entrega, atualize `docs/09-registro.md`, `docs/08-continuidade.md`, os status
do plano e as decisões; inclua SHA, comandos executados, resultados reais e limitações.
Mantenha separado: planejado, implementado, teste local, CI e validação integrada real.
