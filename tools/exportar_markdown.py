"""Exporta o contexto do gabi-brain para markdown (etapa 1 do desenho esper-brain).
Uso: python3 -m tools.exportar_markdown DESTINO [--banco /var/lib/gabi-brain/gabi.db]
Só leitura (?mode=ro), só biblioteca padrão. Número de documento e CNPJ só vão para pessoal/cofre/ (cifrado com git-crypt no
esper-brain); texto livre sai inteiro e as linhas suspeitas são listadas (caminho:linha) para conferência.
Monta tudo em memória e só escreve se nada falhar; DESTINO precisa estar vazio ou não existir."""
import argparse
import json
import re
import sqlite3
import sys
import unicodedata
from collections import Counter
from pathlib import Path

PADRAO_BANCO = Path("/var/lib/gabi-brain/gabi.db")
ESQUEMA = {
    "pessoa": {"id", "nome", "papel", "dados", "excluido_em"},
    "pet": {"id", "nome", "especie", "dados"},
    "bem": {"id", "tipo", "nome", "excluido_em"},
    "documento": {"id", "titular_tipo", "titular_id", "tipo", "pais", "emissor", "paperless_id", "excluido_em"},
    "documento_data": {"documento_id", "tipo", "data"},
    "projeto": {"id", "nome", "objetivo", "status", "prazo", "orcamento_centavos", "criado_em", "encerrado_em"},
    "projeto_fato": {"projeto_id", "texto", "data_fato", "pessoa_nome", "registrado_em"},
    "projeto_pessoa": {"projeto_id", "nome", "papel"},
    "projeto_gasto": {"projeto_id"},
    "atividade": {"id", "texto", "vence_em", "status", "projeto_id", "criada_em", "concluida_em", "marco"},
    "anexo": {"tipo", "paperless_id", "recebido_em", "projeto_id"},
    "allowlist_vip": {"chave", "pessoa", "rotulo"},
    "escuta_remetente": {"numero", "nome", "estado"},
    "documento_numero": {"documento_id", "nome", "valor"},
    "empresa": {"id", "nome", "cnpj", "dados", "excluido_em"},
}
DATAS_DOC = ("emissao", "validade", "vigencia_inicio", "vigencia_fim", "vencimento", "renovacao")
ESTADO_PROJETO = {"ativo": "ativo", "pausado": "parado", "concluido": "concluído", "cancelado": "concluído"}
GRUPO_ESCUTA = {"aprovado": "Escuta", "ignorado": "Ignora", "bloqueado": "Ignora", "pendente": "Aguardando decisão"}
DINHEIRO = r"(?:\s?(?:mil|milh[ãaõo](?:o|es)?|bilh[ãaõo](?:o|es)?))?"
MASCARAS = (
    re.compile(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b"),
    re.compile(r"\b\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}\b"),
    re.compile(r"\b(?:CPF|CNPJ|RG|CNH|RENAVAM|passaporte)\b[\s:nº°#.]*[A-Z]{0,2}\d[\d.\-/]{4,}", re.I),
    re.compile(r"(?:R|US)\$\s?\d[\d.,]*" + DINHEIRO, re.I),
    re.compile(r"\b\d[\d.,]*" + DINHEIRO + r"\s?reais\b", re.I),
)
SUSPEITAS = MASCARAS + (
    re.compile(r"\b[A-Z]{0,2}\d{7,}\b"),                 # passaporte, CPF/RENAVAM sem pontuação (telefones também: ok para conferência)
    re.compile(r"\b\d{1,2}\.\d{3}\.\d{3}-[\dxX]\b"),         # RG
)
PAPEIS_FAMILIA = ("titular", "familia", "esposa", "ex-esposa", "filha", "filho")
COFRE = "pessoal/cofre/"
SEM_CONFERIR = {"people/_aprovados.md"}  # telefones são o dado


class ErroExportacao(Exception):
    pass


def abrir(caminho: Path) -> sqlite3.Connection:
    if not Path(caminho).is_file():
        raise ErroExportacao(f"banco não encontrado: {caminho}")
    con = sqlite3.connect(f"file:{caminho}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    return con


def conferir_esquema(con: sqlite3.Connection) -> None:
    faltam = []
    for tabela, colunas in ESQUEMA.items():
        tem = {r["name"] for r in con.execute(f"pragma table_info({tabela})")}
        if not tem:
            faltam.append(tabela)
            continue
        faltam += [f"{tabela}.{c}" for c in sorted(colunas - tem)]
    if faltam:
        raise ErroExportacao("esquema inesperado, falta: " + ", ".join(faltam))


def slug(texto: str) -> str:
    s = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    if not s:
        raise ErroExportacao(f"nome sem slug: {texto!r}")
    return s


def _dados(texto) -> dict:
    try:
        d = json.loads(texto or "{}")
    except ValueError:
        return {}
    return d if isinstance(d, dict) else {}


def _texto(linhas: list[str]) -> str:
    return "\n".join(linhas).rstrip() + "\n"


def _juntar(destino: dict, parte: dict) -> None:
    for caminho, texto in parte.items():
        if caminho in destino:
            raise ErroExportacao(f"dois itens geram o mesmo arquivo: {caminho}")
        destino[caminho] = texto


def _caminho_livre(arquivos: dict, pasta: str, nome: str, ident) -> str:
    base = slug(mascarar(nome)[0])
    caminho = f"{pasta}/{base}.md"
    return caminho if caminho not in arquivos else f"{pasta}/{base}-{slug(str(ident))}.md"


def mascarar(texto: str) -> tuple[str, int]:
    total = 0
    for padrao in MASCARAS:
        texto, n = padrao.subn("[removido]", texto)
        total += n
    return texto, total


def suspeitas(arquivos: dict[str, str]) -> list[str]:
    """Linhas fora do cofre que parecem ter número de documento ou dinheiro: "caminho:linha", sem o conteúdo."""
    achadas = []
    for caminho, texto in sorted(arquivos.items()):
        if caminho in SEM_CONFERIR or caminho.startswith(COFRE):
            continue
        achadas += [f"{caminho}:{n}" for n, linha in enumerate(texto.splitlines(), 1) if any(r.search(linha) for r in SUSPEITAS)]
    return achadas


def _documentos(con, titular_tipo: str, titular_id: str) -> list[str]:
    linhas = []
    for d in con.execute("select id, tipo, pais, emissor, paperless_id from documento"
                         " where titular_tipo=? and titular_id=? and excluido_em is null order by tipo, id",
                         (titular_tipo, str(titular_id))):
        datas = {r["tipo"]: r["data"] for r in con.execute("select tipo, data from documento_data where documento_id=?", (d["id"],))}
        partes = [d["tipo"].upper() + (f" ({d['pais']})" if d["pais"] and d["pais"] != "BR" else "")]
        if d["emissor"]:
            partes.append(f"emissor {d['emissor']}")
        partes += [f"{t.replace('_', ' ')} {datas[t]}" for t in DATAS_DOC if t in datas]
        if d["paperless_id"]:
            partes.append(f"paperless:{d['paperless_id']}")
        if con.execute("select 1 from documento_numero where documento_id=? limit 1", (d["id"],)).fetchone():
            partes.append("número no cofre")
        linhas.append("- " + " · ".join(partes))
    return linhas


def familia(con) -> dict[str, str]:
    arquivos: dict[str, str] = {}
    for p in con.execute("select id, nome, papel, dados from pessoa"
                         " where excluido_em is null and papel in (" + ", ".join("?" * len(PAPEIS_FAMILIA)) + ")"
                         " order by nome collate nocase, id", PAPEIS_FAMILIA):
        d = _dados(p["dados"])
        parentesco = d.get("parentesco") or (p["papel"] if p["papel"] not in ("familia", "titular") else None)
        campos = [("nome completo", d.get("nome_completo")), ("apelido", d.get("apelido")), ("parentesco", parentesco),
                  ("nascimento", d.get("nascimento")), ("observação", d.get("observacao"))]
        linhas = ["---", f"origem: gabi-brain pessoa:{p['id']}", "---", f"# {p['nome']}", ""]
        linhas += [f"- {rotulo}: {valor}" for rotulo, valor in campos if valor]
        if d.get("falecido") is True:
            linhas.append("- falecido")
        linhas += ["", "## Documentos", *(_documentos(con, "pessoa", p["id"]) or ["- nenhum registrado"])]
        _juntar(arquivos, {_caminho_livre(arquivos, "pessoal/familia", p["nome"], p["id"]): _texto(linhas)})
    return arquivos


def casa(con) -> dict[str, str]:
    pets = ["# Pets", ""]
    for r in con.execute("select nome, especie, dados from pet order by nome collate nocase"):
        d = _dados(r["dados"])
        nascimento = d.get("nascimento") or d.get("aniversario")
        dono = d.get("dono") or d.get("tutor")
        extra = [x for x in (r["especie"], d.get("raca"), nascimento and f"nascimento {nascimento}", dono and f"dono {dono}") if x]
        pets.append(f"- **{r['nome']}**" + (" · " + " · ".join(extra) if extra else ""))
    bens = ["# Bens", ""]
    for b in con.execute("select id, tipo, nome from bem where excluido_em is null order by tipo, nome collate nocase"):
        bens += [f"## {b['nome']} ({b['tipo']})", *(_documentos(con, "bem", b["id"]) or ["- nenhum documento registrado"]), ""]
    return {"pessoal/casa/pets.md": _texto(pets), "pessoal/casa/bens.md": _texto(bens)}


def _yaml(texto) -> str:
    return json.dumps(texto or "", ensure_ascii=False)


def projetos(con) -> dict[str, str]:
    arquivos: dict[str, str] = {}
    for p in con.execute("select * from projeto order by id"):
        pid = p["id"]
        pessoas = list(con.execute("select nome, papel from projeto_pessoa where projeto_id=? order by id", (pid,)))
        abertas = list(con.execute("select texto, vence_em, marco from atividade where projeto_id=? and status='aberta'"
                                   " order by coalesce(vence_em, '9999'), id", (pid,)))
        tem_dinheiro = p["orcamento_centavos"] is not None or \
            con.execute("select 1 from projeto_gasto where projeto_id=? limit 1", (pid,)).fetchone() is not None
        ligacoes = [f"gabi-brain projeto:{pid}"] + ([f"gabi-finance projeto:{pid}"] if tem_dinheiro else [])
        linhas = ["---", f"tema: {_yaml(p['nome'])}", f"estado: {ESTADO_PROJETO[p['status']]}",
                  f"proximo_passo: {_yaml(abertas[0]['texto'] if abertas else '')}", f"prazo: {p['prazo'] or ''}",
                  f"pessoas: [{', '.join(slug(r['nome']) for r in pessoas)}]", f"ligacoes: [{', '.join(ligacoes)}]", "---",
                  f"# {p['nome']}", "", "## Onde estou", f"- {p['objetivo'] or 'objetivo não registrado no gabi-brain'}"]
        linhas += [f"- pessoa: {r['nome']}" + (f" ({r['papel']})" if r["papel"] else "") for r in pessoas]
        linhas += ["", "## Ideias soltas", "", "## Fatos e decisões"]
        for f in con.execute("select texto, data_fato, pessoa_nome, registrado_em from projeto_fato where projeto_id=?"
                             " order by coalesce(data_fato, registrado_em), id", (pid,)):
            linhas.append(f"- {(f['data_fato'] or f['registrado_em'])[:10]} — {f['texto']}" + (f" ({f['pessoa_nome']})" if f["pessoa_nome"] else ""))
        linhas += ["", "## Perguntas em aberto", "", "## Prazos"]
        if p["prazo"]:
            linhas.append(f"- [ ] prazo do projeto — {p['prazo']}")
        linhas += [f"- [ ] {a['texto']}" + (f" — vence {a['vence_em']}" if a["vence_em"] else "") + (" · marco" if a["marco"] else "")
                   for a in abertas]
        historico = [(p["criado_em"][:10], "projeto criado")]
        historico += [(a["concluida_em"][:10], f"{'feito' if a['status'] == 'feita' else 'cancelado'}: {a['texto']}")
                      for a in con.execute("select texto, status, concluida_em from atividade"
                                           " where projeto_id=? and status<>'aberta' and concluida_em is not null", (pid,))]
        historico += [(x["recebido_em"][:10], f"anexo {x['tipo']}" + (f" · paperless:{x['paperless_id']}" if x["paperless_id"] else ""))
                      for x in con.execute("select tipo, paperless_id, recebido_em from anexo where projeto_id=?", (pid,))]
        if p["encerrado_em"]:
            historico.append((p["encerrado_em"][:10], f"projeto {p['status']}"))
        linhas += ["", "## Histórico", *[f"- {data} — {texto}" for data, texto in sorted(historico, reverse=True)]]
        _juntar(arquivos, {_caminho_livre(arquivos, "projetos", p["nome"], pid): _texto(linhas)})
    return arquivos


def pendencias(con) -> dict[str, str]:
    linhas = ["# Pendências", ""]
    linhas += [f"- [ ] {a['texto']}" + (f" — vence {a['vence_em']}" if a["vence_em"] else "") + " · origem gabi-brain"
               for a in con.execute("select texto, vence_em from atividade where status='aberta' and projeto_id is null"
                                    " order by coalesce(vence_em, '9999'), id")]
    return {"pendencias.md": _texto(linhas)}


def aprovados(con) -> dict[str, str]:
    grupos: dict[str, list[str]] = {"VIP": [], "Escuta": [], "Ignora": [], "Aguardando decisão": []}
    for r in con.execute("select chave, pessoa, rotulo from allowlist_vip order by chave"):
        grupos["VIP"].append(f"- {r['rotulo'] or r['pessoa'] or r['chave']} · {r['chave']}")
    for r in con.execute("select numero, nome, estado from escuta_remetente order by nome collate nocase, numero"):
        grupos[GRUPO_ESCUTA[r["estado"]]].append(f"- {r['nome'] or 'sem nome'} · {r['numero']}")
    linhas = ["# Quem a Gabi escuta", ""]
    for titulo, itens in grupos.items():
        linhas += [f"## {titulo}", *(itens or ["- ninguém"]), ""]
    return {"people/_aprovados.md": _texto(linhas)}


def _titular(con, titular_tipo: str, titular_id: str) -> str:
    tabela = "pessoa" if titular_tipo == "pessoa" else "bem"
    r = con.execute(f"select nome from {tabela} where id=?", (titular_id,)).fetchone()
    return r["nome"] if r else f"{titular_tipo} {titular_id}"


def cofre(con) -> dict[str, str]:
    docs = ["# Cofre — documentos", "", "Cifrado no GitHub (git-crypt). Não copie para fora do cofre.", ""]
    for d in con.execute("select d.id, d.titular_tipo, d.titular_id, d.tipo, d.pais, d.paperless_id from documento d"
                         " where d.excluido_em is null and exists (select 1 from documento_numero n where n.documento_id=d.id)"
                         " order by d.titular_tipo, d.titular_id, d.tipo, d.id"):
        titulo = f"## {_titular(con, d['titular_tipo'], d['titular_id'])} — {d['tipo'].upper()}"
        titulo += f" ({d['pais']})" if d["pais"] and d["pais"] != "BR" else ""
        titulo += f" · paperless:{d['paperless_id']}" if d["paperless_id"] else ""
        docs += [titulo, *[f"- {n['nome']}: {n['valor']}" for n in
                           con.execute("select nome, valor from documento_numero where documento_id=? order by id", (d["id"],))], ""]
    emp = ["# Cofre — empresas", "", "Cifrado no GitHub (git-crypt).", ""]
    for e in con.execute("select nome, cnpj from empresa where excluido_em is null order by nome collate nocase, id"):
        emp.append(f"- **{e['nome']}** · CNPJ {e['cnpj'] or 'não registrado'}")
    return {f"{COFRE}documentos.md": _texto(docs), f"{COFRE}empresas.md": _texto(emp)}


def empresas(con) -> dict[str, str]:
    linhas = ["# Empresas importadas do gabi-brain", "", "Cada uma vira a ficha cadastral empresas/<nome>.md (modelo em empresas/_modelo.md).",
              "CNPJ em pessoal/cofre/empresas.md.", ""]
    for e in con.execute("select id, nome, dados from empresa where excluido_em is null order by nome collate nocase, id"):
        relacao = _dados(e["dados"]).get("relacao")
        linhas.append(f"- {e['nome']}" + (f" · relação: {relacao}" if relacao else "") + f" · gabi-brain empresa:{e['id']}")
    return {"empresas/_importadas.md": _texto(linhas)}


def montar(con) -> dict[str, str]:
    conferir_esquema(con)
    arquivos: dict[str, str] = {}
    for parte in (familia(con), casa(con), projetos(con), pendencias(con), aprovados(con), cofre(con), empresas(con)):
        _juntar(arquivos, parte)
    return arquivos


def escrever(arquivos: dict[str, str], destino: Path) -> None:
    if destino.exists() and any(destino.iterdir()):
        raise ErroExportacao(f"destino não está vazio: {destino}")
    for relativo, texto in arquivos.items():
        alvo = destino / relativo
        alvo.parent.mkdir(parents=True, exist_ok=True)
        alvo.write_text(texto, encoding="utf-8")


def contar(arquivos: dict[str, str]) -> dict[str, int]:
    return dict(sorted(Counter(str(Path(k).parent) for k in arquivos).items()))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python3 -m tools.exportar_markdown", description=__doc__.splitlines()[0])
    ap.add_argument("destino", type=Path)
    ap.add_argument("--banco", type=Path, default=PADRAO_BANCO)
    a = ap.parse_args(argv)
    try:
        con = abrir(a.banco)
        con.execute("begin")
        arquivos = montar(con)
        escrever(arquivos, a.destino)
    except (ErroExportacao, sqlite3.Error, OSError) as e:
        print(f"erro: {e}", file=sys.stderr)
        return 1
    for pasta, n in contar(arquivos).items():
        print(f"{pasta}: {n} arquivo(s)")
    conferir = suspeitas(arquivos)
    print(f"linhas para conferir (número ou dinheiro fora do cofre): {len(conferir)}")
    for item in conferir:
        print(f"  {item}")
    print(f"total: {len(arquivos)} arquivo(s) em {a.destino}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
