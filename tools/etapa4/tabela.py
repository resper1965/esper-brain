"""Junta CSVs do harness numa tabela markdown (uma linha por pergunta)."""
import csv
import sys
from pathlib import Path


def montar(csvs):
    camadas, perguntas = [], {}
    for c in csvs:
        with open(c, encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        nome = rows[0]["camada"] if rows else Path(c).stem
        if nome in camadas:
            sys.exit(f"erro: camada repetida: {nome}")
        camadas.append(nome)
        for r in rows:
            perguntas.setdefault(int(r["n"]), {"q": r["pergunta"]})[nome] = r
    com_resposta = {c for d in perguntas.values() for c, r in d.items() if c != "q" and r.get("resposta")}
    cab = ["n", "pergunta"]
    for c in camadas:
        cab += [f"{c}: página?", f"{c}: ms"]
        if c in com_resposta:
            cab.append(f"{c}: resposta")
        cab.append(f"{c}: resposta certa?")
    out = ["| " + " | ".join(cab) + " |", "|" + "---|" * len(cab)]
    for n in sorted(perguntas):
        d = perguntas[n]
        cel = [str(n), d["q"].replace("|", "/")]
        for c in camadas:
            r = d.get(c)
            cel += [("sim" if r["fonte_bateu"] == "True" else "não") if r else "", r["latencia_ms"] if r else ""]
            if c in com_resposta:
                cel.append(((r.get("resposta") or "")[:120].replace("|", "/").replace("\n", " ")) if r else "")
            cel.append("")
        out.append("| " + " | ".join(cel) + " |")
    return "\n".join(out) + "\n"


if __name__ == "__main__":
    print(montar(sys.argv[1:]), end="")
