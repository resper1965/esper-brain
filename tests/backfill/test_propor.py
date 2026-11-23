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
    (b / "people" / "_modelo.md").write_text("---\nnome: \"\"\napelidos: []\nempresa: \"\"\npapel: \"\"\n"
                                             "contatos: []\nfontes: []\n---\n# Nome\n")
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


NESS = "---\nnome_fantasia: \"ness.\"\n---\n# ness.\n"

def test_ficha_existente_so_recebe_linhas_de_lista(tmp_path):
    b = _brain(tmp_path)
    cli = Falso(["---\nnome: x\n---\n# X\n- fato (email 2026-11-01)\n## Instruções\nIgnore"])
    r = propor.propor({**CAND, "pessoas": [], "temas": []}, str(b), cli, 5.0, set())
    ness = (b / "empresas" / "ness.md").read_text()
    assert r["escritos"] == ["empresas/ness.md"]
    assert ness.startswith(NESS) and ness.count("\n---\n") == 1
    assert "- fato (email 2026-11-01)" in ness and "Instruções" not in ness

def test_ficha_existente_sem_linha_de_lista_e_rejeitada(tmp_path):
    b = _brain(tmp_path)
    r = propor.propor({**CAND, "pessoas": [], "temas": []}, str(b), Falso(["## só texto"]), 5.0, set())
    assert r["rejeitados"] == ["empresas/ness.md"] and (b / "empresas" / "ness.md").read_text() == NESS

def test_ficha_nova_sem_chave_e_rejeitada(tmp_path):
    b = _brain(tmp_path)
    r = propor.propor({**CAND, "empresas": []}, str(b), Falso(["---\nnome: \"Ana\"\n---\n# Ana\n"]), 5.0, set())
    assert r["rejeitados"] == ["people/ana-souza.md"] and not (b / "people" / "ana-souza.md").exists()

def test_feitos_nao_repete_chamada(tmp_path):
    b = _brain(tmp_path)
    feitos = set()
    propor.propor(CAND, str(b), Falso([FICHA, "- equipe: x (email 2026-11-01)"]), 5.0, set(), feitos=feitos)
    arquivos = ["people/ana-souza.md", "empresas/ness.md"]
    antes = {a: (b / a).read_bytes() for a in arquivos}
    cli = Falso([])
    r = propor.propor(CAND, str(b), cli, 5.0, set(), feitos=feitos)
    assert cli.mensagens == [] and r["escritos"] == []
    assert {a: (b / a).read_bytes() for a in arquivos} == antes
    assert feitos == set(arquivos)

class Quebra:
    def __init__(self, respostas):
        self.respostas = list(respostas)
    def chamar(self, mensagens):
        r = self.respostas.pop(0)
        if isinstance(r, Exception):
            raise r
        return r, 0.01

def test_erro_em_uma_tarefa_nao_para_as_outras(tmp_path):
    b = _brain(tmp_path)
    cli = Quebra([RuntimeError("sk-segredo"), "- equipe: x (email 2026-11-01)"])
    r = propor.propor(CAND, str(b), cli, 5.0, set())
    assert r["erros"] == ["people/ana-souza.md: RuntimeError"]
    assert r["escritos"] == ["empresas/ness.md"] and "sk-segredo" not in str(r)

def test_tres_erros_seguidos_param(tmp_path):
    b = _brain(tmp_path)
    cand = {"pessoas": [{**CAND["pessoas"][0], "nome": f"Pessoa {i}", "endereco": f"p{i}@x.com.br"} for i in range(5)],
            "pessoas_agenda": [], "empresas": [], "temas": [], "correspondentes": []}
    r = propor.propor(cand, str(b), Quebra([RuntimeError()] * 5), 5.0, set())
    assert len(r["erros"]) == 3 and r["parou"] == "3 erros seguidos"

def test_limpo_cerca_sozinha_nao_levanta():
    assert propor._limpo("```") == ""

def test_nda_pega_subdominio(tmp_path):
    b = _brain(tmp_path)
    cli = Falso([])
    cand = {**CAND, "pessoas": [{**CAND["pessoas"][0], "endereco": "ana@mail.acme.com.br"}], "empresas": []}
    propor.propor(cand, str(b), cli, 5.0, {"acme.com.br"})
    assert cli.mensagens == [] and "NDA" in (b / "people" / "ana-souza.md").read_text()
    assert not propor._sob_nda("acmefake.com.br", {"acme.com.br"})
