# Pendências finais da reestruturação: plano de implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fechar tudo o que ficou aberto depois das etapas 1 a 3 (Gabi no esper-brain, gabi-finance separado, gabi-brain como coletor), menos a chave do modelo (OpenRouter), que o Ricardo resolve sozinho.

**Architecture:** Três repositórios na mesma VPS Contabo: `gabi-finance` (dinheiro), `gabi-brain` (coletor: agenda, e-mail, Teams, Paperless, atividades) e `esper-brain` (cérebro em markdown, acessado pelo MCP `esper_brain`). Código muda aqui (com testes e commit); a VPS muda só por comandos que o Ricardo roda ("você roda, eu guio").

**Tech Stack:** Python 3.12, FastAPI, SQLite, FastMCP, React 19 + Vite (painéis), systemd, Hermes Agent, git-crypt, GitHub (`resper1965/*`).

**Spec:** `docs/superpowers/specs/2026-11-17-esper-brain-design.md` (este repositório) e, para o financeiro, `gabi-finance/docs/adr/039-corte-gabi-finance.md`.

## Global Constraints

- VPS: o Claude escreve os comandos exatos; o Ricardo roda como root. O Claude nunca roda nada na VPS.
- Segredos nunca aparecem na tela nem no chat (`read -rs`, `--gravar`, `stat`/`grep -c` para conferir). Números financeiros e conteúdo de documentos não vêm para o chat.
- Todo bloco de comandos para a VPS começa com `umask 022`. Um `umask 077` só dentro de parênteses: `(umask 077; ...)`.
- Nada é apagado na VPS sem pedido explícito; mudanças em arquivos de configuração têm backup `*.bak-<motivo>-AAAA-MM-DD`.
- Commits terminam com:
  ```
  Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
  Claude-Session: https://claude.ai/code/session_01UEbxi9ixQ8HiepyRDMxftV
  ```
- Push só em branch de trabalho; merge na `main` só por PR, depois de testes verdes.
- Testes: gabi-brain e gabi-finance com `python -m pytest -q` e, no painel, `npx vitest run && npm run build`. O teste `tests/test_obter_token_teams.py::test_main_gravar_falhando_nao_mostra_o_token` falha quando roda como root (falha conhecida, não bloqueia).

**Fora deste plano:** chave do modelo (OpenRouter) e a chave nova do agente GPT (o Ricardo resolve); **etapa 4** (GBrain e Honcho), que é outro subsistema e precisa de spec própria (brainstorming depois que este plano fechar).

---

## Mapa de arquivos

| Repositório | Arquivo | Muda |
|---|---|---|
| gabi-brain | `gabi/mcp/ferramentas_prop.py` | nova ferramenta `documentos_novos` |
| gabi-brain | `gabi/mcp/servidor.py` | registra a ferramenta no mapa de frescor |
| gabi-brain | `tests/mcp/test_documentos.py` | testes da ferramenta |
| gabi-brain | `docs/fontes/hermes.md` | lista oficial do include ganha `documentos_novos` |
| esper-brain | `skills/digestao/SKILL.md` | seção "Documentos novos" no hot |
| gabi-finance | `deploy/instalar.sh` | `umask 022` no início |
| (VPS) | `/etc/gabi-finance/nibo.env`, `/etc/gabi/google.env`, `~/.hermes/config.yaml`, remotes dos clones | operação |

---

### Task 1: gabi-brain: ferramenta `documentos_novos`

**Files:**
- Modify: `gabi/mcp/ferramentas_prop.py` (dicionário `ESCOPOS` no topo; nova ferramenta logo depois de `documentos_buscar`)
- Modify: `gabi/mcp/servidor.py` (`FONTES_DA_FERRAMENTA`, entrada `"documentos_novos": ()` junto de `documentos_buscar`)
- Modify: `docs/fontes/hermes.md` (acrescentar `- documentos_novos` logo abaixo de `- documentos_buscar`)
- Test: `tests/mcp/test_documentos.py`

**Interfaces:**
- Produces: ferramenta MCP `documentos_novos(dias: int = 1, limite: int = 20) -> dict` com `{"desde": "AAAA-MM-DD", "itens": [{"id", "titulo", "adicionado_em", "criado_em", "referencia"}]}`; escopo `docs`. Consumida pela Task 2 (skill `digestao`).

