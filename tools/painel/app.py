"""Painel de temas: API Starlette sobre o esper_mcp (mesmas regras do chat), servida num socket Unix.

Servidor de um usuário e um processo: criar_app() aponta esper_mcp.RAIZ (global do módulo) para o cérebro.
Escritas passam por uma trava (uma por vez) e terminam em esper_mcp.gravar("painel: ...").

Uso: python3 tools/painel/app.py  (ou python3 -m tools.painel.app)
Ambiente: ESPER_BRAIN, ESPER_PAINEL_LOGINS, ESPER_PAINEL_ORIGENS, ESPER_PAINEL_SOCK (padrão /run/esper-painel/painel.sock).
"""
from __future__ import annotations

import datetime as dt
import json
import os
import re
import socket
import sys
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # tools/: import esper_mcp de qualquer jeito
import esper_mcp  # noqa: E402

from starlette.applications import Starlette  # noqa: E402
from starlette.concurrency import run_in_threadpool  # noqa: E402
from starlette.requests import Request  # noqa: E402
from starlette.responses import FileResponse, JSONResponse  # noqa: E402
from starlette.routing import Route  # noqa: E402

COLUNAS = (("familia", "Família"), ("casa", "Casa"), ("saude", "Saúde"), ("pessoal", "Pessoal"),
           ("patrimonio", "Patrimônio"), ("ness", "ness"), ("ionic", "IONIC"), ("bekaa", "Bekaa"),
           ("trabalho", "Trabalho (sem empresa)"))
ESTADOS = ("ativo", "parado", "concluído")
SECOES = ("Ideias soltas", "Fatos e decisões", "Perguntas em aberto", "Prazos")
MAX_TEXTO = 300
INDEX = Path(__file__).resolve().parent / "index.html"
_trava = threading.Lock()


class Erro(Exception):
    def __init__(self, msg: str, status: int = 400):
        super().__init__(msg)
        self.status = status


# ---------- regras (síncronas, rodam fora do laço) ----------

def _tema_rel(caminho) -> Path:
    """Só aceita o caminho exato de um arquivo de tema (lista do esper_mcp)."""
    c = str(caminho or "").strip()
    for f in esper_mcp._arquivos_de_tema():
        if f.relative_to(esper_mcp.RAIZ).as_posix() == c:
            return f
    raise Erro(f"não é um tema: {c!r}")


def _area_empresa(rel: str, fm: dict) -> tuple[str, str]:
    partes = rel.split("/")
    area = fm.get("area") or (partes[1] if len(partes) > 2 and partes[1] in esper_mcp.AREAS else "")
    return (area if area in esper_mcp.AREAS else "pessoal"), fm.get("empresa", "")


def _coluna(area: str, empresa: str) -> str:
    if area == "trabalho":
        return empresa if empresa in esper_mcp.EMPRESAS else "trabalho"
    return area


def _destino(coluna) -> tuple[str, str]:
    c = str(coluna or "").strip()
    if c in esper_mcp.EMPRESAS:
        return "trabalho", c
    if c in esper_mcp.AREAS:
        return c, ""
    raise Erro(f"coluna inválida: {c!r}")


def _titulo(f: Path, fm: dict) -> str:
    return fm.get("tema") or (f.parent.name if f.name == "README.md" else f.stem)


def _cartao_fm(f: Path, mud: dict, hoje: dt.date) -> tuple[dict, dict]:
    """Cartão e frontmatter, lendo o arquivo uma vez."""
    rel = f.relative_to(esper_mcp.RAIZ).as_posix()
    fm = esper_mcp._frontmatter(f.read_text(encoding="utf-8"))
    mudanca = mud.get(rel, "")
    try:
        parado = (hoje - dt.date.fromisoformat(mudanca)).days
    except ValueError:
        parado = 0
    return {"caminho": rel, "tema": _titulo(f, fm), "estado": fm.get("estado") or "ativo",
            "proximo_passo": fm.get("proximo_passo", ""), "prazo": fm.get("prazo", ""),
            "cliente": fm.get("cliente", ""), "marca": fm.get("marca", ""), "frente": fm.get("frente", ""),
            "holding": fm.get("holding", ""), "mudanca": mudanca, "parado_dias": parado}, fm


