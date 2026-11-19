# Etapa 4 — Teste do GBrain: plano de implementação

> **Para quem executa:** este plano roda de forma **inline**, com o Claude guiando e o Ricardo rodando os comandos na VPS ("você roda, eu guio"). As partes de código (harness) o Claude escreve e testa antes. Passos em `- [ ]`.

**Objetivo:** Medir se o GBrain responde melhor que a busca de texto pura no esper-brain, e a que custo, para decidir adotar / descartar / revalidar.

**Spec:** `docs/superpowers/specs/2026-11-19-etapa4-gbrain-design.md`

## Global Constraints

- Tudo do teste vive em `/home/ricardo/etapa4-gbrain/`; removível sem afetar produção. Nada de produção é tocado.
- VPS: o Claude dá os comandos, o Ricardo roda como root. Segredos nunca na tela nem no chat; a chave do OpenRouter entra por `read -rs` em arquivo de ambiente do teste.
- Todo bloco começa com `umask 022`; `umask 077` só entre parênteses.
- O clone de teste nunca destrava o git-crypt; o cofre é removido e commitado no clone antes de indexar.
- Commits (no esper-brain, só o harness e os resultados) terminam com:
  ```
  Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
  Claude-Session: https://claude.ai/code/session_01UEbxi9ixQ8HiepyRDMxftV
  ```

## Mapa de arquivos (no esper-brain)

| Arquivo | Responsabilidade |
|---|---|
| `tools/etapa4/perguntas.json` | As 10 perguntas, com gabarito e página-fonte esperada |
| `tools/etapa4/harness.py` | Roda uma camada (markdown / gbrain-search / gbrain-think) sobre as perguntas e grava uma linha por pergunta (achou a página, latência) num CSV |
| `tools/etapa4/tabela.py` | Junta os CSVs das camadas numa tabela markdown para o Ricardo marcar "resposta certa" e decidir |
| `tools/etapa4/test_harness.py` | Testes do harness e da tabela com um cérebro-fixture |
| `docs/etapa4-resultado.md` | (no fim) a tabela preenchida e a decisão |

Nada do GBrain (binário, índice pglite) entra no esper-brain; fica só na VPS, em `/home/ricardo/etapa4-gbrain/`.

---

### Task 1: perguntas.json e o harness da camada markdown

**Files:**
- Create: `tools/etapa4/perguntas.json`
- Create: `tools/etapa4/harness.py`
- Create: `tools/etapa4/test_harness.py`

**Interfaces:**
- Produces: `harness.py --camada markdown --brain <dir> --perguntas <json> --saida <csv>` grava CSV com colunas `n,camada,pergunta,fonte_esperada,paginas_achadas,fonte_bateu,latencia_ms`.
- `perguntas.json`: lista de `{"n", "pergunta", "fonte_esperada", "gabarito", "palavras_chave"}`.

- [ ] **Step 1: escrever `perguntas.json`** com as 10 perguntas do spec, cada uma com `fonte_esperada` (caminho relativo), `gabarito` (resposta curta certa) e `palavras_chave` (termos para a busca markdown).

- [ ] **Step 2: escrever o teste que falha** (`test_harness.py`): monta um cérebro-fixture em `tmp_path` com 3 arquivos (`empresas/bekaa.md` com "PJ", `pessoal/familia/sabrina.md` com "esposa", `pessoal/casa/bens.md` com "Ford Ranger"), um `perguntas.json` de 3 linhas, roda `harness.markdown(brain, perguntas)` e afirma que para a pergunta do carro `fonte_bateu` é True e aponta `pessoal/casa/bens.md`.

- [ ] **Step 3: rodar e ver falhar** — `python3 -m pytest -q tools/etapa4/test_harness.py` → FAIL (módulo/função não existe).

- [ ] **Step 4: implementar `harness.py`** — camada markdown: para cada pergunta, busca sem acento e sem caixa pelas `palavras_chave` em todos os `.md` do brain (menos `pessoal/cofre/`), ranqueia por nº de termos achados, devolve as 3 páginas de cima; `fonte_bateu` = a `fonte_esperada` está entre elas. Mede latência com `time.perf_counter`. Grava o CSV.

- [ ] **Step 5: rodar e ver passar** — `python3 -m pytest -q tools/etapa4/test_harness.py` → PASS.

- [ ] **Step 6: commit** — `git add tools/etapa4 && git commit` (mensagem: "feat(etapa4): perguntas e harness da camada markdown").

---

### Task 2: suporte a GBrain no harness (search e think) + tabela

**Files:**
- Modify: `tools/etapa4/harness.py` (camadas `gbrain-search` e `gbrain-think`)
- Create: `tools/etapa4/tabela.py`
- Modify: `tools/etapa4/test_harness.py`

