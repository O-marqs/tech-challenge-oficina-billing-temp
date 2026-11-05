# Continuidade para Lucas, ChatGPT e Codex

## Resumo que outra IA precisa ler

Lucas assumiu Billing/Mercado Pago/JWT da Fase 4. Em 05/11/2026 confirmou que não começou
implementação. Autorizou começar a colaboração por aqui e registrar tudo no GitHub, priorizando
custos mínimos. Codex local estava desligado. O primeiro resultado é esta documentação;
nenhuma funcionalidade Billing foi construída ou testada.

Referência atual de desenvolvimento: [repo temporário do Lucas](https://github.com/O-marqs/tech-challenge-oficina-billing-temp),
branch `docs/fase4-lucas-planejamento`. A criação/publicação foi expressamente autorizada
pelo Lucas, após o bloqueio de escrita no Billing do Hélio.
O [hub Confluence](https://marqs.atlassian.net/wiki/spaces/~7120204dc1d32324e343dcad205794dd624c7c/pages/26247169/Tech+Challenge+Fase+4+Lucas+Billing+Mercado+Pago+e+JWT)
permanece como índice. O pacote inicial é um snapshot histórico anterior ao temporário.
Destino final: `helyomendesdev/tech-challenge-oficina-billing`, que não recebeu alterações.
Não transferir propriedade do temporário por cima do destino existente: usar transporte
de commits/branch revisado conforme `docs/10-migracao-github.md`.

## Estado de trabalho

| Item | Estado |
|---|---|
| Enunciado e divisão técnica do grupo | Lidos; resumidos sem republicar anexos/histórico |
| Inventário de oito repos e branches relevantes | Feito; referências imutáveis em 01-auditoria |
| Leitura de código/contratos/workflows | Feita por amostragem dirigida aos riscos de integração |
| Plano/AGENTS/arquitetura/contratos/custos | Branch documental no temporário; índice no Confluence |
| Billing executável, DB, API e workers | NÃO INICIADO |
| Integração MP e JWT Fase 4 | NÃO INICIADA |
| Testes/cobertura local de Billing | NÃO EXECUTADOS / INEXISTENTES |
| CI, deploy e BDD real de Billing | NÃO EXECUTADOS |

## Retomar com segurança e utilidade

1. Ler `AGENTS.md`, `07-decisoes-pendencias.md` e `05-plano-entregas.md`.
2. Inspecionar Git e HEADs remotos; equipe atualiza os repos durante o trabalho.
3. Não atribuir a main do Execution o código que só existe em `feat/execution-service`.
4. P-01 (preços) deve ser respondida antes da precificação; P-06 antes de teste MP real.
5. Próxima entrega técnica independente: PR-02, esqueleto local. Manter interfaces pendentes
   explícitas; não precisar de AWS, credenciais MP ou PC Codex para escrever e testar núcleo.
6. Antes de mexer em Auth/OS/Saga, ler instruções daquele repo e abrir mudança separada somente
   no escopo autorizado; não alterar contrato compartilhado para acomodar bug local.
7. Registrar cada resultado com comandos e evidências; atualizar este handoff no mesmo commit.

## Instrução pronta para continuação

> Continue o Billing da Fase 4 no repo O-marqs/tech-challenge-oficina-billing-temp.
> Leia a branch docs/fase4-lucas-planejamento, especialmente AGENTS.md,
> docs/08-continuidade.md e docs/10-migracao-github.md. O destino final é
> helyomendesdev/tech-challenge-oficina-billing, ainda sem escrita autorizada pela integração.
> Confira HEADs e docs/07-decisoes-pendencias.md; não assuma que o plano virou código.
> Implemente a próxima entrega independente de docs/05-plano-entregas.md, com custo mínimo,
> testes reproduzíveis e registro no handoff. Mantenha contratos Saga/JWT existentes e bancos
> separados. Pare e pergunte ao Lucas se surgir dúvida de regra de negócio/contrato não resolvida.
> Não faça merge, deploy, terraform apply ou pagamento real. Ao terminar, reporte branch/SHA,
> arquivos, testes efetivamente rodados e o que ainda depende do grupo.

## Onde estão as evidências

`01-auditoria.md`: SHAs, branches, achados e links de Actions.
`04-contratos-integracao.md`: mensagens, HTTP, JWT e lacunas.
`09-registro.md`: trabalho realizado, validações e publicação.
Anexos pessoais do grupo não fazem parte do repo; não são necessários para retomar o plano.
