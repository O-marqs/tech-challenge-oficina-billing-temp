# Desenvolvimento local e custos

Objetivo: desenvolver sem despesa adicional contratada. Não há contratação, provisionamento,
transação financeira ou deploy nesta entrega. O computador/container e a conta ChatGPT do
usuário não são declarados gratuitos; o objetivo é evitar novos serviços pagos.

| Necessidade | Primeiro caminho | Limite / alternativa |
|---|---|---|
| Documentação e continuidade | Repo temporário público do Lucas e índice Confluence existente | Escrita no destino do Hélio segue bloqueada; temporário autorizado e acessível |
| Domínio e API | Python/pytest local, depois FastAPI e Postgres local | Fakes para teste unitário; banco real para teste transacional |
| SQS e DynamoDB de integração | Reaproveitar stack local do grupo com LocalStack fixado | Confirmar imagem/licença/disponibilidade antes de uso; se bloqueado, avaliar emulador SQS OSS compatível em override, sem trocar stack do grupo silenciosamente |
| PostgreSQL | Container separado exclusivo do Billing | Sem RDS exclusivo pago para desenvolver |
| CI | Runners Linux padrão do GitHub Actions no repo público | Uso desses runners é gratuito segundo GitHub; armazenamento, runners maiores e outros recursos têm regras próprias |
| Qualidade | Ruff, Bandit, auditoria de dependências e cobertura no CI | Escolher e fixar versões; Sonar opcional se plano/permissões gratuitos atenderem; não comprar plano |
| Mercado Pago | Contas, credenciais e cartões do ambiente de testes | Sem cartão/cobrança real; fake é teste local separado da prova no provedor |
| Kubernetes | kind local, se máquina suportar | Compartilhar cluster local do grupo; deploy automatizado local deve gerar evidência; validar com o grupo o ambiente final |
| Nuvem exigida pelo grupo | Só ambiente acadêmico já disponível, após conferir limites | Não supor EKS, NAT, ALB, RDS ou recursos de laboratório ilimitados/gratuitos |
| Observabilidade | Logs JSON e W3C local; hooks compatíveis com Fase 3 | New Relic só quando conta/quota existentes forem confirmadas; não afirmar rastreio remoto antes de validar |
| Callback HTTPS | Definir endpoint de testes para webhook na etapa MP | Não contratar domínio/hospedagem/túnel; estudar opção temporária permitida ou ambiente existente |

## Ordem econômica de trabalho

1. Documentação, regras puras, validação de schemas e testes sem Docker/AWS.
2. API + PostgreSQL Billing; iniciar só esses processos, com pool e workers pequenos.
3. SQS local e workers; testar atomicidade, retries e reinício.
4. Stack do grupo sob demanda; não manter todos os containers durante teste unitário.
5. Mercado Pago com configuração de teste e credenciais fora do Git.
6. kind/ambiente acadêmico apenas para prova de deploy e integração autorizada.

Não presumir configuração ou capacidade do PC atual. O Codex local estava desligado;
a documentação publicada permite trabalhar agora e retomar depois sem depender deste container.

## Variáveis que o esqueleto deve documentar

Propostas, não existentes ainda: `DATABASE_URL`, `QUEUE_BILLING_COMANDOS_URL`,
`QUEUE_OS_SAGA_RESPOSTAS_URL`, `AWS_ENDPOINT_URL`, `AWS_REGION`,
`AUTH_JWT_PUBLIC_KEY_B64`, `MERCADO_PAGO_MODE`, `MERCADO_PAGO_ACCESS_TOKEN`,
`MERCADO_PAGO_WEBHOOK_SECRET`, URLs públicas de teste e flag explícita do provider fake.
Alinhar nomes às variáveis já fornecidas no compose da Saga.
Em nuvem, retirar endpoint/credenciais fake e usar identidade do workload.

O modo fake deve ser explícito, restrito a teste/desenvolvimento e identificado nos logs/evidências.
Não permitir modo fake como fallback silencioso quando credencial real está ausente.
`.env` e chaves nunca versionados; exemplos só com placeholders/sintéticos.

## CI/CD futuro

PR de documentação não inicia deploy. CI funcional terá lint, testes, cobertura >=80%, análise
de segurança, validação contratual e build. Configurar retenção curta de artefatos e evitar jobs
redundantes; não usar runners maiores. Análise Sonar só quando viável no plano existente.
CD deve depender do mesmo commit aprovado nos checks, ter destino configurado e permanecer
desabilitado até autorização/configuração. Não copiar o workflow OS sem corrigir A-14.

## Fontes oficiais consultadas em 05/11/2026

- [GitHub Actions: billing and usage](https://docs.github.com/en/actions/concepts/billing-and-usage):
  uso de runners padrão em repos públicos; isso não torna infraestrutura AWS gratuita.
- [Mercado Pago: contas de teste](https://www.mercadopago.com.br/developers/en/docs/checkout-pro-preferences/test-accounts):
  contas comprador/vendedor e ambiente próprio de testes.
- [Mercado Pago: compras de teste](https://www.mercadopago.com.br/developers/pt/docs/checkout-pro-preferences/integration-test/test-purchases):
  cenários sem cartão real; conferir regras da variante escolhida antes de executar.
- [Checkout Pro: alternativas de API](https://www.mercadopago.com.br/developers/pt/reference/online-payments/checkout-pro-orders/overview):
  diferencia Orders e Preferências; não misturar contratos de APIs.
- [Notificações Checkout Pro Orders](https://www.mercadopago.com.br/developers/pt/docs/checkout-pro-orders/notifications?scope=prod):
  assinatura e configuração de webhook; modo teste precisa estar correto.
- [Refund via Payments](https://www.mercadopago.com.br/developers/pt/reference/online-payments/checkout-pro-preferences/create-refund/post):
  referência de estorno e chave idempotente do fluxo correspondente, não garantia para toda API MP.
- [SonarQube Cloud: planos](https://docs.sonarsource.com/sonarqube-cloud/administering-sonarcloud/managing-subscription/introduction):
  há plano Free; recursos/elegibilidade devem ser confirmados, sem assumir análise ilimitada.
