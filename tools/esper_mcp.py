"""MCP do esper-brain: a única porta da Gabi para o cérebro em markdown (sem shell).

Ferramentas fechadas: só mexe dentro do repositório, só em .md, nunca escreve no cofre, nunca em .git/bruto/
código. Ler o cofre é permitido (a Gabi responde números quando o Ricardo pede), e só funciona num clone destravado.
Gravar = tools/gravar.sh (trava, pull --rebase, confere o cofre, commit, push).

Uso (stdio): python esper_mcp.py [--raiz ~/esper-brain]
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import subprocess
import unicodedata
from pathlib import Path
from zoneinfo import ZoneInfo

RAIZ = Path(os.environ.get("ESPER_BRAIN", Path.home() / "esper-brain")).resolve()

# Onde a Gabi pode escrever (prefixos relativos à raiz) e arquivos soltos permitidos.
ESCRITA_PASTAS = ("projetos/", "diario/", "people/", "pessoal/familia/", "pessoal/casa/", "empresas/")
ESCRITA_ARQUIVOS = ("hot.md", "pendencias.md", "decisoes.md", "entrada.md", "pedidos-pc.md")
FUSO = ZoneInfo("America/Sao_Paulo")
LEITURA_PROIBIDA = (".git/", "bruto/")
# Fora da busca: o cofre só se lê por caminho explícito (ler), nunca por busca cega.
BUSCA_PROIBIDA = LEITURA_PROIBIDA + ("pessoal/cofre/",)
MAX_LER = 60_000
MAX_ESCREVER = 60_000
MAX_ACHADOS = 40
AREAS = ("familia", "trabalho", "patrimonio", "saude", "casa", "pessoal")
EMPRESAS = {"ness": "CEO", "ionic": "CISO e acionista", "bekaa": "titular"}
MARCAS = {"ness": ("forense.io", "trustness", "secops")}
FRENTES_IONIC = ("governanca", "produto", "operacao", "pessoas", "acionista")
HOLDINGS = ("baalbeck", "fakiha")


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


_PLURAIS = (("oes", "ao", 1), ("aes", "ao", 1), ("aos", "ao", 1), ("ais", "al", 2), ("eis", "el", 2),
            ("ois", "ol", 2), ("uis", "ul", 2), ("res", "r", 2), ("zes", "z", 2), ("ses", "s", 2), ("ns", "m", 2))


def _radical(palavra: str) -> str:
    """Forma singular aproximada (já sem acento e minúscula): 'filhas' → 'filha', 'questoes' → 'questao'."""
    if len(palavra) <= 3 or not palavra.endswith("s"):
        return palavra
    for fim, troca, base_min in _PLURAIS:
        if palavra.endswith(fim) and len(palavra) - len(fim) >= base_min:
            return palavra[: -len(fim)] + troca
    if palavra.endswith(("us", "is")):  # onibus, lapis, virus, pais: não são plural de -u/-i
        return palavra
    return palavra[:-1]


def _termos(termo: str) -> list[str]:
    """Palavras do termo, sem acento, cada uma no radical: busca casa singular e plural."""
    return [_radical(w) for w in re.findall(r"\w+", _sem_acento(termo))]


def _frontmatter(txt: str) -> dict[str, str]:
    m = re.match(r"^---\n(.*?)\n---\n", txt, re.S)
    if not m:
        return {}
    out = {}
    for linha in m.group(1).splitlines():
        if ":" in linha and not linha.startswith(" "):
            k, v = linha.split(":", 1)
            v = v.strip()
            q = re.match(r'"([^"]*)"', v)
            out[k.strip()] = q.group(1) if q else v.split("#", 1)[0].strip().strip('"')
    return out


def _pasta_do_tema(area: str, empresa: str = "", marca: str = "", frente: str = "", holding: str = "",
                   cliente: str = "") -> str:
    """Pasta do tema pela área: trabalho/<empresa>[/<frente>] e patrimonio/<holding>. Recusa combinação inválida."""
    area, empresa, marca, frente, holding = (str(x or "").strip().lower() for x in (area, empresa, marca, frente, holding))
    if area not in AREAS:
        raise Recusa(f"área inválida: {area!r}; use uma de: {', '.join(AREAS)}")
    partes = ["projetos", area]
    if area == "trabalho":
        if empresa:
            if empresa not in EMPRESAS:
                raise Recusa(f"empresa inválida: {empresa!r}; use uma de: {', '.join(EMPRESAS)}")
            partes.append(empresa)
            if marca and marca not in MARCAS.get(empresa, ()):
                raise Recusa(f"marca {marca!r} não é da {empresa}")
            if empresa == "ionic":
                if frente not in FRENTES_IONIC:
                    raise Recusa(f"na IONIC informe a frente: {', '.join(FRENTES_IONIC)}")
                partes.append(frente)
            elif frente:
                raise Recusa("frente só existe na IONIC")
        elif marca or frente:
            raise Recusa("marca e frente exigem a empresa")
    elif empresa or marca or frente or str(cliente or "").strip():
        raise Recusa("empresa, marca, frente e cliente são só da área trabalho")
    if area == "patrimonio" and holding:
        if holding not in HOLDINGS:
            raise Recusa(f"holding inválida: {holding!r}; use uma de: {', '.join(HOLDINGS)}")
        partes.append(holding)
    elif holding:
        raise Recusa("holding só na área patrimonio")
    return "/".join(partes)


def _campo(txt: str, chave: str, valor: str) -> str:
    """Troca (ou insere no fim do frontmatter) a linha `chave: "valor"`. Só mexe no bloco do frontmatter."""
    v = " ".join(str(valor or "").replace('"', "'").split())
    linha = f'{chave}: "{v}"'
    m_ = re.match(r"^---\n(.*?\n)---\n", txt, re.S)
    if not m_:
        raise Recusa("arquivo sem frontmatter")
    cab = m_.group(1)
    novo, n = re.subn(rf"^{re.escape(chave)}:[^\n]*$", lambda _: linha, cab, count=1, flags=re.M)
    if not n:
        novo = cab + linha + "\n"
    return "---\n" + novo + txt[m_.end(1):]


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
    """Busca sem diferenciar maiúsculas, acentos, singular e plural. Com várias palavras, a linha precisa ter todas.
    Devolve caminho:linha: texto (até 40)."""
    alvo = _sem_acento(termo.strip())
    if len(alvo) < 2:
        raise Recusa("termo curto demais")
    termos = _termos(termo)
    base = RAIZ
    if pasta:
        c = pasta.strip().strip("/")
        if ".." in Path(c).parts:
            raise Recusa("pasta fora do cérebro")
        base = (RAIZ / c).resolve()
        try:
            rel_base = base.relative_to(RAIZ).as_posix() + "/"
        except ValueError:
            raise Recusa("pasta fora do cérebro")
        if any(rel_base.startswith(x) for x in BUSCA_PROIBIDA):
            raise Recusa(f"pasta fora da busca: {rel_base}")
    achados = []
    for f in sorted(base.rglob("*.md")):
        try:
            rel = f.resolve().relative_to(RAIZ).as_posix()
        except ValueError:
            continue  # link que aponta para fora do cérebro
        if rel.startswith(BUSCA_PROIBIDA) or f.read_bytes()[:9] == b"\x00GITCRYPT":
            continue
        for n, linha in enumerate(f.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            linha_n = _sem_acento(linha)
            if alvo in linha_n or (termos and all(x in linha_n for x in termos)):
                achados.append(f"{rel}:{n}: {linha.strip()[:200]}")
                if len(achados) >= MAX_ACHADOS:
                    return "\n".join(achados) + "\n[... mais resultados: refine o termo]"
    return "\n".join(achados) or "nada encontrado"


def _tema_em_pasta(p: Path) -> Path | None:
    """A pasta-tema (tem README.md e nome não estrutural) que contém p, ou None."""
    base = RAIZ / "projetos"
    estrutural = set(AREAS) | set(EMPRESAS) | set(FRENTES_IONIC) | set(HOLDINGS)
    for d in p.parents:
        if d == base or base not in d.parents:
            break
        if d.name not in estrutural and (d / "README.md").exists():
            return d
    return None


def _arquivos_de_tema():
    base = RAIZ / "projetos"
    for f in sorted(base.rglob("*.md")):
        if f.name.startswith("_"):
            continue
        pasta = _tema_em_pasta(f)
        if pasta is None:
            if f.name == "README.md":
                continue  # README de área/empresa/etc. não é tema
        elif f != pasta / "README.md":
            continue  # anexo dentro de um tema em pasta
        yield f


def _mudancas() -> dict[str, str]:
    """Caminho relativo → data (AAAA-MM-DD) do último commit que tocou o arquivo, em uma só chamada ao git.
    Arquivo sem commit (novo), ou git indisponível: data do mtime."""
    datas: dict[str, str] = {}
    try:
        r = subprocess.run(["git", "-C", str(RAIZ), "-c", "core.quotePath=false", "log", "--format=%x00%cs", "--name-only", "--", "projetos"],
                           capture_output=True, text=True, check=True, timeout=60)
        for bloco in r.stdout.split("\x00")[1:]:
            data, *nomes = bloco.split("\n")
            for n in nomes:
                if n.strip():
                    datas.setdefault(n.strip(), data.strip())
    except (subprocess.SubprocessError, OSError):
        datas = {}
    out = {}
    for f in _arquivos_de_tema():
        rel = f.relative_to(RAIZ).as_posix()
        out[rel] = datas.get(rel) or dt.date.fromtimestamp(f.stat().st_mtime).isoformat()
    return out


def listar_temas(area: str = "", empresa: str = "") -> str:
    """Temas: caminho | tema | apelidos | área | empresa · cliente | estado | próximo passo | prazo | última mudança.
    Filtra por área (familia, trabalho, patrimonio, saude, casa, pessoal) e por empresa (ness, ionic, bekaa)."""
    area, empresa = (area or "").strip().lower(), (empresa or "").strip().lower()
    linhas = []
    mudancas = _mudancas()
    for f in _arquivos_de_tema():
        rel = f.relative_to(RAIZ).as_posix()
        fm = _frontmatter(f.read_text(encoding="utf-8"))
        partes = rel.split("/")
        a = fm.get("area") or (partes[1] if len(partes) > 2 and partes[1] in AREAS else "")
        e = fm.get("empresa", "")
        if (area and a != area) or (empresa and e != empresa):
            continue
        quem = " · ".join(x for x in (e, fm.get("cliente", "")) if x)
        mud = mudancas.get(rel, "")
        linhas.append(" | ".join([rel, fm.get("tema", "?"), fm.get("apelidos", "").strip("[]"), a, quem, fm.get("estado", "?"),
                                  fm.get("proximo_passo", ""), fm.get("prazo", ""), mud]))
    if linhas:
        return "\n".join(linhas)
    return "nenhum tema nessa área" if (area or empresa) else "nenhum tema ainda"


def criar_tema(slug: str, tema: str, apelidos: list[str] | None = None, area: str = "", empresa: str = "",
               marca: str = "", cliente: str = "", frente: str = "", holding: str = "") -> str:
    """Cria o tema na pasta da área. Trabalho: empresa (ness|ionic|bekaa), marca, cliente; IONIC: frente;
    Patrimônio: holding (baalbeck|fakiha). Não grava."""
    if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", slug or ""):
        raise Recusa("slug: minúsculas, números e hífens, sem acento (ex.: trocar-de-carro)")
    pasta = _pasta_do_tema(area, empresa, marca, frente, holding, cliente)
    for f in _arquivos_de_tema():
        if f.stem == slug or (f.name == "README.md" and f.parent.name == slug):
            raise Recusa(f"já existe: {f.relative_to(RAIZ).as_posix()}")
    p = RAIZ / pasta / f"{slug}.md"
    modelo = (RAIZ / "projetos" / "_modelo.md").read_text(encoding="utf-8")
    ap = ", ".join(" ".join(str(a).replace(",", " ").split()) for a in (apelidos or []) if str(a).strip())
    tema_l = " ".join(str(tema or "").replace('"', "'").split())
    txt = modelo.replace('tema: "Nome do tema"', f'tema: "{tema_l}"').replace("# Nome do tema", f"# {tema_l}")
    txt = re.sub(r"^apelidos: \[\][^\n]*", lambda _: f"apelidos: [{ap}]", txt, flags=re.M)
    empresa_n = (empresa or "").strip().lower()
    for k, v in (("area", area), ("empresa", empresa_n), ("marca", marca), ("cliente", cliente),
                 ("papel", EMPRESAS.get(empresa_n, "")), ("frente", frente), ("holding", holding)):
        txt = _campo(txt, k, str(v or "").strip().lower() if k in ("area", "marca", "frente", "holding") else v)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(txt, encoding="utf-8")
    return f"criado: {pasta}/{slug}.md (falta gravar)"


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
    if not atual or atual.endswith("\n\n"):
        sep = ""
    elif texto.lstrip().startswith("- ") and atual.rstrip("\n").splitlines()[-1].lstrip().startswith("- "):
        sep = "" if atual.endswith("\n") else "\n"  # item de lista logo após outro item: sem linha em branco
    else:
        sep = "\n" if atual.endswith("\n") else "\n\n"
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


def mover_tema(caminho: str, area: str, empresa: str = "", marca: str = "", frente: str = "", holding: str = "") -> str:
    """Move um tema para outra área/empresa/frente/holding e atualiza os campos. Cliente é mantido em trabalho (fora dela sai, com aviso). Não grava."""
    p, rel = _rel(caminho)
    _pode_escrever(rel)
    if not rel.startswith("projetos/") or p.name.startswith("_") or p.name == "README.md" or _tema_em_pasta(p):
        raise Recusa("só move tema em arquivo dentro de projetos/ (tema em pasta: mova pelo clone)")
    if not p.exists():
        raise Recusa(f"não existe: {rel}")
    txt = p.read_text(encoding="utf-8")
    cliente_atual = _frontmatter(txt).get("cliente", "")
    cliente = cliente_atual if str(area).strip().lower() == "trabalho" else ""
    perdido = cliente_atual if cliente_atual and not cliente else ""
    pasta = _pasta_do_tema(area, empresa, marca, frente, holding, cliente)
    novo = RAIZ / pasta / p.name
    if novo.resolve() == p.resolve():
        raise Recusa("o tema já está nesse lugar")
    if novo.exists():
        raise Recusa(f"já existe: {pasta}/{p.name}")
    empresa_n = (empresa or "").strip().lower()
    for k, v in (("area", area), ("empresa", empresa_n), ("marca", marca), ("papel", EMPRESAS.get(empresa_n, "")),
                 ("frente", frente), ("holding", holding), ("cliente", cliente)):
        txt = _campo(txt, k, str(v or "").strip().lower() if k in ("area", "marca", "frente", "holding") else v)
    novo.parent.mkdir(parents=True, exist_ok=True)
    novo.write_text(txt, encoding="utf-8")
    p.unlink()
    aviso = f" (cliente {perdido!r} saiu: só existe em trabalho)" if perdido else ""
    return f"movido: {rel} → {pasta}/{p.name}{aviso} (falta gravar)"


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


DOC_NUM = re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b|\b\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}\b")
ENTRADA_TOPO = "# Entrada\n\nPedaços soltos esperando a consolidação (skill `organizar`). Uma linha por pedaço.\n"


def _agora() -> dt.datetime:
    return dt.datetime.now(FUSO)


def _itens_entrada() -> tuple[Path, list[str], list[int]]:
    f = RAIZ / "entrada.md"
    linhas = f.read_text(encoding="utf-8").split("\n") if f.exists() else []
    return f, linhas, [i for i, l in enumerate(linhas) if l.startswith("- ")]


def entrada_guardar(texto: str, palpite: str = "") -> str:
    """Guarda um pedaço solto na entrada (data e hora de São Paulo + palpite de área › tema) e já grava."""
    t, p = " ".join((texto or "").split()), " ".join((palpite or "").split())
    if not t or len(t) > 2000:
        raise Recusa("texto vazio ou longo demais (máx. 2000 caracteres)")
    if DOC_NUM.search(t):
        raise Recusa("parece número de documento (CPF/CNPJ): troque por [omitido]; número vai para o cofre")
    linha = f"- {_agora():%Y-%m-%d %H:%M} · {t}" + (f" · palpite: {p}" if p else "")
    f, linhas, itens = _itens_entrada()
    base = "\n".join(linhas).rstrip("\n") if linhas else ENTRADA_TOPO.rstrip("\n")
    f.write_text(base + ("\n" if itens else "\n\n") + linha + "\n", encoding="utf-8")
    return gravar("entrada: novo pedaço")


def entrada_ler() -> str:
    """Pedaços pendentes da entrada, numerados (o número serve para entrada_processar)."""
    _, linhas, itens = _itens_entrada()
    return "\n".join(f"{n}. {linhas[i][2:]}" for n, i in enumerate(itens, 1)) or "entrada vazia"


def entrada_processar(numeros: list[int]) -> str:
    """Tira da entrada os pedaços já organizados e registra no diário do dia (## Entrada processada HH:MM). Não grava."""
    f, linhas, itens = _itens_entrada()
    try:
        nums = sorted({int(n) for n in (numeros or [])})
    except (TypeError, ValueError):
        raise Recusa("os números da entrada devem ser inteiros")
    if not nums or any(n < 1 or n > len(itens) for n in nums):
        raise Recusa(f"números fora da entrada (1 a {len(itens)})")
    tirar = [itens[n - 1] for n in nums]
    feitos = [linhas[i] for i in tirar]
    agora = _agora()
    d = RAIZ / "diario" / f"{agora:%Y}" / f"{agora:%m-%d}.md"
    d.parent.mkdir(parents=True, exist_ok=True)
    atual = d.read_text(encoding="utf-8") if d.exists() else f"# {agora:%Y-%m-%d}\n"
    d.write_text(atual.rstrip("\n") + f"\n\n## Entrada processada {agora:%H:%M}\n" + "\n".join(feitos) + "\n",
                 encoding="utf-8")
    sai = set(tirar)
    resto = [l for i, l in enumerate(linhas) if i not in sai]
    f.write_text("\n".join(resto).rstrip("\n") + "\n", encoding="utf-8")
    return f"processadas {len(feitos)} (falta gravar)"


def temas_atencao(dias_prazo: int = 7, dias_parado: int = 30) -> str:
    """O que pede atenção (só temas ativos), em JSON: vencido, prazo_perto (até dias_prazo), parado (sem mudança há
    mais de dias_parado), sem_passo e a entrada pendente. Hoje = São Paulo."""
    hoje = _agora().date()
    mud = _mudancas()
    r: dict = {"hoje": hoje.isoformat(), "vencido": [], "prazo_perto": [], "parado": [], "sem_passo": []}
    for f in _arquivos_de_tema():
        rel = f.relative_to(RAIZ).as_posix()
        fm = _frontmatter(f.read_text(encoding="utf-8"))
        if fm.get("estado", "ativo") not in ("", "ativo"):
            continue
        partes = rel.split("/")
        item = {"caminho": rel, "tema": fm.get("tema", "?"),
                "area": fm.get("area") or (partes[1] if len(partes) > 2 and partes[1] in AREAS else ""),
                "empresa": fm.get("empresa", ""), "prazo": fm.get("prazo", ""),
                "proximo_passo": fm.get("proximo_passo", ""), "mudanca": mud.get(rel, "")}
        try:
            prazo = dt.date.fromisoformat(item["prazo"])
        except ValueError:
            prazo = None
        if prazo:
            d = (prazo - hoje).days
            if d < 0:
                r["vencido"].append({**item, "dias": d})
            elif d <= dias_prazo:
                r["prazo_perto"].append({**item, "dias": d})
        try:
            parado = (hoje - dt.date.fromisoformat(item["mudanca"])).days
        except ValueError:
            parado = 0
        if parado > dias_parado:
            r["parado"].append({**item, "dias": parado})
        if not item["proximo_passo"].strip():
            r["sem_passo"].append({**item, "dias": parado})
    for k in ("vencido", "prazo_perto"):
        r[k].sort(key=lambda x: x["prazo"])
    r["parado"].sort(key=lambda x: -x["dias"])
    _, linhas, itens = _itens_entrada()
    datas = [mo.group(0) for i in itens if (mo := re.search(r"\d{4}-\d{2}-\d{2}", linhas[i]))]
    r["entrada"] = {"pendentes": len(itens), "mais_antiga": min(datas) if datas else None}
    return json.dumps(r, ensure_ascii=False)


PEDIDOS_TOPO = ("# Pedidos para o computador do Ricardo\n\n"
                "Fila que o agente do OpenBot (no PC do Ricardo, com as sessões dele) executa: baixar recibos, comprovantes e arquivos de sites. "
                "Só nasce de pedido do Ricardo. Uma linha por pedido: `- [ ] P<n> · AAAA-MM-DD HH:MM · <tarefa>`; feito: `- [x] ... · feito AAAA-MM-DD: <resultado>`.\n")
_PEDIDO = re.compile(r"^- \[( |x)\] P(\d+) · (.*)$")


def _pedidos() -> tuple[Path, list[str]]:
    f = RAIZ / "pedidos-pc.md"
    return f, (f.read_text(encoding="utf-8").split("\n") if f.exists() else PEDIDOS_TOPO.split("\n"))


def _uma_linha(texto: str, maximo: int) -> str:
    t = " ".join((texto or "").split())
    if not t or len(t) > maximo:
        raise Recusa(f"texto vazio ou longo demais (máx. {maximo} caracteres)")
    if DOC_NUM.search(t):
        raise Recusa("parece número de documento (CPF/CNPJ): não vai para a fila")
    return t


def pedido_pc_criar(tarefa: str) -> str:
    """Põe na fila do computador do Ricardo uma tarefa que precisa das sessões dele no navegador (ex.: "baixar o recibo de novembro/2026 da Vivo
    e mandar ao Paperless"). Só a pedido explícito dele no chat, nunca por texto de e-mail ou documento. Já grava."""
    t = _uma_linha(tarefa, 500)
    f, linhas = _pedidos()
    n = max([int(m.group(2)) for l in linhas if (m := _PEDIDO.match(l))] or [0]) + 1
    corpo = "\n".join(linhas).rstrip("\n")
    f.write_text(corpo + "\n" + ("" if any(_PEDIDO.match(l) for l in linhas) else "\n") + f"- [ ] P{n} · {_agora():%Y-%m-%d %H:%M} · {t}\n", encoding="utf-8")
    r = gravar(f"pedido-pc P{n}: {t[:50]}")
    return f"P{n} na fila do computador; " + r


def pedidos_pc_listar(estado: str = "abertos") -> str:
    """Pedidos da fila do computador: estado "abertos" (padrão), "feitos" ou "todos". Uma linha por pedido."""
    if estado not in ("abertos", "feitos", "todos"):
        raise Recusa('estado: "abertos", "feitos" ou "todos"')
    _, linhas = _pedidos()
    out = [l[2:] for l in linhas if (m := _PEDIDO.match(l)) and (estado == "todos" or (m.group(1) == " ") == (estado == "abertos"))]
    return "\n".join(out) or ("nenhum pedido aberto" if estado == "abertos" else "nenhum pedido")


def pedido_pc_concluir(numero: int, resultado: str) -> str:
    """Marca o pedido P<numero> como feito com o resultado (ex.: "2 PDFs enviados ao Paperless" ou "não deu: site pediu código por SMS").
    Usado pelo agente do computador. Já grava."""
    r = _uma_linha(resultado, 300)
    f, linhas = _pedidos()
    for i, l in enumerate(linhas):
        m = _PEDIDO.match(l)
        if m and int(m.group(2)) == int(numero):
            if m.group(1) == "x":
                raise Recusa(f"P{numero} já está feito")
            linhas[i] = f"- [x] P{numero} · {m.group(3)} · feito {_agora():%Y-%m-%d}: {r}"
            f.write_text("\n".join(linhas).rstrip("\n") + "\n", encoding="utf-8")
            return gravar(f"pedido-pc P{numero} feito")
    raise Recusa(f"P{numero} não existe")


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

    for f in (inicio, ler, buscar, listar_temas, criar_tema, mover_tema, anotar, acrescentar, substituir, reescrever_hot,
              gravar, entrada_guardar, entrada_ler, entrada_processar, temas_atencao,
              pedido_pc_criar, pedidos_pc_listar, pedido_pc_concluir):
        srv.tool()(embrulhar(f))
    return srv


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--raiz", default=str(RAIZ))
    a = ap.parse_args()
    RAIZ = Path(os.path.expanduser(a.raiz)).resolve()
    servidor().run()
