# Painel de temas e proatividade — plano

> **Para quem executa:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development (Tasks 1–4). A Task 5 roda na VPS (o Claude guia, o Ricardo roda).

**Objetivo:** quadro estilo Trello dos temas do esper-brain (ler e editar) e avisos proativos da Gabi (diário e semanal).
**Arquitetura:** `tools/esper_mcp.py` ganha `temas_atencao` e datas do git; `tools/painel/app.py` (Starlette) expõe uma API fina sobre as funções do MCP e serve `tools/painel/index.html`; skills `vigiar`; unit systemd e `tailscale serve` na VPS.
**Stack:** Python 3 (Starlette/uvicorn, que já vêm com o `mcp`), HTML/CSS/JS sem dependências, pytest (+ `httpx` só para o TestClient).
**Spec:** `docs/superpowers/specs/2026-11-24-painel-e-proatividade-design.md`

## Global Constraints
- Empresas: `ness` (papel "CEO"; marcas `forense.io`, `trustness`, `secops`), `ionic` (papel "CISO e acionista"; frentes `governanca`, `produto`, `operacao`, `pessoas`, `acionista`), `bekaa` (papel "titular"). Não existe `pf`.
- Colunas do quadro, nesta ordem e com estes ids: `familia`, `casa`, `saude`, `pessoal`, `patrimonio`, `ness`, `ionic`, `bekaa`, `trabalho` (rótulos: Família, Casa, Saúde, Pessoal, Patrimônio, ness, IONIC, Bekaa, Trabalho (sem empresa)).
- Toda escrita do painel passa pelas funções do `esper_mcp` e termina em `gravar(...)`; mensagens de commit começam com `painel: `.
- Hoje e horas: America/Sao_Paulo (`esper_mcp.FUSO`, `esper_mcp._agora()`).
- Testes: `python3 -m pytest -q` na raiz; os da API pulam (`pytest.importorskip("httpx")`) se faltar httpx.
- Texto ao usuário em português do Brasil, frases curtas.

---

### Task 1: modelo (sem pf, com secops), datas do git e `temas_atencao`
**Files:** `tools/esper_mcp.py`, `projetos/_modelo.md`, `skills/capturar/SKILL.md`, `AGENTS.md`, `mapa.md`, `tests/test_esper_mcp.py`, `tests/test_skills.py`
**Produces:**
- `EMPRESAS = {"ness": "CEO", "ionic": "CISO e acionista", "bekaa": "titular"}`; `MARCAS = {"ness": ("forense.io", "trustness", "secops")}`.
- `_mudancas() -> dict[str, str]`: caminho relativo → data `AAAA-MM-DD` do último commit que tocou o arquivo, em UMA chamada `git -C RAIZ log --format=%x00%cs --name-only -- projetos` (o primeiro visto de cada caminho vence); arquivo sem commit (novo) → data do mtime. Sem git (erro) → mtime para todos. `listar_temas` passa a usar isto na coluna "última mudança".
- `temas_atencao(dias_prazo: int = 7, dias_parado: int = 30) -> str` (JSON, `ensure_ascii=False`): `{"hoje": "AAAA-MM-DD", "vencido": [...], "prazo_perto": [...], "parado": [...], "sem_passo": [...], "entrada": {"pendentes": N, "mais_antiga": "AAAA-MM-DD" | null}}`; cada item `{"caminho","tema","area","empresa","prazo","proximo_passo","mudanca","dias"}` (`dias` = dias até o prazo (negativo se vencido) ou dias parado). Só temas `estado` ativo (vazio conta como ativo). Prazo inválido é ignorado. Registrar no `servidor()`.
**Steps (TDD):** testes primeiro: pf recusado e secops aceito em `_pasta_do_tema`; `_mudancas` com commits em datas diferentes (use `GIT_COMMITTER_DATE` no fixture) e arquivo novo não commitado; `temas_atencao` com um vencido, um em 3 dias, um parado (commit antigo), um sem passo, um concluído (ignorado) e 2 pedaços na entrada. Atualizar `_modelo.md` (comentários de empresa/papel/marca), `capturar` (empresas: ness, ionic, bekaa; freelancer = bekaa com cliente; marcas da ness: forense.io, trustness, secops), AGENTS regra 9 e `mapa.md` (tirar `pf/`; Bekaa inclui freelancer). `tests/test_skills.py`: `temas_atencao` em FERRAMENTAS. Commit: `feat(esper_mcp): sem pf, secops, datas do git e temas_atencao`.

