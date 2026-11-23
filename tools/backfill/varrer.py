"""Barra número de documento e arquivo do cofre antes de publicar a branch do backfill."""
import re
import sys
from pathlib import Path

PADROES = {
    "cpf": re.compile(r"(?<!\d)\d{3}\.?\d{3}\.?\d{3}-?\d{2}(?!\d)"),
    "cnpj": re.compile(r"(?<!\d)\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}(?!\d)"),
    "rg": re.compile(r"\bRG\b\s*:?\s*[\d.\-xX]{7,}", re.I),
}


def achados(texto: str) -> list[str]:
    return [nome for nome, rx in PADROES.items() if rx.search(texto)]


def main(caminhos) -> int:
    ruim = 0
    for c in caminhos:
        if c.replace("\\", "/").startswith("pessoal/cofre/"):
            print(f"BLOQUEADO (cofre): {c}"); ruim = 1; continue
        p = Path(c)
        if p.is_file():
            a = achados(p.read_text(encoding="utf-8", errors="ignore"))
            if a:
                print(f"BLOQUEADO ({', '.join(a)}): {c}"); ruim = 1
    return ruim


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
