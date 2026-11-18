"""MCP do esper-brain: a única porta da Gabi para o cérebro em markdown (sem shell).

Ferramentas fechadas: só mexe dentro do repositório, só em .md, nunca escreve no cofre, nunca em .git/bruto/
código. Ler o cofre é permitido (a Gabi responde números quando o Ricardo pede), e só funciona num clone destravado.
Gravar = tools/gravar.sh (trava, pull --rebase, confere o cofre, commit, push).

Uso (stdio): python esper_mcp.py [--raiz ~/esper-brain]
"""
from __future__ import annotations

import argparse
import datetime as dt
import os
import re
import subprocess
import unicodedata
from pathlib import Path

RAIZ = Path(os.environ.get("ESPER_BRAIN", Path.home() / "esper-brain")).resolve()

# Onde a Gabi pode escrever (prefixos relativos à raiz) e arquivos soltos permitidos.
ESCRITA_PASTAS = ("projetos/", "diario/", "people/", "pessoal/familia/", "pessoal/casa/", "empresas/")
ESCRITA_ARQUIVOS = ("hot.md", "pendencias.md", "decisoes.md")
LEITURA_PROIBIDA = (".git/", "bruto/")
MAX_LER = 60_000
MAX_ESCREVER = 60_000
MAX_ACHADOS = 40


class Recusa(Exception):
    pass


def _rel(caminho: str) -> tuple[Path, str]:
    """Resolve um caminho relativo dentro da raiz; recusa absoluto, '..', links que saem e o que não é .md."""
    c = (caminho or "").strip()
    while c.startswith("./"):
        c = c[2:]
    if not c or c.startswith("/") or ".." in Path(c).parts:
        raise Recusa(f"caminho recusado: {caminho!r} (use um caminho relativo ao cérebro, ex.: projetos/carro.md)")
    p = (RAIZ / c).resolve()
    try:
        rel = p.relative_to(RAIZ).as_posix()
    except ValueError:
        raise Recusa(f"caminho fora do cérebro: {caminho!r}")
    if any(rel == x.rstrip("/") or rel.startswith(x) for x in LEITURA_PROIBIDA):
        raise Recusa(f"caminho recusado: {rel}")
    if p.suffix != ".md":
        raise Recusa(f"só arquivos .md: {rel}")
    return p, rel


def _pode_escrever(rel: str) -> None:
    if rel.startswith("pessoal/cofre/"):
        raise Recusa("o cofre não é escrito por aqui: o Ricardo edita o cofre no clone dele")
    if rel in ESCRITA_ARQUIVOS or rel.startswith(ESCRITA_PASTAS):
        if Path(rel).name.startswith("_modelo"):
            raise Recusa("o modelo não é editado por aqui")
        return
    raise Recusa(f"sem permissão de escrita em {rel} (permitido: {', '.join(ESCRITA_ARQUIVOS + ESCRITA_PASTAS)})")


def _sem_acento(s: str) -> str:
    return "".join(ch for ch in unicodedata.normalize("NFD", s.lower()) if unicodedata.category(ch) != "Mn")


def _frontmatter(txt: str) -> dict[str, str]:
    m = re.match(r"^---\n(.*?)\n---\n", txt, re.S)
    if not m:
        return {}
    out = {}
    for linha in m.group(1).splitlines():
        if ":" in linha and not linha.startswith(" "):
            k, v = linha.split(":", 1)
            out[k.strip()] = v.split("#", 1)[0].strip().strip('"')
    return out


# ---------- ferramentas (funções puras, testáveis sem MCP) ----------

def inicio() -> str:
    """Leitura de começo de conversa: AGENTS.md, mapa.md, hot.md e pendencias.md."""
    partes = []
    for nome in ("AGENTS.md", "mapa.md", "hot.md", "pendencias.md"):
        f = RAIZ / nome
        if f.exists():
            partes.append(f"===== {nome} =====\n{f.read_text(encoding='utf-8')}")
    return "\n\n".join(partes)