Branch: a partir de `sem-pessoal` (`git checkout sem-pessoal && git pull && git checkout -b documentos-novos`).

- [ ] **Step 1: Escrever os testes que falham** (acrescentar ao fim de `tests/mcp/test_documentos.py`)

```python
def test_documentos_novos_pede_ao_paperless_so_os_adicionados_depois_da_data(banco, token):
    from datetime import timedelta
    falso = PaperlessFalso(docs=[{"id": 7, "title": "CRLV Ranger", "created": "2026-11-17", "added": "2026-11-18T09:00:00-03:00", "tags": [], "content": "x"}])
    with _cliente(banco, falso) as cli:
        d = chamar(cli, token, "documentos_novos", dias=2)["dados"]
    desde = (AGORA - timedelta(days=2)).date().isoformat()
    assert d["desde"] == desde
    gets = [c[1] for c in falso.chamadas if c[0] == "GET" and c[1].startswith("/api/documents/?")]
    assert gets and f"added__date__gt={desde}" in gets[0] and "ordering=-added" in gets[0]
    assert d["itens"] == [{"id": 7, "titulo": "CRLV Ranger", "adicionado_em": "2026-11-18T09:00:00-03:00", "criado_em": "2026-11-17",
                           "referencia": {"paperless_id": 7, "titulo": "CRLV Ranger", "criado_em": "2026-11-17"}}]


def test_documentos_novos_recusa_dias_fora_da_faixa(cli, token):
    r = chamar(cli, token, "documentos_novos", dias=31)
    assert r.get("erro") or r.get("status") == "erro" or "dias" in str(r)


def test_documentos_novos_exige_escopo_docs(banco):
    c = conectar(banco)
    t = emitir(c, "sem-docs", ["trabalho"])
    c.close()
    with _cliente(banco, PaperlessFalso(docs=[])) as cli:
        r = chamar(cli, t, "documentos_novos", dias=1)
    assert "sem_escopo" in str(r)
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `python -m pytest -q tests/mcp/test_documentos.py -k documentos_novos`
Expected: FAIL (ferramenta `documentos_novos` desconhecida). Se o formato de erro de `chamar` for diferente do assumido no segundo e no terceiro teste, ajuste só a asserção de formato olhando como `test_servidor.py` testa `sem_escopo` e `ValueError`: o comportamento exigido (recusar 31 dias; exigir `docs`) não muda.

- [ ] **Step 3: Implementar**

Em `ESCOPOS`, acrescentar `"documentos_novos": "docs",`. Logo depois da função `documentos_buscar` (dentro do mesmo `registrar`), acrescentar:

```python
    @srv.tool()
    def documentos_novos(dias: int = 1, limite: int = 20) -> dict:
        """Documentos que ENTRARAM no Paperless nos últimos `dias` (1 a 30), do mais novo ao mais antigo: id, título, quando entrou (`adicionado_em`), data do documento (`criado_em`) e a referência. Use na digestão diária ("o que entrou ontem"). Só leitura; para ler, documentos_texto; para o arquivo, documentos_baixar."""
        def f(con, agora):
            if isinstance(dias, bool) or not isinstance(dias, int) or not 1 <= dias <= 30:
                raise ValueError("dias deve ser um inteiro de 1 a 30")
            if isinstance(limite, bool) or not isinstance(limite, int) or not 1 <= limite <= 50:
                raise ValueError("limite deve ser um inteiro de 1 a 50")
            desde = (agora - timedelta(days=dias)).date().isoformat()
            try:
                docs = _paperless(paperless).docs(added__date__gt=desde, ordering="-added", page_size=limite, limite=limite)
            except ErroPaperless as e:
                raise ErroFerramenta("fonte_indisponivel", str(e)) from None
            return {"desde": desde, "itens": [{"id": d["id"], "titulo": d.get("title"), "adicionado_em": d.get("added"),
                                               "criado_em": d.get("created"), "referencia": _referencia(d)} for d in docs[:limite]]}
        return executar("documentos_novos", f)
