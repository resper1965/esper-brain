---
name: retomar
description: Dá o briefing de um tema/projeto da vida do Ricardo a partir do esper-brain, para ele retomar o assunto sem perder o fio. Use quando ele perguntar "como está a sucessão?", "retoma o carro", "onde parei em X?", ou só mandar o nome de um tema.
---
# Retomar

Só lê; não grava. Ferramentas do MCP `esper_brain`.

1. `listar_temas` e ache o tema como na skill `capturar`. Na dúvida, pergunte qual.
2. `ler(caminho)` do tema.
3. Responda em até 10 linhas, nesta ordem, pulando o que estiver vazio:
   - **Onde estou** (resumido).
   - **Próximo passo** (`proximo_passo`).
   - **Prazos**, os primeiros, com data; ⚠️ no que vence em até 7 dias ou já venceu.
   - **Perguntas em aberto.**
   - **Ideias soltas** mais recentes (até 5), com data.
4. Se `ligacoes` tiver `gabi-finance projeto:N` e ele perguntar de dinheiro, consulte o MCP `gabi_finance`; não invente valor.
5. Última mudança (coluna final de `listar_temas`) há mais de 30 dias → uma linha: `parado desde DD/MM; segue ou arquiva?`.
6. Se ele responder com atualização: `substituir` (Onde estou, `proximo_passo`, `estado`) ou a skill `capturar`, depois `gravar`; diga "atualizado" só depois de `gravado:`.