def ler(caminho: str) -> str:
    p, rel = _rel(caminho)
    if not p.exists():
        raise Recusa(f"não existe: {rel}")
    b = p.read_bytes()
    if b[:9] == b"\x00GITCRYPT":
        raise Recusa(f"{rel} está cifrado: o clone da VPS não foi destravado (git-crypt unlock)")
    t = b.decode("utf-8", errors="replace")
    return t if len(t) <= MAX_LER else t[:MAX_LER] + f"\n[... cortado em {MAX_LER} caracteres]"


def buscar(termo: str, pasta: str = "") -> str:
    """Busca sem diferenciar maiúsculas nem acentos. Devolve caminho:linha: texto (até 40)."""
    alvo = _sem_acento(termo.strip())
    if len(alvo) < 2:
        raise Recusa("termo curto demais")
    base = RAIZ
    if pasta:
        base = (RAIZ / pasta.strip("/")).resolve()
        if not str(base).startswith(str(RAIZ)):
            raise Recusa("pasta fora do cérebro")
    achados = []
    for f in sorted(base.rglob("*.md")):
        rel = f.relative_to(RAIZ).as_posix()
        if rel.startswith(LEITURA_PROIBIDA) or f.read_bytes()[:9] == b"\x00GITCRYPT":
            continue
        for n, linha in enumerate(f.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            if alvo in _sem_acento(linha):
                achados.append(f"{rel}:{n}: {linha.strip()[:200]}")
                if len(achados) >= MAX_ACHADOS:
                    return "\n".join(achados) + "\n[... mais resultados: refine o termo]"
    return "\n".join(achados) or "nada encontrado"


def listar_temas() -> str:
    """Temas/projetos: caminho | tema | apelidos | estado | próximo passo | prazo | última mudança no arquivo."""
    linhas = []
    for f in sorted(list((RAIZ / "projetos").glob("*.md")) + list((RAIZ / "projetos").glob("*/README.md"))):
        if f.name.startswith("_"):
            continue
        fm = _frontmatter(f.read_text(encoding="utf-8"))
        mud = dt.date.fromtimestamp(f.stat().st_mtime).isoformat()
        linhas.append(" | ".join([f.relative_to(RAIZ).as_posix(), fm.get("tema", "?"), fm.get("apelidos", "[]"),
                                  fm.get("estado", "?"), fm.get("proximo_passo", ""), fm.get("prazo", ""), mud]))
    return "\n".join(linhas) or "nenhum tema ainda"


def criar_tema(slug: str, tema: str, apelidos: list[str] | None = None) -> str:
    if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", slug or ""):
        raise Recusa("slug: minúsculas, números e hífens, sem acento (ex.: trocar-de-carro)")
    p = RAIZ / "projetos" / f"{slug}.md"
    if p.exists() or (RAIZ / "projetos" / slug).exists():
        raise Recusa(f"já existe: projetos/{slug}")
    modelo = (RAIZ / "projetos" / "_modelo.md").read_text(encoding="utf-8")
    ap = ", ".join(a.strip() for a in (apelidos or []) if a.strip())
    txt = modelo.replace('tema: "Nome do tema"', f'tema: "{tema}"').replace("# Nome do tema", f"# {tema}")
    txt = re.sub(r"^apelidos: \[\][^\n]*", f"apelidos: [{ap}]", txt, flags=re.M)
    p.write_text(txt, encoding="utf-8")
    return f"criado: projetos/{slug}.md (falta gravar)"


def anotar(caminho: str, secao: str, texto: str) -> str:
    """Põe uma linha '- texto' logo abaixo do título '## secao' (mais nova em cima). Não grava."""
    p, rel = _rel(caminho)
    _pode_escrever(rel)
    if not p.exists():
        raise Recusa(f"não existe: {rel}")
    texto = " ".join(texto.split())
    if not texto or len(texto) > 2000:
        raise Recusa("texto vazio ou longo demais (máx. 2000 caracteres)")
    linhas = p.read_text(encoding="utf-8").split("\n")
    alvo = _sem_acento(secao.strip().lstrip("#").strip())
    for i, l in enumerate(linhas):
        if l.startswith("## ") and _sem_acento(l[3:].strip()) == alvo:
            linhas.insert(i + 1, f"- {texto}")
            p.write_text("\n".join(linhas), encoding="utf-8")
            return f"anotado em {rel} › {l[3:].strip()} (falta gravar)"
    secoes = [l[3:].strip() for l in linhas if l.startswith("## ")]
    raise Recusa(f"seção {secao!r} não existe em {rel}; seções: {', '.join(secoes)}")


def acrescentar(caminho: str, texto: str) -> str:
    """Acrescenta texto ao fim do arquivo (cria o arquivo, e a pasta, se não existir). Para diário e notas."""
    p, rel = _rel(caminho)
    _pode_escrever(rel)
    if len(texto) > MAX_ESCREVER:
        raise Recusa("texto longo demais")
    p.parent.mkdir(parents=True, exist_ok=True)
    atual = p.read_text(encoding="utf-8") if p.exists() else ""
    sep = "" if not atual or atual.endswith("\n\n") else ("\n" if atual.endswith("\n") else "\n\n")
    p.write_text(atual + sep + texto.rstrip("\n") + "\n", encoding="utf-8")
    return f"acrescentado em {rel} (falta gravar)"


def substituir(caminho: str, trecho_antigo: str, trecho_novo: str) -> str:
    """Troca um trecho exato (que aparece uma vez só) por outro. Para 'Onde estou', próximo passo, estado."""
    p, rel = _rel(caminho)
    _pode_escrever(rel)
    if not p.exists():
        raise Recusa(f"não existe: {rel}")
    t = p.read_text(encoding="utf-8")
    n = t.count(trecho_antigo)
    if n != 1:
        raise Recusa(f"o trecho antigo aparece {n} vezes em {rel}; precisa aparecer exatamente 1")
    p.write_text(t.replace(trecho_antigo, trecho_novo, 1), encoding="utf-8")
    return f"alterado {rel} (falta gravar)"


def reescrever_hot(texto: str) -> str:
    """Substitui o hot.md inteiro (só ele). Usado pela digestão diária. Não grava."""
    t = (texto or "").strip()
    if not t.startswith("# "):
        raise Recusa("o hot.md começa com um título '# ...'")
    if len(t) > 8000:
        raise Recusa("hot.md longo demais (máx. 8000 caracteres): resuma")
    (RAIZ / "hot.md").write_text(t + "\n", encoding="utf-8")
    return "hot.md reescrito (falta gravar)"


def gravar(mensagem: str) -> str:
    """Commit + push do que mudou nas áreas permitidas. Só depois de 'gravado:' diga 'anotado'."""
    msg = " ".join((mensagem or "").split())[:200]
    if not msg:
        raise Recusa("mensagem de commit vazia")
    st = subprocess.run(["git", "-C", str(RAIZ), "status", "--porcelain", "-uall"],
                        capture_output=True, text=True, check=True).stdout
    caminhos = []
    for l in st.splitlines():
        rel = l[3:].split(" -> ")[-1].strip('"')
        try:
            _pode_escrever(rel)
        except Recusa:
            continue
        if rel.endswith(".md"):
            caminhos.append(rel)
    if not caminhos:
        return "nada a gravar"
    r = subprocess.run([str(RAIZ / "tools" / "gravar.sh"), msg, *caminhos], capture_output=True, text=True, timeout=180)
    saida = (r.stdout + r.stderr).strip()
    if r.returncode != 0:
        raise Recusa(f"NÃO gravado: {saida}")
    return saida


# ---------- servidor MCP ----------

def servidor():
    from mcp.server.fastmcp import FastMCP

    srv = FastMCP("esper_brain")

    def embrulhar(f):
        def w(*a, **k):
            try:
                return f(*a, **k)
            except Recusa as e:
                return f"recusado: {e}"
        w.__name__, w.__doc__ = f.__name__, f.__doc__
        w.__signature__ = __import__("inspect").signature(f)
        w.__annotations__ = f.__annotations__
        return w

    for f in (inicio, ler, buscar, listar_temas, criar_tema, anotar, acrescentar, substituir, reescrever_hot, gravar):
        srv.tool()(embrulhar(f))
    return srv


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--raiz", default=str(RAIZ))
    a = ap.parse_args()
    RAIZ = Path(os.path.expanduser(a.raiz)).resolve()
    servidor().run()
