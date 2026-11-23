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
        camadas.append(nome)
        for r in rows:
            perguntas.setdefault(int(r["n"]), {"q": r["pergunta"]})[nome] = r
    cab = ["n", "pergunta"]
    for c in camadas:
        cab += [f"{c}: página?", f"{c}: ms", f"{c}: resposta certa?"]
    out = ["| " + " | ".join(cab) + " |", "|" + "---|" * len(cab)]
    for n in sorted(perguntas):
        d = perguntas[n]
        cel = [str(n), d["q"].replace("|", "/")]
        for c in camadas:
            r = d.get(c)
            cel += [("sim" if r["fonte_bateu"] == "True" else "não") if r else "", r["latencia_ms"] if r else "", ""]
        out.append("| " + " | ".join(cel) + " |")
    return "\n".join(out) + "\n"


if __name__ == "__main__":
    print(montar(sys.argv[1:]), end="")