```

No topo do arquivo, `from datetime import timedelta`. Em `gabi/mcp/servidor.py`, no `FONTES_DA_FERRAMENTA`, acrescentar `"documentos_novos"` à tupla que já tem `"documentos_buscar"`. Em `docs/fontes/hermes.md`, acrescentar `- documentos_novos` abaixo de `- documentos_buscar`.

- [ ] **Step 4: Rodar os testes**

Run: `python -m pytest -q tests/mcp/test_documentos.py` e depois a suíte inteira `python -m pytest -q`
Expected: os 3 novos passam. Se algum teste de inventário (contagem de ferramentas, `docs/api.md`, lista do Hermes) acusar a ferramenta nova, atualize o inventário do jeito que o teste pede (há gerador em `tools/` para `docs/api.md`/`openapi.json`; veja a mensagem do teste). Única falha aceita: a conhecida do Global Constraints.

- [ ] **Step 5: Commit e push da branch**

```bash
git add gabi/mcp/ferramentas_prop.py gabi/mcp/servidor.py docs/fontes/hermes.md tests/mcp/test_documentos.py docs/
git commit -m "feat(mcp): documentos_novos lista o que entrou no Paperless nos últimos N dias (para a digestão)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01UEbxi9ixQ8HiepyRDMxftV"
git push -u origin documentos-novos
```

---

### Task 2: esper-brain: a digestão traz "Documentos novos"

**Files:**
- Modify: `skills/digestao/SKILL.md`

**Interfaces:**
- Consumes: `documentos_novos(dias=1)` da Task 1 (MCP `gabi_brain`).

- [ ] **Step 1:** Em "## 1. Coletar", acrescentar a linha `- documentos_novos(dias=1)` (só título, data e `paperless:N`; não leia o texto).
- [ ] **Step 2:** No modelo do hot.md, entre "Prazos e vencimentos" e "Temas parados", acrescentar:

```
## Documentos novos (ontem)
- paperless:N · <título> · <data do documento>
```

e, logo abaixo do modelo, a regra: "Se um documento novo combina claramente com um tema (`listar_temas`, título com a mesma palavra-chave), escreva `→ tema <slug>?` no fim da linha; nunca ligue sozinho (ligar é na skill `capturar`, depois do sim)."
- [ ] **Step 3:** No passo 5 (resposta de uma linha), acrescentar `, D documentos novos` depois de `K pendências novas`.
- [ ] **Step 4:** Rodar `python3 -m pytest -q tests/` (não deve mudar nada) e commitar:

```bash
git add skills/digestao/SKILL.md
git commit -m "feat(digestao): documentos novos do Paperless no hot.md" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01UEbxi9ixQ8HiepyRDMxftV"
git push
```

---

### Task 3: gabi-brain: PRs para a `main`

A produção roda branches (`sem-financeiro` → `sem-pessoal`); a `main` do GitHub está atrás. Fechar isso evita instalar código errado no futuro.

- [ ] **Step 1:** Conferir que `documentos-novos` contém `sem-pessoal`, que contém `sem-financeiro`: `git merge-base --is-ancestor sem-pessoal documentos-novos && git merge-base --is-ancestor sem-financeiro sem-pessoal && echo ok`. Expected: `ok`.
- [ ] **Step 2:** Abrir o PR `documentos-novos → main` com `gh pr create --base main --head documentos-novos --title "sem-financeiro + sem-pessoal + documentos_novos (produção desde 17-18/11)" --body "<resumo dos 3 blocos e dos testes>"`, terminando o corpo com a linha de atribuição do Claude Code.
- [ ] **Step 3:** Se o GitHub acusar conflito com a `main`, resolver no branch (`git merge origin/main`), rodar a suíte inteira, push. Expected: PR sem conflito e verde.
- [ ] **Step 4:** Mostrar o PR ao Ricardo e fazer o merge só com o "pode" dele (`gh pr merge --merge`).

---

### Task 4: VPS: instalar o gabi-brain novo e ligar a ferramenta

Comandos para o Ricardo (root). Depende das Tasks 1 a 3.

- [ ] **Step 1: atualizar o clone, compilar o painel e instalar**

```bash
umask 022
GB=/home/ricardo/gabi-brain
git -c safe.directory=$GB -C $GB fetch -q origin && git -c safe.directory=$GB -C $GB checkout -q main && git -c safe.directory=$GB -C $GB pull -q --ff-only
chmod -R u+rwX,go+rX $GB && chown -R ricardo:ricardo $GB
git -c safe.directory=$GB -C $GB log --oneline -1
sudo -u ricardo -H bash -c "cd $GB/painel && npm ci --silent && npm run build --silent" >/dev/null && ls -l $GB/gabi/painel/index.html
/home/ricardo/instalar-brain.sh
sleep 20; systemctl is-active gabi-brain-api gabi-brain-mcp
systemctl is-enabled gabi-brain-extratos.timer gabi-brain-saldos.timer gabi-brain-notas.timer gabi-brain-anexos.timer
```

Expected: commit do merge; `index.html`; `Instalado.` e a linha "Virada do gabi-finance ativa..."; dois `active`; quatro `disabled`.

- [ ] **Step 2: pôr `documentos_novos` no include do Hermes e atualizar o esper-brain**

```bash
umask 022
H=/home/ricardo/.hermes/config.yaml
sudo -u ricardo cp -p $H $H.bak-documentos-novos-$(date +%F)
sudo -u ricardo -H python3 - <<'PY'
import re
p = "/home/ricardo/.hermes/config.yaml"
t = open(p, encoding="utf-8").read().split("\n")
i = next(k for k, l in enumerate(t) if re.match(r"^\s*-\s*documentos_buscar\s*$", l))
if not any(re.match(r"^\s*-\s*documentos_novos\s*$", l) for l in t):
    t.insert(i + 1, t[i].replace("documentos_buscar", "documentos_novos"))
