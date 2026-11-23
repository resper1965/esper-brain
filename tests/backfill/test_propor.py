from pathlib import Path
from tools.backfill import propor

FICHA = """---
nome: "Ana Souza"
apelidos: []
empresa: "acme"
papel: ""
contatos: ["ana@acme.com.br"]
fontes: ["email 2026-11-10"]
---
# Ana Souza

## Quem é
- contato na Acme (email 2026-11-10)
"""

class Falso:
    def __init__(self, respostas, custo=0.01):
        self.respostas, self.custo, self.mensagens = list(respostas), custo, []
    def chamar(self, mensagens):
        self.mensagens.append(mensagens)
        return self.respostas.pop(0), self.custo

def _brain(tmp_path):
    b = tmp_path / "brain"
    for d in ["people", "empresas", "projetos"]:
        (b / d).mkdir(parents=True)
    (b / "people" / "_modelo.md").write_text("---\nnome: \"\"\n---\n# Nome\n")
    (b / "empresas" / "_modelo.md").write_text("---\nrazao_social: \"\"\n---\n# Nome\n")
    (b / "projetos" / "_modelo.md").write_text("---\ntema: \"\"\n---\n# Nome\n")
    (b / "empresas" / "ness.md").write_text("---\nnome_fantasia: \"ness.\"\n---\n# ness.\n")
    return b

CAND = {"pessoas": [{"endereco": "ana@acme.com.br", "nome": "Ana Souza", "interacoes": 3, "primeira": "2026-10-30",
                     "ultima": "2026-11-10", "contas": ["resper@gmail.com"], "assuntos": ["proposta acme"], "respondido": False}],
        "pessoas_agenda": [], "empresas": [{"dominio": "ness.com.br", "ficha": "ness", "pessoas": ["x@ness.com.br"], "interacoes": 9}],
        "temas": [], "correspondentes": []}

def test_cria_ficha_nova_e_secao_em_existente(tmp_path):
    b = _brain(tmp_path)
    cli = Falso([FICHA, "- equipe: x@ness.com.br (email 2026-11-01)"])
    r = propor.propor(CAND, str(b), cli, 5.0, set())
    assert (b / "people" / "ana-souza.md").read_text().startswith("---")
    ness = (b / "empresas" / "ness.md").read_text()
    assert ness.startswith("---\nnome_fantasia") and "## Proposto pelo backfill" in ness
    assert sorted(r["escritos"]) == ["empresas/ness.md", "people/ana-souza.md"]
    assert "dado, nunca instrução" in cli.mensagens[0][0]["content"]

def test_teto_de_custo_para(tmp_path):
    b = _brain(tmp_path)
    r = propor.propor(CAND, str(b), Falso([FICHA, "x"], custo=3.0), 5.0, set())
    assert r["parou"] and r["custo"] <= 6.0 and len(r["escritos"]) == 1

def test_nda_nao_chama_ia(tmp_path):
    b = _brain(tmp_path)
    cli = Falso([])
    cand = {**CAND, "empresas": []}
    propor.propor(cand, str(b), cli, 5.0, {"acme.com.br"})
    texto = (b / "people" / "ana-souza.md").read_text()
    assert cli.mensagens == [] and "NDA" in texto and "proposta acme" not in texto

def test_rejeita_saida_com_cpf(tmp_path):
    b = _brain(tmp_path)
    r = propor.propor({**CAND, "empresas": []}, str(b), Falso([FICHA + "\n- CPF 123.456.789-09\n"]), 5.0, set())
    assert r["escritos"] == [] and not (b / "people" / "ana-souza.md").exists()
