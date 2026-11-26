# Gabi mais simples Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Gabi lê um SOUL coerente (sem o que migrou), o Ricardo consegue ver o uso real das ferramentas e atualiza tudo com um comando.

**Architecture:** (1) gabi-brain: SOUL de origem enxuto e lista do Hermes sem as ferramentas migradas, sem apagar código. (2) gabi-brain: relatório somente leitura de `chamada_mcp`. (3) esper-brain: `deploy/gabi.sh` com `estado` e `atualizar`, compondo o SOUL na ordem certa.

**Tech Stack:** Python 3 (pytest), bash, git. Sem dependência nova.

**Spec:** `docs/superpowers/specs/2026-11-26-gabi-mais-simples-design.md`

## Global Constraints

- Nada é implantado na VPS; o Ricardo roda os comandos. Nenhum arquivo de dados do esper-brain (`entrada.md`, `hot.md`, `pendencias.md`, `projetos/`, `pessoal/`) é editado.
- O código das ferramentas migradas não é apagado; só saem do SOUL e da lista oficial do Hermes.
- Scripts não leem nem imprimem segredos.
- Commits terminam com `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>` e `Claude-Session: https://claude.ai/code/session_01UEbxiDj9R8NxPXQZDEY6gb`.
- Baseline: o teste `test_obter_token_teams::test_main_gravar_falhando_nao_mostra_o_token` do gabi-brain já falhava antes.

---

### Task 1: gabi-brain, lista do Hermes sem o que migrou

**Files:**
- Modify: `/home/claude/gabi-brain/gabi/mcp/servidor.py` (`ferramentas_do_hermes`)
- Modify: `/home/claude/gabi-brain/gabi/mcp/ferramentas_projetos.py:13` (`FORA_DO_HERMES`)
- Modify: `/home/claude/gabi-brain/gabi/mcp/ferramentas_familia.py` (nova constante `FORA_DO_HERMES`)
- Modify: `/home/claude/gabi-brain/tests/mcp/test_hermes.py`
- Regenerate: `/home/claude/gabi-brain/docs/fontes/hermes.md` (`python -m tools.gerar_hermes`)

**Interfaces:**
- Produces: `ferramentas_projetos.FORA_DO_HERMES` = todas as `NOMES` de projetos (incluindo `anexo_recentes`); `ferramentas_familia.FORA_DO_HERMES` = `familia_listar, familia_consultar, familia_atualizar_contato, familia_registrar_pessoa, familia_registrar_pet, familia_propor_documento` (não inclui `familia_vencimentos`). `ferramentas_do_hermes()` exclui os dois conjuntos.

- [ ] **Step 1: Teste que falha** em `tests/mcp/test_hermes.py`, trocando a linha que exige `projeto_ligar` e acrescentando:

```python
def test_hermes_nao_ve_o_que_migrou_para_o_esper_brain():
    nomes = set(ferramentas_do_hermes())
    migradas = {"projeto_criar", "projeto_ligar", "projeto_listar", "projeto_ver", "projeto_atualizar", "projeto_pessoa",
                "projeto_gasto", "projeto_fato", "projeto_fatos", "projeto_anexar", "anexo_recentes",
                "familia_listar", "familia_consultar", "familia_atualizar_contato", "familia_registrar_pessoa",
                "familia_registrar_pet", "familia_propor_documento"}
    assert not nomes & migradas
    assert "familia_vencimentos" in nomes  # fica no gabi_brain
```

e em `test_hermes_so_ve_as_ferramentas_da_lista` remover a asserção `"projeto_ligar" in ferramentas_do_hermes() and ...`, mantendo as duas primeiras.

- [ ] **Step 2: Rodar e ver falhar**: `cd /home/claude/gabi-brain && python -m pytest tests/mcp/test_hermes.py -q` → falha em `test_hermes_nao_ve_o_que_migrou_para_o_esper_brain`.

- [ ] **Step 3: Implementar.** Em `ferramentas_projetos.py`: `FORA_DO_HERMES = NOMES  # migrou para o esper-brain (temas); o código fica, o Hermes não enxerga`. Em `ferramentas_familia.py` acrescentar, perto dos `NOMES`: `FORA_DO_HERMES = ("familia_listar", "familia_consultar", "familia_atualizar_contato", "familia_registrar_pessoa", "familia_registrar_pet", "familia_propor_documento")  # migrou para o esper-brain`. Em `servidor.py`:

```python
def ferramentas_do_hermes() -> list[str]:
    """O `tools.include` do Hermes: as ferramentas dos escopos dele, menos as que migraram para o esper-brain (ADR-038 e etapa 3A)."""
    fora = set(ferramentas_projetos.FORA_DO_HERMES) | set(ferramentas_familia.FORA_DO_HERMES)
    return [n for n in ferramentas_do_token(ESCOPOS_HERMES) if n not in fora]
```

- [ ] **Step 4: Regerar a doc** `python -m tools.gerar_hermes`, depois rodar `python -m pytest tests/mcp -q` e corrigir só os testes que dependiam da lista antiga (não das ferramentas).

- [ ] **Step 5: Commit** (`git add` dos arquivos acima) com mensagem `hermes: lista oficial sem o que migrou para o esper-brain`.

### Task 2: gabi-brain, SOUL de origem enxuto

**Files:**
- Modify: `/home/claude/gabi-brain/deploy/hermes/SOUL.md`
- Modify: `/home/claude/gabi-brain/tests/mcp/test_hermes.py` (3 testes do SOUL), `/home/claude/gabi-brain/tests/mcp/test_confiabilidade.py` se citar o texto removido

**Interfaces:**
- Consumes: Task 1 (a lista já não tem as ferramentas).
- Produces: SOUL sem `projeto_*`, `anexo_recentes`, `familia_registrar_*`, `familia_atualizar_contato`, `familia_propor_documento`; com a linha-ponteiro "Família, temas e projetos da vida: esper-brain".

- [ ] **Step 1: Teste que falha** (substitui os 3 testes de SOUL de família/projeto em `test_hermes.py`):

```python
def _soul():
    return (Path(__file__).parent.parent.parent / "deploy" / "hermes" / "SOUL.md").read_text(encoding="utf-8")


def test_soul_nao_ensina_o_que_migrou_e_aponta_para_o_esper_brain():
    soul = _soul()
    for n in ("projeto_criar", "projeto_ligar", "projeto_listar", "projeto_ver", "projeto_atualizar", "projeto_pessoa", "projeto_gasto",
              "projeto_fato", "projeto_anexar", "anexo_recentes", "familia_registrar_pessoa", "familia_registrar_pet",
              "familia_atualizar_contato", "familia_propor_documento", "Linear (as ferramentas"):
        assert n not in soul, n
    assert "esper-brain" in soul and "família" in soul.lower()


def test_soul_continua_com_as_regras_de_gravar_de_verdade_e_despesas():
    soul = _soul()
    assert "Gravar de verdade" in soul and "Não tenho como gravar isso no brain; fica só nesta conversa." in soul
    gravar = soul.split("Gravar de verdade:")[1]
    assert "despesa_" in gravar and "atividade_" in gravar
    assert any(l.startswith("- Exceção (a pedido explícito") for l in soul.splitlines())
```

(os testes `test_soul_excecao_cobre_pessoa_pet_e_contato_sem_contradizer` e `test_soul_so_grava_fato_dito_e_nunca_cala` são removidos; `test_soul_ensina_as_despesas...` e `..._atividades...` ficam.)

- [ ] **Step 2: Rodar e ver falhar**: `python -m pytest tests/mcp/test_hermes.py -q`.

- [ ] **Step 3: Editar o SOUL com um script único** (`python - <<EOF`) que lê `deploy/hermes/SOUL.md`, aplica cada troca com `assert texto.count(velho) == 1` e grava:
  1. Remove a linha que começa com `- Exceção: pessoa, parentesco, apelido, nascimento, pet e contato da família`.
  2. Na linha `- Exceção (a pedido explícito`, remove o trecho que vai de `; "vou começar o projeto X" / "tenho um problema com X" vai para o Linear` até `` vai para `projeto_fato` `` (inclusive) e deixa `. Em todos, menos a lixeira...`.
  3. Remove as 5 linhas que começam com `- "vou começar o projeto X"`, `- "como está o projeto X?"`, `- "o mecânico disse`, `- "gastei R$ 300`, `- "conclui o projeto X"`.
  4. Na linha `- Valor a receber → `, remove de `; projeto → Linear (projeto e etapas)` até `(o fato, só do que ele afirmou ou confirmou)` mantendo `. Só por pedido do Ricardo nesta conversa.`.
  5. Remove as 4 linhas que começam com `- Pessoa, parentesco, apelido, nascimento → `, `- Grave só o que o Ricardo afirma como fato sobre uma pessoa ou um pet`, `- Na dúvida, pergunte "Quer que eu grave no brain: <fato>?"`, `- Nunca fique calado sobre um fato de pessoa ou pet`.
  6. Troca `(exceto atividades, lixeira de e-mail e família)` por `(exceto atividades e lixeira de e-mail)`; `• Família: "o Chafic é meu irmão" · contatos: "telefone do fulano?"` por `• Contatos: "telefone do fulano?"`; remove a linha `• Projeto: ...`.
  7. Troca `Os dados vêm do gabi.brain (ferramentas MCP).` por `Os dados vêm do gabi.brain, do `gabi_finance` e do `esper_brain` (ferramentas MCP).` e acrescenta, logo antes de `Onde achar:`, a linha: `- Família, pessoas, casa, ficha das empresas, temas e projetos da vida moram no esper-brain (seção "Segundo cérebro", no fim): use aquelas ferramentas, não procure cadastro de família aqui.`.