open(p, "w", encoding="utf-8").write("\n".join(t))
import yaml
inc = yaml.safe_load(open(p))["mcp_servers"]["gabi_brain"]["tools"]["include"]
print("documentos_novos no include:", "documentos_novos" in inc)
PY
sudo -u ricardo -H git -C /home/ricardo/esper-brain pull -q
systemctl restart hermes-gateway; sleep 5; systemctl is-active hermes-gateway
```

Expected: `documentos_novos no include: True` e `active`. (Se aparecer `StopIteration`, `documentos_buscar` não está no include: me mande a saída.)

- [ ] **Step 3: aceite.** Telegram: `/new` e `roda a digestão agora`. Expected: a linha final cita "documentos novos"; o commit `digestão ...` no GitHub tem a seção "Documentos novos (ontem)" no `hot.md`.

---

### Task 5: Gmail (resper@gmail.com) e `promessas_candidatas`

A `promessas_candidatas` só falha inteira quando nenhuma conta de e-mail lê; o token do Gmail pessoal venceu em 17/11. Primeiro o token, depois a prova.

- [ ] **Step 1: ver o estado das contas** (root; não mostra segredo):

```bash
umask 022
sudo -u gabibrain /opt/gabi-brain/venv/bin/python - <<'PY'
import sqlite3
c = sqlite3.connect("file:/var/lib/gabi-brain/gabi.db?mode=ro", uri=True)
for r in c.execute("select conta, provedor, estado, substr(coalesce(ultimo_erro,''),1,80) from email_fonte order by id"): print(r)
PY
journalctl -u gabi-brain-mcp --since "2026-11-18 08:50" --until "2026-11-18 09:00" --no-pager -o cat | grep -iE 'promessas|invalid_grant|ErroGoogle|ErroGraph' | cut -c1-160 | tail -5
```

Expected: a(s) conta(s) com erro de credencial; anote quais.

- [ ] **Step 2: renovar o token de cada conta com erro**, uma por vez, no terminal da VPS (o navegador abre no seu computador; cole a URL final):

```bash
umask 022
cd /home/ricardo/gabi-brain && sudo /opt/gabi-brain/venv/bin/python -m tools.obter_token_google resper@gmail.com --env /etc/gabi/google.env --gravar
systemctl restart gabi-brain-fontes
```

Expected: a ferramenta confirma os escopos e grava `GOOGLE_REFRESH_RESPER_GMAIL_COM` sem mostrar o token. Se a conta com erro for a da ness (Graph), use o passo de `obter_token_teams` do runbook do brain (`#graph-ness`).

