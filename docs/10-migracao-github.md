# Repositório temporário e migração para o Billing do grupo

Data: 05/11/2026. Lucas autorizou criar um repo em sua própria conta para continuar
e transportar o trabalho ao repo do Hélio posteriormente.

| Papel | Local |
|---|---|
| Trabalho atual | `O-marqs/tech-challenge-oficina-billing-temp` |
| Branch documental | `docs/fase4-lucas-planejamento` |
| Destino do serviço no grupo | `helyomendesdev/tech-challenge-oficina-billing` |
| OS/orquestrador | `helyomendesdev/tech-challenge-oficina-os` |
| Mensagens e BDD | `helyomendesdev/tech-challenge-oficina-saga` |
| JWT existente | `helyomendesdev/tech-challenge-oficina-auth` |
| Execution | `helyomendesdev/tech-challenge-oficina-execution`, implementação na feature auditada |

## Por que existe

O destino recusou `create_file` com 403 (`Resource not accessible by integration`).
A instalação consultada da integração está na conta `O-marqs`, com seleção de todos
os repos dessa conta. Não foi observada instalação acessível na conta do Hélio.
Isso explica a diferença entre colaboração pessoal e acesso por instalação, mas não
é prova isolada de todas as configurações que motivaram o 403 do destino.
No temporário, criação do repo foi realizada pelo navegador autenticado e a criação da branch
foi confirmada pela conexão GitHub. Acesso de leitura ao código do grupo foi reconfirmado.

## Regras para manter migração simples

- Manter um serviço Billing, com os contratos/nome de aplicação/nomes de fila do grupo.
- Não criar uma variante funcional própria só por estar em outro repo.
- CI do temporário roda só verificações locais/build; não implantar recursos do grupo.
- Compose do repo Saga ainda aponta o Billing do Hélio. Testes do temporário usam
  override local apontando build para este checkout, sem alterar main alheia.
- Pin de dependência de contratos deve usar referência auditada imutável do `-saga`;
  não copiar/bifurcar contrato para passar nos testes.
- Não copiar anexos privados, tokens, `.env`, chaves, logs sensíveis ou credenciais para Git.
- Não adicionar licença própria ao trabalho reaproveitado sem analisar licenças/origem.
- Não apagar o temporário depois da migração sem autorização do Lucas.

## Transporte ao destino quando houver acesso

1. Conferir HEAD, arquivos, PRs e instruções atuais do destino. Ele pode ter recebido
   alterações desde a auditoria; não assumir repo vazio nem sobrescrever conteúdo.
2. Definir base/review com Hélio. Se continuar vazio, criar README mínimo de bootstrap
   autorizado; se tiver histórico, partir de sua branch base vigente.
3. Manter remotos distintos e explícitos (`origin` temporário e `upstream` destino,
   se esses nomes ainda não estiverem ocupados). Conferir URLs antes de qualquer push.
4. Criar branch de migração a partir da base atual do destino e aplicar commits funcionais
   por cherry-pick/patch, resolvendo conflitos e preservando histórico/evidências de origem.
   Históricos independentes não devem ser fundidos com force push ou substituição da main.
5. Se o destino ainda não tiver histórico e o mantenedor optar por importar o histórico
   integral, registrar a escolha antes do push e preservar os commits existentes do destino.
6. Rodar checks no destino após a aplicação; conferir paths, Actions, links, badges,
   configurações de imagem e pin de dependências. Segredos/configurações não migram por Git.
7. Abrir PR para o destino; review humano e checks antes de merge, conforme regras do grupo.
8. Após aceite, atualizar compose/refs e continuidade para usar destino; manter temporário
   identificado como histórico/encerrado, sem jobs concorrentes de deploy.

Não é uma promessa de que GitHub permite transferir a propriedade do repo para um nome
já ocupado. O objetivo é mover o código/documentação por commits revisáveis, mantendo o repo
oficial já criado pelo grupo e suas integrações.

## Estado desta entrega

Repositório e branch documental criados; funcionalidade Billing ainda não implementada.
Fonte de preço, credenciais de teste Mercado Pago e demais perguntas do plano permanecem abertas.
O temporário resolve publicação/continuidade, não remove dependências funcionais de OS/Saga/Execution.
