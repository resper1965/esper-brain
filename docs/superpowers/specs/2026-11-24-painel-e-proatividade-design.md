# Painel de temas (estilo Trello) e proatividade da Gabi — design

Data: 2026-11-24. Partes 2 e 3 do plano "Gabi mais esperta" (a parte 1, blocos, está em `2026-11-23-gabi-blocos-design.md`).
O Ricardo pediu as duas partes "sem muita intervenção, com as melhores recomendações"; as decisões abaixo foram tomadas assim e estão marcadas (decidido pelo Claude) quando não vieram dele.

## 1. Ajustes no modelo de áreas (do Ricardo, 24/11)
- Trabalho tem **3 empresas**: `ness` (marcas `forense.io`, `trustness`, `secops`), `ionic` (frentes governanca, produto, operacao, pessoas, acionista) e `bekaa`.
- **Não existe mais `pf`**: freelancer é Bekaa (a nota fiscal sai pela Bekaa); quem contratou vai em `cliente`.
- "Última mudança" de um tema passa a vir do `git log` (data do último commit do arquivo), não do mtime, que muda a cada pull.

## 2. Proatividade (decidido pelo Claude)
- Ferramenta MCP nova `temas_atencao(dias_prazo=7, dias_parado=30)`: lista o que pede atenção, só de temas com estado `ativo`:
  `vencido` (prazo < hoje), `prazo_perto` (prazo em até `dias_prazo`), `parado` (sem mudança há mais de `dias_parado`), `sem_passo` (proximo_passo vazio); mais `entrada_pendente` (quantos pedaços e o mais antigo). Hoje = America/Sao_Paulo.
- Skill `vigiar`, em dois modos:
  - **diário** (cron 08:40): só vencidos e prazos em até 3 dias; nada → não manda nada (resposta vazia). Uma linha por item, com área › tema e a data.
  - **semanal** (cron segunda 08:50): revisão por área: vencidos, prazos da semana, parados há > 30 dias, sem próximo passo, entrada esquecida; no fim uma pergunta: qual tema retomar. Máx. 15 linhas.
- A Gabi nunca muda tema sozinha nessas rotinas: só avisa.

## 3. Painel (caminho 1, decidido com o Ricardo; detalhes pelo Claude)
- **Onde:** `tools/painel/` no esper-brain. App Starlette (vem com o `mcp`) servida por uvicorn num **socket Unix** `/run/esper-painel/painel.sock`, como o usuário `ricardo` (dono do clone e das credenciais do git). Publicado por `tailscale serve --https=8448`. Nenhuma porta TCP.
- **Quem entra:** cabeçalho `Tailscale-User-Login` (posto pelo `tailscale serve`) precisa estar em `ESPER_PAINEL_LOGINS` (lista separada por vírgula, em `/etc/esper-painel.env`). Sem o cabeçalho ou fora da lista → 403.
- **Escrita:** só `POST` com `Content-Type: application/json` e `Origin` igual a uma de `ESPER_PAINEL_ORIGENS` (anti-CSRF). Toda escrita passa pelas funções do `esper_mcp` (mesmas regras do chat) e termina com `gravar` (commit e push); falhou o gravar → a API devolve o erro e o painel mostra.
- **Quadro:** colunas na ordem: Família, Casa, Saúde, Pessoal, Patrimônio, ness, IONIC, Bekaa, Trabalho (sem empresa). Cartão: tema, etiquetas (estado se não for ativo; marca; frente; holding; cliente), próximo passo, prazo (vermelho vencido, âmbar até 7 dias), "parado há N dias" (> 30). Concluídos escondidos por padrão (botão "mostrar concluídos"). Busca por texto. Contador da entrada no topo.
- **Ações:** arrastar cartão para outra coluna = `mover_tema` (para IONIC pergunta a frente; patrimônio vai para a raiz da área); clicar abre o detalhe com o markdown do tema e os campos editáveis: estado, próximo passo, prazo, cliente (só trabalho), marca (só ness); "anotar" (Ideias soltas, Fatos e decisões, Perguntas em aberto, Prazos); "+ cartão" em cada coluna (= `criar_tema`, slug gerado do título). No celular, o detalhe tem "Mover para…" (arrastar é ruim no toque).
- **API:** `GET /api/quadro`, `GET /api/tema?caminho=`, `POST /api/mover`, `POST /api/campos`, `POST /api/anotar`, `POST /api/criar`. `GET /` = a página (um único `index.html`, sem build, sem CDN).
- **Visual:** estilo Trello (colunas lado a lado com rolagem horizontal, cartões brancos sobre fundo de cor), tema claro/escuro pelo sistema.

## 4. Fora de escopo
Visão de calendário, anexos, comentários, várias pessoas editando ao mesmo tempo (é só o Ricardo; um `gravar` por vez já é garantido pelo `flock` do `gravar.sh`).

## 5. Critérios de aceite
- `python3 -m pytest -q` verde (testes novos da API com cabeçalho, origem e cada ação; do `temas_atencao`; das skills).
- Na VPS: `https://srv-hermes.tail985643.ts.net:8448` abre o quadro com os temas atuais; arrastar um cartão gera um commit no esper-brain; o cron diário fica calado sem prazo perto; o semanal manda a revisão.