- [ ] **Step 4: Rodar** `python -m pytest tests/mcp -q` e acertar só o que citava o texto removido. Conferir que `grep -c "projeto_" deploy/hermes/SOUL.md` dá 0 e que a contagem de palavras caiu (`wc -w`).

- [ ] **Step 5: Commit**: `soul: gabi-brain sem o que migrou; aponta para o esper-brain`.

### Task 3: gabi-brain, relatório de uso das ferramentas

**Files:**
- Create: `/home/claude/gabi-brain/tools/uso_ferramentas.py`
- Create: `/home/claude/gabi-brain/tests/tools/test_uso_ferramentas.py`

**Interfaces:**
- Produces: `relatorio(con, desde_iso: str, oficiais: list[str]) -> dict` com chaves `usadas` (lista de `(ferramenta, n, erros, ultimo)` por n desc), `nunca` (oficiais sem chamada no período), `total`; `main(argv=None) -> int` com `--banco`, `--dias` (padrão 30).

- [ ] **Step 1: Teste que falha**:

```python
import sqlite3
from tools import uso_ferramentas as u


def _con():
    c = sqlite3.connect(":memory:")
    c.execute("create table chamada_mcp(id integer primary key, quando text, token_id int, ferramenta text, escopo text, status text, duracao_ms int)")
    return c


def test_relatorio_conta_por_ferramenta_e_lista_as_nunca_chamadas():
    c = _con()
    for q, f, s in [("2026-11-20T10:00:00+00:00", "atividade_criar", "ok"), ("2026-11-21T10:00:00+00:00", "atividade_criar", "erro"),
                    ("2026-11-22T10:00:00+00:00", "resumo_manha", "ok"), ("2026-09-01T10:00:00+00:00", "teams_pendentes", "ok")]:
        c.execute("insert into chamada_mcp(quando, ferramenta, escopo, status) values (?,?,?,?)", (q, f, "x", s))
    r = u.relatorio(c, "2026-11-01T00:00:00+00:00", ["atividade_criar", "resumo_manha", "teams_pendentes", "avisos_abertos"])
    assert r["usadas"][0][:3] == ("atividade_criar", 2, 1)
    assert r["nunca"] == ["avisos_abertos", "teams_pendentes"]  # teams_pendentes só tem chamada fora do período
    assert r["total"] == 3
```

- [ ] **Step 2: Rodar e ver falhar**: `python -m pytest tests/tools/test_uso_ferramentas.py -q` (ModuleNotFoundError).

- [ ] **Step 3: Implementar** `tools/uso_ferramentas.py`:

