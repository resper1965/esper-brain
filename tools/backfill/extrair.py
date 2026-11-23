"""Fase 1 do backfill: candidatos a fichas, sem IA. Lê o banco do gabi-brain só para leitura e títulos do Paperless."""
import argparse
import json
import os
import re
import sys
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tools.backfill import fontes, paperless  # noqa: E402

AUTOMATICO = re.compile(r"(^|[._-])(no-?reply|do-?not-?reply|notifica\w*|notifications?|news(letter)?|marketing|mailer-daemon|"
                        r"postmaster|bounces?|alertas?|alerts?|info|suporte|support|billing|cobranca|faturas?)([._-]|@)"
                        r"|@(\w+\.)*(linkedin\.com|facebookmail\.com|google\.com|github\.com|microsoft\.com|calendly\.com)$")
LIVRES = {"gmail.com", "hotmail.com", "outlook.com", "live.com", "yahoo.com", "yahoo.com.br", "icloud.com", "me.com",
          "uol.com.br", "bol.com.br", "terra.com.br", "msn.com", "proton.me", "protonmail.com"}
PREFIXO = re.compile(r"^\s*((re|res|fw|fwd|enc|tr|aw)\s*:\s*)+", re.I)


def e_automatico(endereco: str) -> bool:
    return bool(AUTOMATICO.search(endereco.lower()))


def normalizar_assunto(s: str) -> str:
    return re.sub(r"\s+", " ", PREFIXO.sub("", s or "")).strip().lower()


def _acumulador() -> dict:
    return {"datas": [], "contas": set(), "assuntos": defaultdict(int)}


def pessoas(emails, respondidos: set[str], contatos, proprios, minimo=3) -> list[dict]:
    acc = defaultdict(_acumulador)
    for e in emails:
        end = e["remetente"]
        if not end or end in proprios or e["lista"] or e["classe"] == "lixo" or e_automatico(end):
            continue
        a = acc[end]
        a["datas"].append(e["recebida_em"][:10])
        a["contas"].add(e["conta"])
        a["assuntos"][normalizar_assunto(e["assunto"])] += 1
    saida = []
    for end, a in acc.items():
        respondido = end in respondidos          # só sinal: email_respondido não tem data de resposta confiável
        conhecido = respondido or bool(contatos.get(end))
        if not conhecido:                        # robô ou newsletter: nunca escrito pelo Ricardo nem nos contatos
            continue
        if len(a["datas"]) < minimo and not (respondido and a["datas"]):
            continue
        datas = sorted(a["datas"])
        top = sorted(a["assuntos"].items(), key=lambda kv: -kv[1])[:5]
        saida.append({"endereco": end, "nome": contatos.get(end, ""), "interacoes": len(a["datas"]),
                      "primeira": datas[0], "ultima": datas[-1], "contas": sorted(a["contas"]),
                      "assuntos": [k for k, _ in top if k], "respondido": respondido})
    return sorted(saida, key=lambda p: (-p["interacoes"], p["endereco"]))


def pessoas_agenda(agenda, minimo=2) -> list[dict]:
    acc = defaultdict(list)
    for ev in agenda:
        if ev["organizador"] and "@" not in ev["organizador"]:
            acc[ev["organizador"]].append(ev)
    saida = [{"nome": n, "reunioes": len(evs), "titulos": sorted({e["titulo"] for e in evs if e["titulo"]})[:5],
              "primeira": min(e["dia"] for e in evs), "ultima": max(e["dia"] for e in evs)}
             for n, evs in acc.items() if len(evs) >= minimo]
    return sorted(saida, key=lambda p: (-p["reunioes"], p["nome"]))


def empresas(pessoas_, slugs: set[str]) -> list[dict]:
    acc = defaultdict(lambda: {"pessoas": [], "interacoes": 0})
    for p in pessoas_:
        dom = p["endereco"].split("@")[-1]
        if dom in LIVRES:
            continue
        acc[dom]["pessoas"].append(p["endereco"])
        acc[dom]["interacoes"] += p["interacoes"]
    saida = []
    for dom, a in acc.items():
        raiz = dom.split(".")[0]
        ficha = next((s for s in sorted(slugs) if s == raiz or s.replace("-", "") == raiz or s.startswith(raiz + "-")), None)
        saida.append({"dominio": dom, "ficha": ficha, "pessoas": a["pessoas"], "interacoes": a["interacoes"]})
    return sorted(saida, key=lambda e: (-e["interacoes"], e["dominio"]))