### Task 2: API do painel
**Files:** create `tools/painel/__init__.py`, `tools/painel/app.py`, `tests/test_painel_api.py`; modify `tools/requirements-mcp.txt` (+ `starlette`, `uvicorn`)
**Consumes:** `esper_mcp` (`RAIZ`, `_arquivos_de_tema`, `_frontmatter`, `_campo`, `_mudancas`, `ler`, `criar_tema`, `mover_tema`, `anotar`, `gravar`, `entrada_ler`, `Recusa`, `AREAS`, `EMPRESAS`, `MARCAS`, `FRENTES_IONIC`, `HOLDINGS`, `_agora`).
**Produces:** `criar_app(raiz: Path, logins: set[str], origens: set[str]) -> Starlette` e `main()` (lê `ESPER_BRAIN`, `ESPER_PAINEL_LOGINS`, `ESPER_PAINEL_ORIGENS`, `ESPER_PAINEL_SOCK` (padrão `/run/esper-painel/painel.sock`); roda `uvicorn.run(app, uds=sock, proxy_headers=False)`; `python3 -m tools.painel.app` ou `python3 tools/painel/app.py`).
- Toda rota exige `Tailscale-User-Login` em `logins` → senão 403 `{"erro":"proibido"}`. POST exige `application/json` e `Origin` em `origens` → senão 403 `{"erro":"origem"}`.
- `GET /` → `index.html` (mesma pasta), `Cache-Control: no-store`.
- `GET /api/quadro` → `{"colunas":[{"id","rotulo","cartoes":[...]}], "entrada": N, "hoje": "AAAA-MM-DD", "frentes": [...], "marcas": [...], "holdings": [...]}`. Cartão: `{"caminho","tema","estado","proximo_passo","prazo","cliente","marca","frente","holding","mudanca","parado_dias"}`. Coluna = `empresa` se área trabalho e empresa ∈ EMPRESAS; `trabalho` se trabalho sem empresa; senão a área (tema sem área conhecida → coluna `pessoal`). Ordem dos cartões: vencidos/prazo mais perto primeiro, depois sem prazo por mudança mais recente.
- `GET /api/tema?caminho=` → `{"caminho","texto"}` via `ler` (Recusa → 400 `{"erro": msg}`).
- `POST /api/mover {caminho, coluna, frente?, holding?}` → coluna → (area, empresa); `ionic` exige `frente`; chama `mover_tema` e `gravar("painel: move <tema>")`. Mesmo lugar → 200 sem mudança.
- `POST /api/campos {caminho, estado?, proximo_passo?, prazo?, cliente?, marca?}` → valida (`estado` ∈ ativo|parado|concluído; `prazo` vazio ou AAAA-MM-DD; `cliente` só em trabalho; `marca` só em ness e ∈ MARCAS["ness"] ou vazia; textos sem quebra de linha, ≤ 300 caracteres); só arquivos de tema (dentro de `projetos/`, não `_*`); grava via `_campo` e `gravar("painel: <tema>")`. `prazo` é gravado sem aspas no formato do modelo (`prazo: 2027-03-31`).
- `POST /api/anotar {caminho, secao, texto}` → `secao` ∈ "Ideias soltas", "Fatos e decisões", "Perguntas em aberto", "Prazos"; prefixa `AAAA-MM-DD: ` e chama `anotar` + `gravar`.
- `POST /api/criar {coluna, tema, frente?, holding?, cliente?}` → slug = tema sem acento, minúsculas, não alfanumérico → `-`, máx. 60, colisão → sufixo `-2`, `-3`; `criar_tema` + `gravar`. Devolve o cartão.
- Erros de gravar (saída que não começa com `gravado:`) → 502 `{"erro": saída}`; `Recusa` → 400.
**Tests:** fixture com bare remote + clone (copie o padrão de `tests/test_esper_mcp.py::cerebro`), `TestClient` com `base_url="https://srv-hermes.x.ts.net:8448"`; casos: sem cabeçalho 403, login fora 403, POST sem Origin 403, quadro com colunas na ordem e cartões no lugar certo, mover para ionic sem frente 400 e com frente 200 + commit no remoto, campos (prazo inválido 400, cliente fora de trabalho 400), anotar, criar com colisão de slug, tema dentro de `pessoal/cofre/` recusado. Commit: `feat(painel): API do quadro de temas`.

