import sqlite3
import pytest
from tools.backfill import fontes

def test_abrir_e_so_leitura(banco):
    con = fontes.abrir(banco)
    with pytest.raises(sqlite3.OperationalError):
        con.execute("delete from email_msg")

def test_emails_respeita_janela(banco):
    con = fontes.abrir(banco)
    rems = {e["remetente"] for e in fontes.emails(con, "2026-08-25")}
    assert "velho@antigo.com" not in rems
    assert "ana@acme.com.br" in rems

def test_emails_so_contas_sim_e_sem_lixeira(banco):
    con = fontes.abrir(banco)
    rems = {e["remetente"] for e in fontes.emails(con, "2026-08-25")}
    assert "carlos@acme.com.br" not in rems
    assert "lixo@acme.com.br" not in rems

def test_contas_respondidos_contatos(banco):
    con = fontes.abrir(banco)
    assert fontes.contas_proprias(con) == {"resper@gmail.com", "ricardo@ness.com.br", "velha@esper.ws"}
    # conta 'nao' ignorada; sentinela endereco='' excluída
    assert fontes.respondidos(con) == {"bob@acme.com.br", "so-respondido@acme.com.br"}
    assert fontes.contatos(con)["ana@acme.com.br"] == "Ana Souza"

def test_agenda_e_projetos(banco):
    con = fontes.abrir(banco)
    ag = fontes.agenda(con, "2026-08-25")
    assert {a["organizador"] for a in ag} == {"Ana Souza"}
    assert len(ag) == 2                      # evento da agenda_fonte 'nao' não entra
    pj = fontes.projetos(con)
    assert pj == [{"id": 7, "nome": "Trocar de carro", "objetivo": "SUV híbrido", "status": "ativo",
                   "prazo": "2027-03-31", "pessoas": ["Vendedor Toyota"]}]