def temas(emails, projetos, slugs_temas: set[str], proprios, minimo_dias=3, remetentes: set[str] | None = None) -> list[dict]:
    """`remetentes`: se dado, só e-mails dessas pessoas (ou das contas do Ricardo) viram tema."""
    acc = defaultdict(lambda: {"dias": set(), "pessoas": set()})
    for e in emails:
        end = e["remetente"]
        if e["lista"] or e["classe"] == "lixo" or e_automatico(end):
            continue
        if remetentes is not None and end not in remetentes and end not in proprios:
            continue
        t = normalizar_assunto(e["assunto"])
        if len(t) >= 4:
            acc[t]["dias"].add(e["recebida_em"][:10])
            if end not in proprios:
                acc[t]["pessoas"].add(end)
    saida = [{"tema": t, "dias": len(a["dias"]), "primeira": min(a["dias"]), "ultima": max(a["dias"]),
              "origem": "email", "pessoas": sorted(a["pessoas"])}
             for t, a in acc.items() if len(a["dias"]) >= minimo_dias]
    for p in projetos:
        if p["status"] in ("ativo", "pausado") and slug(p["nome"]) not in slugs_temas:
            saida.append({"tema": p["nome"], "dias": 0, "primeira": "", "ultima": "", "origem": f"gabi-brain projeto:{p['id']}",
                          "pessoas": p["pessoas"], "objetivo": p["objetivo"] or "", "prazo": p["prazo"] or ""})
    return sorted(saida, key=lambda t: (-t["dias"], t["tema"]))


def slug(texto: str) -> str:
    import unicodedata
    s = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")


def _slugs(pasta: Path) -> set[str]:
    return {p.stem for p in pasta.glob("*.md") if not p.stem.startswith("_")} if pasta.is_dir() else set()


def extrair(banco: str, brain: str, dias: int, hoje: date, paperless_cfg=None) -> dict:
    desde = (hoje - timedelta(days=dias)).isoformat()
    con = fontes.abrir(banco)
    proprios = fontes.contas_proprias(con)
    em = fontes.emails(con, desde)
    ps = pessoas(em, fontes.respondidos(con), fontes.contatos(con), proprios)
    b = Path(brain)
    c = {"gerado_em": hoje.isoformat(), "janela_desde": desde, "pessoas": ps,
         "pessoas_agenda": pessoas_agenda(fontes.agenda(con, desde)),
         "empresas": empresas(ps, _slugs(b / "empresas")),
         "temas": temas(em, fontes.projetos(con), _slugs(b / "projetos"), proprios,
                        remetentes={p["endereco"] for p in ps}),
         "correspondentes": []}
    if paperless_cfg:
        c["correspondentes"] = paperless.correspondentes(paperless_cfg["url"], paperless_cfg["token"], desde)
    return c


def resumo(c: dict) -> str:
    linhas = [f"janela desde {c['janela_desde']}",
              f"pessoas: {len(c['pessoas'])}", f"pessoas_agenda: {len(c['pessoas_agenda'])}",
              f"empresas: {len(c['empresas'])}", f"temas: {len(c['temas'])}",
              f"correspondentes: {len(c['correspondentes'])}", "", "top pessoas:"]
    linhas += [f"  {p['interacoes']:>3}  {p['nome'] or '-'} <{p['endereco']}>{' (respondido)' if p['respondido'] else ''}"
               for p in c["pessoas"][:20]]
    linhas += ["", "top empresas:"] + [f"  {e['interacoes']:>3}  {e['dominio']}{' → ' + e['ficha'] if e['ficha'] else ''}"
                                       for e in c["empresas"][:10]]
    linhas += ["", "top temas:"] + [f"  {t['dias']:>3}d {t['tema']} ({t['origem']})" for t in c["temas"][:10]]
    return "\n".join(linhas)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--banco"); ap.add_argument("--brain"); ap.add_argument("--dias", type=int, default=90)
    ap.add_argument("--saida"); ap.add_argument("--resumo", metavar="ARQ")
    a = ap.parse_args(argv)
    if a.resumo:
        print(resumo(json.loads(Path(a.resumo).read_text(encoding="utf-8"))))
        return 0
    faltando = [nome for nome, valor in (("--banco", a.banco), ("--brain", a.brain), ("--saida", a.saida)) if not valor]
    if faltando:
        ap.error(f"obrigatório sem --resumo: {', '.join(faltando)}")
    cfg = None
    if os.environ.get("PAPERLESS_URL") and os.environ.get("PAPERLESS_TOKEN"):
        cfg = {"url": os.environ["PAPERLESS_URL"], "token": os.environ["PAPERLESS_TOKEN"]}
    c = extrair(a.banco, a.brain, a.dias, date.today(), cfg)
    fd = os.open(a.saida, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    os.fchmod(fd, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(c, f, ensure_ascii=False, indent=1)
    print(resumo(c))
    return 0


if __name__ == "__main__":
    sys.exit(main())