**Interfaces:**
- `harness.py --camada gbrain-search` chama `gbrain search "<pergunta>" --json` e lê as páginas-fonte do JSON; `--camada gbrain-think` chama `gbrain think "<pergunta>"` e guarda a resposta + citações. Caminho do binário por `--gbrain <path>` (padrão `gbrain`).
- `tabela.py <csv...>` junta as camadas numa tabela markdown (uma linha por pergunta, colunas por camada: página bateu, latência; mais uma coluna vazia "resposta certa?" para o Ricardo marcar).

- [ ] **Step 1: teste que falha** — em `test_harness.py`, um teste que injeta um `gbrain` falso (script shell no `tmp_path` que ecoa um JSON fixo de resultados) e afirma que a camada `gbrain-search` extrai as páginas e preenche `fonte_bateu`. E um teste de `tabela.py` que, dados dois CSVs (markdown e gbrain-search), gera uma tabela com as duas colunas e a coluna "resposta certa?" vazia.

- [ ] **Step 2: rodar e ver falhar.**

- [ ] **Step 3: implementar** as duas camadas no `harness.py` (via `subprocess`, com timeout; parse do `--json`; para `think`, guarda `resposta` e `citacoes`) e o `tabela.py`.

- [ ] **Step 4: rodar e ver passar** — `python3 -m pytest -q tools/etapa4/test_harness.py`.

- [ ] **Step 5: commit** — "feat(etapa4): camadas gbrain-search/think no harness e a tabela".

---

### Task 3: VPS — instalar o GBrain e montar o cérebro de teste

Comandos para o Ricardo (root). Nada de produção é tocado.

- [ ] **Step 1: Bun + GBrain**
  ```bash
  umask 022
  install -d -o ricardo -g ricardo /home/ricardo/etapa4-gbrain
  sudo -u ricardo -H bash -lc 'curl -fsSL https://bun.sh/install | bash'
  sudo -u ricardo -H bash -lc 'export BUN_INSTALL=$HOME/.bun; export PATH=$BUN_INSTALL/bin:$PATH; bun --version && bun install -g github:garrytan/gbrain#stable && gbrain --version'
  ```
  Verificação: versão do Bun ≥ 1.4.4 e uma versão do `gbrain`. Se `gbrain` não estiver no PATH, usar `~/.bun/bin/gbrain` nos passos seguintes.

- [ ] **Step 2: clone de teste sem o cofre**
  ```bash
  umask 022
  EB=/home/ricardo/etapa4-gbrain/brain
  sudo -u ricardo -H git clone -q /home/ricardo/esper-brain "$EB"
  sudo -u ricardo -H git -C "$EB" rm -r -q pessoal/cofre
  sudo -u ricardo -H git -C "$EB" -c user.name=teste -c user.email=teste@local commit -q -m "teste etapa4: sem cofre"
  sudo -u ricardo -H bash -c "grep -rIl $'\\x00GITCRYPT' $EB || echo 'nenhum arquivo cifrado — ok'"
  ```
  Verificação: "nenhum arquivo cifrado — ok" e `pessoal/cofre` ausente.

- [ ] **Step 3: indexar (keyless) e medir**
  ```bash
  umask 022
  cd /home/ricardo/etapa4-gbrain
  sudo -u ricardo -H bash -lc 'export PATH=$HOME/.bun/bin:$PATH; cd /home/ricardo/etapa4-gbrain; gbrain init --pglite --no-embedding && gbrain sources add brain --path ./brain --federated --force && gbrain sync --all && gbrain doctor --json'
  ```
  Verificação: `gbrain doctor --json` sem erro; anotar quantas páginas foram indexadas.

---

### Task 4: rodar a camada markdown e a camada gbrain-search

- [ ] **Step 1: trazer o harness para a VPS** — no clone de produção do esper-brain do Ricardo, `git pull` traz `tools/etapa4/`. Copiar para fora do índice de teste:
  ```bash
  umask 022
  sudo -u ricardo -H git -C /home/ricardo/esper-brain pull -q
  install -d -o ricardo -g ricardo /home/ricardo/etapa4-gbrain/run
  cp /home/ricardo/esper-brain/tools/etapa4/*.py /home/ricardo/esper-brain/tools/etapa4/perguntas.json /home/ricardo/etapa4-gbrain/run/
  ```

- [ ] **Step 2: camada markdown**
  ```bash
  umask 022
  cd /home/ricardo/etapa4-gbrain/run
  sudo -u ricardo -H python3 harness.py --camada markdown --brain /home/ricardo/etapa4-gbrain/brain --perguntas perguntas.json --saida markdown.csv
  cat markdown.csv
  ```