- [ ] **Step 3: provar.** `sudo systemctl start gabi-brain-correio.service; journalctl -u gabi-brain-correio -n 5 -o cat` (sem erro de credencial) e, no Telegram, `quais promessas eu fiz por e-mail esta semana?`. Expected: a Gabi responde com itens (ou "nenhuma"), não com "não consegui ler".
- [ ] **Step 4: se ainda falhar com credencial OK**, voltar ao Claude com a saída do Step 1 e do log; aí vira tarefa de código (TDD no `gabi/mcp/ferramentas_assistente.py`, reproduzindo o erro num teste com a ponte falsa antes de corrigir).

---

### Task 6: Nibo (token novo)

- [ ] **Step 1:** No Nibo (web), gerar um token de API novo (Configurações › Integrações/API). Não cole aqui.
- [ ] **Step 2: gravar sem mostrar** (root):

```bash
umask 022
F=/etc/gabi-finance/nibo.env
cp -p $F $F.bak-$(date +%F) 2>/dev/null || true
echo "cole o token do Nibo e tecle Enter (não aparece):"; read -rs T
grep -v '^NIBO_TOKEN=' $F 2>/dev/null > $F.novo || true; printf 'NIBO_TOKEN=%s\n' "$T" >> $F.novo; unset T
install -m 600 -o root -g root $F.novo $F && rm -f $F.novo
grep -c '^NIBO_TOKEN=.' $F; stat -c '%U %a' $F
systemctl restart gabi-finance-fontes
systemctl start gabi-finance-notas; journalctl -u gabi-finance-notas -n 10 --no-pager -o cat | cut -c1-160
```

Expected: `1`, `root 600`, e o log das notas sem `nao_configurada` nem erro de autenticação.

---

### Task 7: mcp.ai: as 2 contas que nunca leem

- [ ] **Step 1: quais são** (só nomes e estado, sem saldo):

```bash
umask 022
runuser -u gabifinance -- /opt/gabi-finance/venv/bin/python - <<'PY'
import sqlite3
c = sqlite3.connect("file:/var/lib/gabi-finance/gabi.db?mode=ro", uri=True)
for r in c.execute("select banco, nome, tipo, status_conexao, ult_sync_ok from conta_estado where status_conexao like 'ERRO%' order by banco"): print(r)
PY
```

Expected: 2 linhas (banco, nome da conta, tipo, `ERRO_LEITURA: <exceção>`, última leitura boa).

- [ ] **Step 2: decidir com o Ricardo, conta a conta** (uma pergunta, com recomendação):
  - consentimento Open Finance vencido ou revogado (normal após 12 meses) → reconectar a instituição no painel do mcp.ai;
  - conta encerrada ou que não interessa → no painel do gabi-finance, Cadastros › Contas, marcar como **não acompanhar** (estado `nao`), sem apagar histórico.
- [ ] **Step 3: provar.** `systemctl start gabi-finance-extratos` e, depois de terminar, a linha `extratos: ... falhas=[] conferida=True` (`journalctl -u gabi-finance-extratos -n 3 -o cat`). Expected: `falhas=[]` e `conferida=True`.

---

### Task 8: gabi-finance: publicar o painel novo (laudo)

**Files:**
- Modify: `deploy/instalar.sh` (gabi-finance): `umask 022` logo depois de `set -euo pipefail`.

- [ ] **Step 1 (aqui):** no clone do gabi-finance, `git checkout redesign-laudo && git merge --ff-only main` (deve ser fast-forward). Acrescentar a linha `umask 022` com o comentário `# um umask 077 herdado deixava o código ilegível para o usuário do serviço (18/11/2026)` depois de `set -euo pipefail` em `deploy/instalar.sh`, e um teste em `tests/` que leia o instalador e afirme `"\numask 022\n" in texto` (siga o padrão de qualquer teste existente que leia `deploy/instalar.sh`; se não houver, crie `tests/test_instalar.py` com `pathlib.Path("deploy/instalar.sh").read_text()`).
- [ ] **Step 2:** `python -m pytest -q` e `cd painel && npx vitest run && npm run build`. Expected: verdes.
- [ ] **Step 3:** commit, `git push -u origin redesign-laudo`, PR `redesign-laudo → main` com as capturas antes/depois de `.impeccable/review/` descritas no corpo; merge só com o "pode" do Ricardo.
- [ ] **Step 4 (VPS, root):**

