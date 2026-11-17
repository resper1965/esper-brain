---
name: retomar
description: Dá o briefing de um tema/projeto da vida do Ricardo a partir do esper-brain, para ele retomar o assunto sem perder o fio. Use quando ele perguntar "como está a sucessão?", "retoma o carro", "onde parei em X?", ou só mandar o nome de um tema.
---
# Retomar

Só lê; não grava nada.

1. Ache o tema como na skill `capturar` (passo 1). Se houver dúvida, pergunte qual.
2. Leia o arquivo inteiro (`~/esper-brain/projetos/<slug>.md` ou `<slug>/README.md`).
3. Responda em até 10 linhas, nesta ordem, pulando o que estiver vazio:
   - **Onde estou:** a seção, resumida.
   - **Próximo passo:** `proximo_passo` do topo.
   - **Prazos:** os que vencem primeiro, com data; marque ⚠️ o que vence em até 7 dias ou já venceu.
   - **Perguntas em aberto.**
   - **Ideias soltas ainda não tratadas:** as mais recentes (até 5), com data.
4. Se `ligacoes` tiver `gabi-finance projeto:N` e ele perguntar de dinheiro, consulte o MCP `gabi_finance`; não invente valor.
5. Termine com uma pergunta curta só se ajudar: `Quer atualizar o "Onde estou"?` ou `O próximo passo ainda é esse?`.
6. Se ele responder com atualização, use a skill `capturar` (ou edite "Onde estou"/`proximo_passo`) e grave com `tools/gravar.sh`; diga "atualizado" só depois de `gravado:`.

Tema sem mudança há mais de 30 dias: avise numa linha ("parado desde DD/MM; segue ou arquiva?").
