"""Barra número de documento e arquivo do cofre antes de publicar a branch do backfill."""
import os
import re
import sys
from pathlib import Path

PADROES = {
    "cpf": re.compile(r"(?<!\d)\d{3}\.?\d{3}\.?\d{3}-?\d{2}(?!\d)"),
    "cnpj": re.compile(r"(?<!\d)\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}(?!\d)"),
    "rg": re.compile(r"\bRG\b\s*(?:n[º°o.]?\s*)?:?\s*[\d.\-xX]{7,}", re.I),
    "passaporte": re.compile(
        r"\bpassaporte\b[^A-Za-z0-9\n]{0,4}(?:n[º°o.]?[^A-Za-z0-9\n]{0,3})?"
        r"(?=[A-Za-z0-9]*\d)[A-Za-z0-9]{6,9}\b",
        re.I,
    ),
    "cnh": re.compile(r"\bCNH\b[^\d\n]{0,10}?\d{9,11}(?!\d)", re.I),
    "renavam": re.compile(r"\bRENAVAM\b[^\d\n]{0,10}?\d{9,11}(?!\d)", re.I),
}


def achados(texto: str) -> list[str]:
    return [nome for nome, rx in PADROES.items() if rx.search(texto)]


def _normalizado(c: str) -> str:
    return os.path.normpath(c).replace("\\", "/")


def _no_cofre(c: str) -> bool:
    n = _normalizado(c)
    return n == "pessoal/cofre" or n.startswith("pessoal/cofre/")


def main(caminhos) -> int:
    ruim = 0
    for c in caminhos:
        if _no_cofre(c):
            print(f"BLOQUEADO (cofre): {c}"); ruim = 1; continue
        p = Path(c)
        if not p.exists():
            print(f"AVISO: não encontrado: {c}"); ruim = 1; continue
        if not (p.is_dir() or p.is_file()):
            print(f"AVISO: não é arquivo: {c}"); ruim = 1; continue
        arquivos = sorted(f for f in p.rglob("*") if f.is_file()) if p.is_dir() else [p]
        for f in arquivos:
            if _no_cofre(str(f)):
                print(f"BLOQUEADO (cofre): {f}"); ruim = 1; continue
            a = achados(f.read_text(encoding="utf-8", errors="ignore"))
            if a:
                print(f"BLOQUEADO ({', '.join(a)}): {f}"); ruim = 1
    return ruim


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