```bash
umask 022
GF=/home/ricardo/gabi-finance
git -c safe.directory=$GF -C $GF fetch -q origin && git -c safe.directory=$GF -C $GF checkout -q main && git -c safe.directory=$GF -C $GF pull -q --ff-only
chmod -R u+rwX,go+rX $GF && chown -R ricardo:ricardo $GF
sudo -u ricardo -H bash -c "cd $GF/painel && npm ci --silent && npm run build --silent" >/dev/null && ls -l $GF/gabi/painel/index.html
cd $GF && bash deploy/instalar.sh --confirmo-backup-exportado | tail -5
sleep 10; systemctl is-active gabi-finance-api gabi-finance-mcp
```

Expected: `index.html` novo; instalador sem erro; dois `active`.
- [ ] **Step 5: aceite.** Abrir `https://gabi-brain.tail985643.ts.net:8446` no computador: Resumo com "Conclusão", achados RS-0N, carimbos; passar o mouse num código abre a origem do número. E no celular, a mesma tela.

---

### Task 9: endurecimento de credenciais

- [ ] **Step 1: 9.7 da virada: tirar dinheiro do token do Hermes no brain** (root):

```bash
umask 022
cd /opt/gabi-brain
runuser -u gabibrain -- ./venv/bin/python -m gabi.mcp.tokens --banco /var/lib/gabi-brain/gabi.db listar
```

Anotar o id e os escopos do token `hermes`. Depois, com os escopos anotados **sem** `fin` e **sem** `propostas`:

```bash
runuser -u gabibrain -- ./venv/bin/python -m gabi.mcp.tokens --banco /var/lib/gabi-brain/gabi.db escopos <id> <escopos sem fin e sem propostas>
```

Expected: `listar` mostra o token com os escopos novos. Aceite: no Telegram, `o que tenho hoje?` e `como está a fila de e-mail?` continuam respondendo. Se algo do brain parar (`sem_escopo`), devolver os escopos anotados.

- [ ] **Step 2: trocar o token amplo do `gh` (root) por chaves de deploy só de leitura.** Enquanto o `gh` ainda está logado:

```bash
umask 022
for R in gabi-brain gabi-finance; do
  sudo -u ricardo ssh-keygen -q -t ed25519 -N '' -C "vps $R ro" -f /home/ricardo/.ssh/$R
  gh repo deploy-key add /home/ricardo/.ssh/$R.pub -R resper1965/$R --title vps-ro
  sudo -u ricardo tee -a /home/ricardo/.ssh/config >/dev/null <<CFG

Host github-$R
  HostName github.com
  User git
  IdentityFile ~/.ssh/$R
  IdentitiesOnly yes
CFG
  git -c safe.directory=/home/ricardo/$R -C /home/ricardo/$R remote set-url origin github-$R:resper1965/$R.git
  sudo -u ricardo -H git -C /home/ricardo/$R fetch -q && echo "$R: fetch ok"
done
```

Expected: `gabi-brain: fetch ok` e `gabi-finance: fetch ok`. Daqui em diante os `git fetch/pull` da VPS rodam como `ricardo` (`sudo -u ricardo -H git -C ...`), sem `safe.directory`.

- [ ] **Step 3: desligar o `gh` do root** (só depois do Step 2 ok): `gh auth logout -h github.com` e `git config --global --unset-all credential.https://github.com.helper || true`. Expected: `gh auth status` diz que não está logado; os três clones continuam fazendo `fetch` pelas chaves de deploy.

---

### Task 10: fechamento

- [ ] **Step 1:** Atualizar `esper-brain/docs/migracao.md` com uma seção "Estado em 2026-11-18": o que roda onde (finance, brain-coletor, esper-brain), onde está cada segredo (sem valores), chaves de deploy e o que ficou para a etapa 4.
- [ ] **Step 2:** Commit e push no esper-brain.
- [ ] **Step 3:** Abrir o brainstorming da etapa 4 (GBrain + Honcho), com as 10 perguntas reais de aceite do spec.