```python
"""Relatório de uso das ferramentas MCP (somente leitura): quantas vezes cada uma foi chamada e quais da lista oficial do Hermes
não foram chamadas no período. Uso: python -m tools.uso_ferramentas [--banco /var/lib/gabi/brain.db] [--dias 30]"""
import argparse
import datetime as dt
import os


def relatorio(con, desde_iso: str, oficiais: list[str]) -> dict:
    linhas = con.execute(
        "select ferramenta, count(*), sum(status != 'ok'), max(quando) from chamada_mcp where quando >= ? and ferramenta is not null "
        "group by ferramenta order by count(*) desc, ferramenta", (desde_iso,)).fetchall()
    usadas = [(f, n, int(e or 0), ultimo) for f, n, e, ultimo in linhas]
    vistas = {f for f, *_ in usadas}
    return {"usadas": usadas, "nunca": sorted(n for n in oficiais if n not in vistas), "total": sum(n for _, n, *_ in usadas)}


def main(argv=None) -> int:
    from gabi.db import conectar
    from gabi.mcp.servidor import ferramentas_do_hermes
    ap = argparse.ArgumentParser()
    ap.add_argument("--banco", default=os.environ.get("GABI_BANCO", "/var/lib/gabi/brain.db"))
    ap.add_argument("--dias", type=int, default=30)
    a = ap.parse_args(argv)
    desde = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=a.dias)).isoformat()
    con = conectar(a.banco)
    try:
        r = relatorio(con, desde, ferramentas_do_hermes())
    finally:
        con.close()
    print(f"Últimos {a.dias} dias: {r['total']} chamadas em {len(r['usadas'])} ferramentas")
    for f, n, e, ultimo in r["usadas"]:
        print(f"{n:5d}  {f}  (erros {e}, última {ultimo[:10]})")
    print(f"\nNa lista do Hermes e nunca chamadas ({len(r['nunca'])}):")
    for f in r["nunca"]:
        print("  " + f)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

Antes de gravar, conferir como o banco real é achado: `grep -rn "def conectar" gabi/db.py` e `grep -rn "GABI_BANCO\|brain.db" gabi/*.py deploy/*.service | head` e ajustar o padrão de `--banco` ao que existe.

- [ ] **Step 4: Rodar** o teste e ver passar; rodar `python -m tools.uso_ferramentas --help`.

- [ ] **Step 5: Commit**: `tools: relatório de uso das ferramentas MCP (somente leitura)`.

### Task 4: esper-brain, comando único `deploy/gabi.sh`

**Files:**
- Create: `/home/claude/esper-brain/deploy/gabi.sh`
- Create: `/home/claude/esper-brain/tests/test_gabi_sh.py`
- Create: `/home/claude/esper-brain/docs/operacao.md`

**Interfaces:**
- Produces: `gabi.sh estado` (somente leitura, sai com 0 se tudo certo e 3 se achou problema) e `gabi.sh atualizar [--sem-reiniciar]`. Variáveis: `GABI_HOME` (padrão `$HOME`), `GABI_SIMULAR=1` (só imprime o que faria). Repositórios em `$GABI_HOME/{esper-brain,gabi-brain,gabi-finance}`; ausente = aviso, não erro.

- [ ] **Step 1: Teste que falha** (`tests/test_gabi_sh.py`):

```python
import os, subprocess, pathlib

SH = pathlib.Path(__file__).resolve().parent.parent / "deploy" / "gabi.sh"


def _rodar(home, *args, **env):
    e = {**os.environ, "GABI_HOME": str(home), "HOME": str(home), **env}
    return subprocess.run(["bash", str(SH), *args], capture_output=True, text=True, env=e)


def _git(d, *a):
    subprocess.run(["git", "-C", str(d), "-c", "user.email=t@t", "-c", "user.name=t", *a], check=True, capture_output=True)


def _repo(home, nome):
    d = home / nome; d.mkdir(parents=True); _git(d, "init", "-q"); (d / "x").write_text("1"); _git(d, "add", "x"); _git(d, "commit", "-qm", "organizar 2026-11-26: 1 pedaços, t")
    return d


def test_estado_acusa_soul_com_texto_antigo(tmp_path):
    _repo(tmp_path, "esper-brain")
    (tmp_path / ".hermes").mkdir()
    (tmp_path / ".hermes" / "SOUL.md").write_text("use `familia_registrar_pessoa` e `projeto_ligar`")
    r = _rodar(tmp_path, "estado")
    assert r.returncode == 3 and "SOUL desatualizado" in r.stdout


def test_estado_ok_com_soul_limpo_e_organizar_recente(tmp_path):
    _repo(tmp_path, "esper-brain")
    (tmp_path / ".hermes").mkdir()
    (tmp_path / ".hermes" / "SOUL.md").write_text("<!-- esper-brain:inicio -->\nok\n<!-- esper-brain:fim -->\n")
    r = _rodar(tmp_path, "estado")
    assert r.returncode == 0, r.stdout + r.stderr


def test_atualizar_simulado_mostra_a_ordem_e_nao_executa(tmp_path):
    for n in ("esper-brain", "gabi-brain", "gabi-finance"):
        _repo(tmp_path, n)
    r = _rodar(tmp_path, "atualizar", GABI_SIMULAR="1")
    assert r.returncode == 0, r.stderr
    ordem = [l for l in r.stdout.splitlines() if l.startswith("[simulado]")]
    assert any("git -C" in l and "pull" in l for l in ordem)
    i_brain = next(i for i, l in enumerate(ordem) if "instalar-hermes-soul.sh" in l)
    i_fin = next(i for i, l in enumerate(ordem) if "editar_soul.py" in l)
    i_restart = next(i for i, l in enumerate(ordem) if "restart hermes-gateway" in l)
    assert i_brain < i_fin < i_restart
    assert not (tmp_path / ".hermes" / "SOUL.md").exists()


def test_atualizar_pula_repositorio_ausente_sem_erro(tmp_path):
    _repo(tmp_path, "esper-brain")
    r = _rodar(tmp_path, "atualizar", "--sem-reiniciar", GABI_SIMULAR="1")
    assert r.returncode == 0 and "gabi-brain: não encontrado" in r.stdout
```

- [ ] **Step 2: Rodar e ver falhar**: `cd /home/claude/esper-brain && python -m pytest tests/test_gabi_sh.py -q` (script não existe).

- [ ] **Step 3: Implementar `deploy/gabi.sh`** (bash, `set -uo pipefail`, executável) com:
  - funções `rodar()` (se `GABI_SIMULAR=1` imprime `[simulado] <comando>`, senão executa) e `repo()` (caminho ou aviso `<nome>: não encontrado`).
  - `estado`: para cada repositório presente imprime branch, HEAD curto, e `git fetch -q` seguido de quantos commits atrás do remoto (falha de rede = aviso, não erro); lê `$GABI_HOME/.hermes/SOUL.md`: se casar `projeto_(ligar|criar|listar|ver|atualizar|pessoa|gasto|fato|fatos|anexar)|anexo_recentes|familia_(listar|consultar|atualizar_contato|registrar_pessoa|registrar_pet|propor_documento)` imprime `SOUL desatualizado: ainda ensina ferramentas que migraram (rode: gabi.sh atualizar)` e marca problema; se faltar o marcador `<!-- esper-brain:inicio -->` imprime `SOUL sem a seção do esper-brain` e marca problema; no esper-brain, se o último commit cujo assunto começa com `organizar ` tem mais de 36 h (ou não existe) imprime `organizar sem gravar há mais de 36 h` e marca problema; se `hermes` existir, `hermes cron list` (tolerando falha). Sai com 3 se houve problema, 0 senão.
  - `atualizar`: (1) `git -C <repo> pull -q --ff-only` em cada repositório presente; (2) `bash <gabi-brain>/deploy/instalar-hermes-soul.sh` (base + seção esper-brain); (3) `python3 <gabi-finance>/deploy/hermes/editar_soul.py --data $(date +%Y-%m-%d-%H%M)`; (4) se `$HOME/.hermes/.env` contiver `NESS_KNOW_TOKEN=`, `python3 <esper-brain>/deploy/hermes/ligar_ness_know.py $HOME/.hermes/config.yaml --gravar`; (5) `python3 <esper-brain>/deploy/hermes/configurar_hermes.py` com `--python` lido do próprio config (comando de `mcp_servers.esper_brain`) e `--eb <esper-brain> --gravar`, só se esse bloco existir; (6) se não for `--sem-reiniciar`, `systemctl restart hermes-gateway` (com `sudo` se não for root); (7) roda `estado` e imprime `Falta: mande /new no Telegram`.
  - Qualquer passo que falha imprime `FALHOU: <passo>` e o script continua nos passos independentes, mas sai com 1 no fim.

- [ ] **Step 4: Rodar** `python -m pytest tests/test_gabi_sh.py -q` e depois a suíte inteira `python -m pytest -q tests` (esperado: tudo passando).

- [ ] **Step 5: `docs/operacao.md`** (curto): como rodar `gabi.sh estado` e `gabi.sh atualizar`, a ordem de composição do SOUL (base gabi-brain → editar_soul do gabi-finance → seção do esper-brain), que `/new` continua sendo do Ricardo, e o que o comando não faz (deploy do código do gabi-brain e do gabi-finance continua em `instalar-brain.sh` e equivalente).

- [ ] **Step 6: Commit**: `deploy: gabi.sh (estado e atualizar) compõe o SOUL na ordem certa`.

### Task 5: verificação e entrega

- [ ] **Step 1:** `cd /home/claude/gabi-brain && python -m pytest -q` (só o teste do baseline pode falhar), `cd /home/claude/esper-brain && python -m pytest -q tests`.
- [ ] **Step 2:** `git -C <repo> status --short` nos dois repositórios: só os arquivos do plano, nenhum arquivo de dados.
- [ ] **Step 3:** push dos dois repositórios e passo a passo da VPS para o Ricardo (um bloco, `umask 022`, `sudo -u ricardo -H bash -lc`).
