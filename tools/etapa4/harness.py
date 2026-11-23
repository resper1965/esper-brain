"""Harness da Etapa 4: markdown puro vs GBrain (search/think) sobre o mesmo cérebro."""
import argparse
import csv
import json
import re
import subprocess
import time
import unicodedata
from pathlib import Path

COLUNAS = ["n", "camada", "pergunta", "fonte_esperada", "paginas_achadas",
           "fonte_bateu", "latencia_ms", "erro"]
IGNORAR = {"pessoal/cofre", ".git", ".superpowers", "docs", "tools", "tests",
           "skills", "deploy"}
CHAVES = {"path", "file", "slug", "source", "page", "source_path"}
TIMEOUT = 120


def norm(s):
    s = unicodedata.normalize("NFD", s)
    return "".join(c for c in s if unicodedata.category(c) != "Mn").lower()


def como_lista(v):
    return [v] if isinstance(v, str) else list(v)


def carregar_perguntas(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


STOPWORDS = set("""que quem qual quais de do da dos das o a os as e ele ela dele dela tem ainda para
alem em é eh um uma na no nas nos por com se ou foi era são sao ricardo""".split()) | {"é"}


def palavras_da_pergunta(pergunta):
    return [t for t in re.findall(r"\w+", norm(pergunta)) if t not in STOPWORDS and len(t) >= 4]


def norm_pagina(s, brain=""):
    s = s.strip()
    if brain:
        pre = str(brain).rstrip("/") + "/"
        if s.startswith(pre):
            s = s[len(pre):]
    if s.startswith("./"):
        s = s[2:]
    if s.startswith("brain/"):
        s = s[len("brain/"):]
    if s.endswith(".md"):
        s = s[:-3]
    return s


def bateu(esperadas, achadas, modo="alguma"):
    ach = {norm_pagina(a) for a in achadas}
    ok = [norm_pagina(e) in ach for e in como_lista(esperadas)]
    return all(ok) if modo == "todas" else any(ok)


def _ignorado(rel):
    return any(rel == i or rel.startswith(i + "/") for i in IGNORAR)


def _linha(p, camada, achadas, ms, erro="", resposta=None):
    r = {"n": p["n"], "camada": camada, "pergunta": p["pergunta"],
         "fonte_esperada": como_lista(p["fonte_esperada"]),
         "paginas_achadas": achadas,
         "fonte_bateu": bool(not erro and bateu(p["fonte_esperada"], achadas, p.get("modo", "alguma"))),
         "latencia_ms": round(ms, 1), "erro": erro}
    if resposta is not None:
        r["resposta"] = resposta
    return r


def markdown(brain, perguntas):
    brain = Path(brain)
    saida = []
    for p in perguntas:
        t0 = time.perf_counter()
        termos = [norm(k) for k in p.get("palavras_chave") or palavras_da_pergunta(p["pergunta"])]
        pontos = []
        for f in sorted(brain.rglob("*.md")):
            rel = f.relative_to(brain).as_posix()
            if _ignorado(rel):
                continue
            linhas = [norm(l) for l in f.read_text(encoding="utf-8", errors="ignore").splitlines()]
            n = sum(1 for t in termos if any(t in l for l in linhas))  # substring, como o buscar da Gabi
            if n:
                nl = sum(1 for l in linhas if any(t in l for t in termos))
                pontos.append((-n, -nl, rel))
        pontos.sort()
        achadas = [rel for _, _, rel in pontos[:3]]
        saida.append(_linha(p, "markdown", achadas, (time.perf_counter() - t0) * 1000))
    return saida


def extrair_paginas(obj, brain=""):
    """Percorre o JSON e coleta valores de chaves de caminho, relativos ao brain."""
    achados = []

    def limpa(s):
        return norm_pagina(s, brain)

    def anda(o):
        if isinstance(o, dict):
            for k, v in o.items():
                if k in CHAVES and isinstance(v, str) and v.strip():
                    s = limpa(v)
                    if s not in achados:
                        achados.append(s)
                else:
                    anda(v)
        elif isinstance(o, list):
            for v in o:
                anda(v)

    anda(obj)
    return achados[:3]


def gbrain(brain, perguntas, camada, binario="gbrain"):
    saida = []
    for p in perguntas:
        cmd = [binario, "search", p["pergunta"], "--json"] if camada == "gbrain-search" \
            else [binario, "think", p["pergunta"]]
        t0 = time.perf_counter()
        achadas, erro, resposta = [], "", None
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=TIMEOUT)
            if r.returncode != 0:
                erro = f"saida {r.returncode}"
            else:
                try:
                    dados = json.loads(r.stdout)
                    achadas = extrair_paginas(dados, brain)  # ja no maximo 3
                    if camada == "gbrain-think":
                        resposta = (dados.get("answer") or dados.get("resposta") or dados.get("text")
                                    or "") if isinstance(dados, dict) else str(dados)
                except json.JSONDecodeError:
                    if camada == "gbrain-think":  # texto puro: guarda como resposta
                        resposta = r.stdout.strip()
                        erro = "saida sem JSON; sem citacoes"
                    else:
                        erro = "JSON invalido"
        except subprocess.TimeoutExpired:
            erro = f"timeout {TIMEOUT}s"
        except OSError as e:
            erro = f"falha ao executar: {type(e).__name__}"
        saida.append(_linha(p, camada, achadas, (time.perf_counter() - t0) * 1000, erro, resposta))
    return saida


def gravar_csv(linhas, path):
    cols = COLUNAS + (["resposta"] if any("resposta" in l for l in linhas) else [])
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for l in linhas:
            l = dict(l)
            l["fonte_esperada"] = ";".join(l["fonte_esperada"])
            l["paginas_achadas"] = ";".join(l["paginas_achadas"])
            w.writerow(l)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--camada", required=True, choices=["markdown", "gbrain-search", "gbrain-think"])
    ap.add_argument("--brain", required=True)
    ap.add_argument("--perguntas", required=True)
    ap.add_argument("--saida", required=True)
    ap.add_argument("--gbrain", default="gbrain")
    a = ap.parse_args()
    ps = carregar_perguntas(a.perguntas)
    linhas = markdown(a.brain, ps) if a.camada == "markdown" else gbrain(a.brain, ps, a.camada, a.gbrain)
    gravar_csv(linhas, a.saida)


if __name__ == "__main__":
    main()