- [ ] **Step 3: camada gbrain-search + RAM**
  ```bash
  umask 022
  cd /home/ricardo/etapa4-gbrain/run
  sudo -u ricardo -H bash -lc 'export PATH=$HOME/.bun/bin:$PATH; cd /home/ricardo/etapa4-gbrain/run; python3 harness.py --camada gbrain-search --gbrain "$(command -v gbrain)" --brain /home/ricardo/etapa4-gbrain/brain --perguntas perguntas.json --saida gbrain_search.csv'
  cat gbrain_search.csv
  # RAM do processo gbrain durante uma consulta
  sudo -u ricardo -H bash -lc 'export PATH=$HOME/.bun/bin:$PATH; /usr/bin/time -v gbrain search "quem e a esposa do ricardo" --json >/dev/null 2> /tmp/gbt.txt; grep "Maximum resident" /tmp/gbt.txt'
  ```
  Enviar ao Claude: `markdown.csv`, `gbrain_search.csv` e a linha de RAM. (São só nomes de página e latências; sem dados sensíveis.)

- [ ] **Step 4: decisão de seguir para a síntese** — o Claude monta a tabela parcial. Se a camada keyless do GBrain já não acrescentar nada sobre o markdown nas perguntas de grafo/semântica (4, 6, 7, 8), registrar e **parar aqui** (GBrain não compensa num cérebro magro; revalidar depois). Se acrescentar, seguir para a Task 5.

---

### Task 5: camada semântica + síntese (com a chave do OpenRouter)

Depende da Task 4 ter valido a pena. Primeiro o Claude descobre a configuração; depois o Ricardo roda.

- [ ] **Step 1: descobrir a config do modelo de chat/embeddings** — o Claude lê os docs do GBrain (`docs/INSTALL.md`, `docs/guides/data-ingestion.md`, `docs/guides/*`, `gbrain config --help`, `gbrain think --help`) e escreve os comandos exatos de: (a) habilitar embeddings com provedor OpenRouter (ou Voyage); (b) apontar o modelo de síntese para a chave do OpenRouter. Sem isso, não há `gbrain think`. Entregável: o bloco de comandos com os nomes de variável corretos.

- [ ] **Step 2: chave do OpenRouter no teste** (Ricardo)
  ```bash
  umask 022
  install -d -o ricardo -g ricardo -m 700 /home/ricardo/etapa4-gbrain/secret
  echo "cole a chave do OpenRouter e Enter (não aparece):"; read -rs OR
  printf 'OPENROUTER_API_KEY=%s\n' "$OR" | install -m 600 -o ricardo -g ricardo /dev/stdin /home/ricardo/etapa4-gbrain/secret/or.env; unset OR
  grep -c '^OPENROUTER_API_KEY=.' /home/ricardo/etapa4-gbrain/secret/or.env
  ```
  Verificação: `1`. (O nome exato da variável pode mudar conforme a Task 5 Step 1; ajustar.)

- [ ] **Step 3: reindexar com embeddings e rodar `gbrain think`** — comandos conforme o Step 1 (reinit/sync com embeddings + `harness.py --camada gbrain-think`). Enviar `gbrain_think.csv` e as respostas ao Claude. Anotar o custo pela OpenRouter (o Ricardo olha o painel da OpenRouter; valores não vêm para o chat).

---

### Task 6: tabela, decisão e limpeza

- [ ] **Step 1: montar a tabela** — `python3 tabela.py markdown.csv gbrain_search.csv [gbrain_think.csv] > tabela.md`. O Ricardo marca "resposta certa?" por pergunta/camada.

- [ ] **Step 2: decidir** — contra o critério do spec: GBrain adotado se acerta o que o markdown erra (4, 6, 7, 8) com custo/latência/RAM que compensam; descartado se empata e custa mais; revalidar se inconclusivo por cérebro magro. O Claude escreve `docs/etapa4-resultado.md` no esper-brain com a tabela e a decisão, e commita.

- [ ] **Step 3: limpar** — `rm -rf /home/ricardo/etapa4-gbrain` (apaga índice, clone e a chave do teste). Nada de produção foi tocado.

## Self-review

- Cobertura do spec: preparar cérebro sem cofre (Task 3), harness duas camadas + 10 perguntas (Tasks 1–2, 4), critério custo/latência/RAM (Tasks 4–5), decisão e limpeza (Task 6). ✓
- A config de síntese do GBrain é a única incógnita; tratada como passo de descoberta (Task 5 Step 1), não como placeholder. ✓
- Tipos consistentes: colunas do CSV iguais entre `harness.py` e `tabela.py`. ✓