### Task 3: página do quadro
**Files:** create `tools/painel/index.html`, `tests/test_painel_pagina.py`
**Consumes:** a API da Task 2.
- Um arquivo só (HTML + CSS + JS), sem dependências externas nem CDN, ≤ 60 KB.
- Topo: título "Temas", busca, botão "mostrar concluídos", contador "entrada: N", botão recarregar. Quadro: colunas com rolagem horizontal (largura ~272 px), cabeçalho com nome e contagem, cartões, botão "+ cartão" no pé (abre campo de título; Enter cria).
- Cartão: tema; etiquetas coloridas (estado se ≠ ativo, marca, frente, holding, cliente); próximo passo (1–2 linhas); prazo como chip (vermelho vencido, âmbar ≤ 7 dias); "parado há N dias" quando > 30.
- Arrastar e soltar (HTML5 drag events) entre colunas → `POST /api/mover`; soltar na IONIC abre a escolha da frente; durante o envio o cartão fica esmaecido; erro → toast e volta ao lugar.
- Clique abre painel lateral/modal com o texto do tema (markdown simples renderizado: títulos `#`, listas `-`, negrito; escapar HTML), campos editáveis (estado, próximo passo, prazo `type=date`, cliente, marca), "Salvar", área "Anotar" (seção + texto), e "Mover para…" (select de colunas; obrigatório no celular).
- Todo `fetch` POST manda `Content-Type: application/json`; o navegador põe o `Origin`. Depois de cada ação, recarrega o quadro. Mensagens em toast. Claro/escuro por `prefers-color-scheme`. Acessível: botões com texto, foco visível, `Esc` fecha o modal.
**Tests:** `GET /` devolve a página com `<title>Temas</title>`; o JS embutido passa em `node --check` (extraia o `<script>` para um arquivo temporário; pule se não houver `node`); a página não referencia `http://` nem `https://` externos. Commit: `feat(painel): quadro estilo Trello`.

### Task 4: skill `vigiar` e deploy do painel
**Files:** create `skills/vigiar/SKILL.md`, `deploy/painel/esper-painel.service`, `deploy/painel/README.md`; modify `skills/digestao/SKILL.md` (usar `temas_atencao` no lugar de varrer à mão, se fizer sentido), `mapa.md` (linha do `skills/` + linha "Painel de temas" na tabela de endereços: https://srv-hermes.tail985643.ts.net:8448), `tests/test_skills.py` (`vigiar` na lista de skills).
- `vigiar`: frontmatter padrão; modos **diário** (só `vencido` e `prazo_perto` com `dias` ≤ 3; nada → responder exatamente `[SILENT]`, que o cron do Hermes não entrega) e **semanal** (revisão por área conforme a spec §2, máx. 15 linhas, termina com "Qual destes você quer retomar?"). Usa só `temas_atencao` e `listar_temas`; nunca grava.
- `esper-painel.service`: `User=ricardo`, `Group=ricardo`, `RuntimeDirectory=esper-painel` (0755), `EnvironmentFile=/etc/esper-painel.env`, `Environment=ESPER_BRAIN=/home/ricardo/esper-brain`, `ExecStart=/home/ricardo/.local/share/esper-brain-mcp/bin/python /home/ricardo/esper-brain/tools/painel/app.py`, `Restart=on-failure`, `UMask=0002`; endurecimento compatível com git push (sem `ProtectHome=` que bloqueie /home/ricardo; `NoNewPrivileges=yes`, `PrivateTmp=yes`).
- `deploy/painel/README.md`: os comandos de instalação (env file com `ESPER_PAINEL_LOGINS` e `ESPER_PAINEL_ORIGENS=https://srv-hermes.tail985643.ts.net:8448`, install da unit, `systemctl enable --now`, `tailscale serve --bg --https=8448 unix:/run/esper-painel/painel.sock`, teste com curl no socket).
- Commit: `feat: skill vigiar e deploy do painel`.

### Task 5: VPS (Ricardo roda)
pull; `pip install` do requirements no venv do MCP; env file; unit; `tailscale serve 8448`; crons `vigiar-diario` (`40 8 * * *`) e `vigiar-semanal` (`50 8 * * 1`) com `--skill vigiar`; incluir `temas_atencao` no include do `esper_brain` (o `configurar_hermes.py` atualizado); restart do gateway; testar o quadro e um arraste.