def _cartao(f: Path, mud: dict, hoje: dt.date) -> dict:
    return _cartao_fm(f, mud, hoje)[0]


def _cartao_de(rel: str) -> dict:
    return _cartao(esper_mcp.RAIZ / rel, esper_mcp._mudancas(), esper_mcp._agora().date())


def _gravar(msg: str) -> str:
    try:
        out = esper_mcp.gravar(msg)
    except esper_mcp.Recusa as e:
        raise Erro(str(e), 502)
    if not out.startswith("gravado:"):
        raise Erro(out, 502)
    return out


def _texto(v, nome: str, obrigatorio: bool = False) -> str:
    s = str(v if v is not None else "")
    if "\n" in s or "\r" in s:
        raise Erro(f"{nome}: sem quebra de linha")
    s = s.strip()
    if len(s) > MAX_TEXTO:
        raise Erro(f"{nome}: máximo {MAX_TEXTO} caracteres")
    if obrigatorio and not s:
        raise Erro(f"{nome}: vazio")
    return s


def _slug(tema: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", esper_mcp._sem_acento(tema)).strip("-")[:60].strip("-")
    if not s:
        raise Erro("tema sem letras nem números")
    usados = {f.stem if f.name != "README.md" else f.parent.name for f in esper_mcp._arquivos_de_tema()}
    if s not in usados:
        return s
    n = 2
    while True:
        suf = f"-{n}"
        cand = s[: 60 - len(suf)].rstrip("-") + suf
        if cand not in usados:
            return cand
        n += 1


def quadro() -> dict:
    hoje = esper_mcp._agora().date()
    mud = esper_mcp._mudancas()
    cols = {c: [] for c, _ in COLUNAS}
    for f in esper_mcp._arquivos_de_tema():
        card, fm = _cartao_fm(f, mud, hoje)
        cols[_coluna(*_area_empresa(card["caminho"], fm))].append(card)

    def ordem(c):
        try:
            return (0, dt.date.fromisoformat(c["prazo"]).toordinal())
        except ValueError:
            try:
                return (1, -dt.date.fromisoformat(c["mudanca"]).toordinal())
            except ValueError:
                return (2, 0)

    _, _, itens = esper_mcp._itens_entrada()
    return {"colunas": [{"id": c, "rotulo": r, "cartoes": sorted(cols[c], key=ordem)} for c, r in COLUNAS],
            "entrada": len(itens), "hoje": hoje.isoformat(), "frentes": list(esper_mcp.FRENTES_IONIC),
            "marcas": list(esper_mcp.MARCAS["ness"]), "holdings": list(esper_mcp.HOLDINGS)}


def tema(caminho) -> dict:
    f = _tema_rel(caminho)
    rel = f.relative_to(esper_mcp.RAIZ).as_posix()
    return {"caminho": rel, "texto": esper_mcp.ler(rel)}


def mover(d: dict) -> dict:
    f = _tema_rel(d.get("caminho"))
    rel = f.relative_to(esper_mcp.RAIZ).as_posix()
    fm = esper_mcp._frontmatter(f.read_text(encoding="utf-8"))
    area, empresa = _destino(d.get("coluna"))
    frente, holding = str(d.get("frente") or ""), str(d.get("holding") or "")
    marca = fm.get("marca", "") if empresa == "ness" else ""
    pasta = esper_mcp._pasta_do_tema(area, empresa, marca, frente, holding)
    if f.parent == esper_mcp.RAIZ / pasta:
        return {"ok": True, "mudou": False, "caminho": rel, "cartao": _cartao_de(rel)}
    esper_mcp.mover_tema(rel, area, empresa, marca, frente, holding)
    novo = f"{pasta}/{f.name}"
    return {"ok": True, "mudou": True, "caminho": novo, "gravado": _gravar(f"painel: move {_titulo(f, fm)}"),
            "cartao": _cartao_de(novo)}


def campos(d: dict) -> dict:
    f = _tema_rel(d.get("caminho"))
    rel = f.relative_to(esper_mcp.RAIZ).as_posix()
    esper_mcp._pode_escrever(rel)
    txt = f.read_text(encoding="utf-8")
    fm = esper_mcp._frontmatter(txt)
    area, empresa = _area_empresa(rel, fm)
    mudar = {}
    if "estado" in d:
        if d["estado"] not in ESTADOS:
            raise Erro(f"estado: use {', '.join(ESTADOS)}")
        mudar["estado"] = d["estado"]
    if "proximo_passo" in d:
        mudar["proximo_passo"] = _texto(d["proximo_passo"], "próximo passo")
    if "cliente" in d:
        mudar["cliente"] = _texto(d["cliente"], "cliente")
        if mudar["cliente"] and area != "trabalho":
            raise Erro("cliente só existe na área trabalho")
    if "marca" in d:
        mudar["marca"] = _texto(d["marca"], "marca").lower()
        if mudar["marca"] and (area != "trabalho" or empresa != "ness" or mudar["marca"] not in esper_mcp.MARCAS["ness"]):
            raise Erro(f"marca só na ness: {', '.join(esper_mcp.MARCAS['ness'])}")
    prazo = None
    if "prazo" in d:
        prazo = _texto(d["prazo"], "prazo")
        if prazo:
            try:
                if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", prazo):
                    raise ValueError
                dt.date.fromisoformat(prazo)
            except ValueError:
                raise Erro("prazo: use AAAA-MM-DD")
    if not mudar and prazo is None:
        raise Erro("nada para mudar")
    original = txt
    for k, v in mudar.items():
        if v != fm.get(k, ""):  # só a chave que mudou; cliente/marca vazios não entram onde não existem
            txt = esper_mcp._campo(txt, k, v)
    if prazo is not None and prazo != fm.get("prazo", ""):  # prazo sem aspas, como no modelo
        m_ = re.match(r"^---\n(.*?\n)---\n", txt, re.S)
        if not m_:
            raise Erro("arquivo sem frontmatter")
        linha = f"prazo: {prazo}" if prazo else "prazo:"
        cab, n = re.subn(r"^prazo:[^\n]*$", lambda _: linha, m_.group(1), count=1, flags=re.M)
        txt = "---\n" + (cab if n else cab + linha + "\n") + txt[m_.end(1):]
    if txt == original:
        return {"ok": True, "mudou": False, "cartao": _cartao_de(rel)}
    f.write_text(txt, encoding="utf-8")
    return {"ok": True, "mudou": True, "gravado": _gravar(f"painel: {_titulo(f, fm)}"), "cartao": _cartao_de(rel)}


def anotar(d: dict) -> dict:
    f = _tema_rel(d.get("caminho"))
    rel = f.relative_to(esper_mcp.RAIZ).as_posix()
    secao = d.get("secao")
    if secao not in SECOES:
        raise Erro(f"seção: use {', '.join(SECOES)}")
    texto = _texto(d.get("texto"), "texto", obrigatorio=True)
    antes = f.read_text(encoding="utf-8")
    esper_mcp.anotar(rel, secao, f"{esper_mcp._agora():%Y-%m-%d}: {texto}")
    depois = f.read_text(encoding="utf-8")
    if depois == antes:
        return {"ok": True, "mudou": False, "cartao": _cartao_de(rel)}
    titulo = _titulo(f, esper_mcp._frontmatter(depois))
    return {"ok": True, "mudou": True, "gravado": _gravar(f"painel: anota {titulo}"), "cartao": _cartao_de(rel)}


def criar(d: dict) -> dict:
    area, empresa = _destino(d.get("coluna"))
    titulo = _texto(d.get("tema"), "tema", obrigatorio=True)
    cliente = _texto(d.get("cliente"), "cliente")
    frente, holding = str(d.get("frente") or ""), str(d.get("holding") or "")
    pasta = esper_mcp._pasta_do_tema(area, empresa, "", frente, holding, cliente)
    slug = _slug(titulo)
    esper_mcp.criar_tema(slug, titulo, area=area, empresa=empresa, cliente=cliente, frente=frente, holding=holding)
    rel = f"{pasta}/{slug}.md"
    return {"ok": True, "mudou": True, "caminho": rel, "gravado": _gravar(f"painel: cria {titulo}"), "cartao": _cartao_de(rel)}


# ---------- HTTP ----------

def criar_app(raiz: Path, logins: set[str], origens: set[str]) -> Starlette:
    esper_mcp.RAIZ = Path(raiz).resolve()  # global do módulo: um usuário, um processo

    def proibido(req: Request):
        if req.headers.get("tailscale-user-login", "") not in logins:
            return JSONResponse({"erro": "proibido"}, status_code=403)
        return None

    async def executar(fn, *args, escrita=False):
        def rodar():
            if escrita:
                with _trava:
                    return fn(*args)
            return fn(*args)
        try:
            return JSONResponse(await run_in_threadpool(rodar))
        except Erro as e:
            return JSONResponse({"erro": str(e)}, status_code=e.status)
        except esper_mcp.Recusa as e:
            return JSONResponse({"erro": str(e)}, status_code=400)

    def get(fn):
        async def ep(req: Request):
            return proibido(req) or await fn(req)
        return ep

    def post(fn):
        async def ep(req: Request):
            if (r := proibido(req)):
                return r
            tipo = req.headers.get("content-type", "").split(";")[0].strip().lower()
            if tipo != "application/json" or req.headers.get("origin", "") not in origens:
                return JSONResponse({"erro": "origem"}, status_code=403)
            try:
                d = json.loads(await req.body())
            except (ValueError, UnicodeDecodeError):
                d = None
            if not isinstance(d, dict):
                return JSONResponse({"erro": "corpo JSON inválido"}, status_code=400)
            return await executar(fn, d, escrita=True)
        return ep

    async def index(req: Request):
        if not INDEX.exists():
            return JSONResponse({"erro": "página ausente"}, status_code=404, headers={"Cache-Control": "no-store"})
        return FileResponse(INDEX, media_type="text/html; charset=utf-8", headers={"Cache-Control": "no-store"})

    async def api_quadro(req: Request):
        return await executar(quadro)

    async def api_tema(req: Request):
        return await executar(tema, req.query_params.get("caminho", ""))

    return Starlette(routes=[
        Route("/", get(index), methods=["GET"]),
        Route("/api/quadro", get(api_quadro), methods=["GET"]),
        Route("/api/tema", get(api_tema), methods=["GET"]),
        Route("/api/mover", post(mover), methods=["POST"]),
        Route("/api/campos", post(campos), methods=["POST"]),
        Route("/api/anotar", post(anotar), methods=["POST"]),
        Route("/api/criar", post(criar), methods=["POST"]),
    ])


def _lista(nome: str) -> set[str]:
    return {x.strip() for x in os.environ.get(nome, "").split(",") if x.strip()}


def _abrir_socket(caminho: str) -> socket.socket:
    """Socket Unix só do dono (0600): o cabeçalho de login só vale se o único outro par é o tailscaled (root).
    (uvicorn.run(uds=...) deixaria 0666.)"""
    if os.path.lexists(caminho):
        os.unlink(caminho)  # sobra de execução anterior
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    velho = os.umask(0o177)
    try:
        s.bind(caminho)
    finally:
        os.umask(velho)
    os.chmod(caminho, 0o600)
    s.listen(128)
    return s


def main() -> None:
    import uvicorn

    raiz = Path(os.path.expanduser(os.environ.get("ESPER_BRAIN", "~/esper-brain"))).resolve()
    sock = os.environ.get("ESPER_PAINEL_SOCK", "/run/esper-painel/painel.sock")
    app = criar_app(raiz, _lista("ESPER_PAINEL_LOGINS"), _lista("ESPER_PAINEL_ORIGENS"))
    uvicorn.Server(uvicorn.Config(app, proxy_headers=False)).run(sockets=[_abrir_socket(sock)])


if __name__ == "__main__":
    main()
