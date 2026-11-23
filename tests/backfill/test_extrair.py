import json
from datetime import date
from tools.backfill import extrair

def test_automaticos():
    for e in ["noreply@x.com", "no-reply@x.com", "notifications@github.com", "news@loja.com", "x@linkedin.com", "mailer-daemon@x"]:
        assert extrair.e_automatico(e)
    assert not extrair.e_automatico("ana@acme.com.br")

def test_normalizar_assunto():
    assert extrair.normalizar_assunto("RE: Fwd:  Proposta  ACME") == "proposta acme"

def test_extrair_ponta_a_ponta(banco, tmp_path):
    brain = tmp_path / "brain"
    (brain / "empresas").mkdir(parents=True)
    (brain / "empresas" / "ness.md").write_text("x")
    (brain / "projetos").mkdir()
    c = extrair.extrair(banco, str(brain), 90, date(2026, 11, 23))
    enderecos = [p["endereco"] for p in c["pessoas"]]
    assert enderecos == ["ana@acme.com.br", "bob@acme.com.br"]          # ana: 3 e-mails; bob: respondido
    ana = c["pessoas"][0]
    assert ana["nome"] == "Ana Souza" and ana["interacoes"] == 3 and ana["ultima"] == "2026-11-10"
    bob = c["pessoas"][1]
    assert bob["respondido"] is True and bob["interacoes"] == 1
    assert bob["primeira"] == bob["ultima"] == "2026-11-01"      # data do sync de email_respondido nunca entra
    assert "" not in enderecos and "so-respondido@acme.com.br" not in enderecos and "naoconsentido@acme.com.br" not in enderecos
    assert all(e not in enderecos for e in ["noreply@banco.com.br", "news@loja.com", "spam@x.com", "ricardo@ness.com.br"])
    assert c["pessoas_agenda"][0]["nome"] == "Ana Souza" and c["pessoas_agenda"][0]["reunioes"] == 2
    assert c["empresas"][0]["dominio"] == "acme.com.br" and c["empresas"][0]["ficha"] is None
    temas = {t["tema"]: t for t in c["temas"]}
    assert "proposta acme" in temas and temas["proposta acme"]["dias"] == 3
    assert temas["Trocar de carro"]["origem"] == "gabi-brain projeto:7"
    json.dumps(c)  # serializável

def test_empresa_com_ficha_existente():
    ps = [{"endereco": "x@ness.com.br", "interacoes": 4}]
    assert extrair.empresas(ps, {"ness"})[0]["ficha"] == "ness"

def test_resumo_tem_contagens(banco, tmp_path):
    brain = tmp_path / "b"; (brain / "empresas").mkdir(parents=True); (brain / "projetos").mkdir()
    texto = extrair.resumo(extrair.extrair(banco, str(brain), 90, date(2026, 11, 23)))
    assert "pessoas: 2" in texto and "empresas: 1" in texto

def test_main_fixa_600_em_arquivo_existente(banco, tmp_path, monkeypatch):
    monkeypatch.delenv("PAPERLESS_URL", raising=False)
    monkeypatch.delenv("PAPERLESS_TOKEN", raising=False)
    brain = tmp_path / "b"; (brain / "empresas").mkdir(parents=True); (brain / "projetos").mkdir()
    saida = tmp_path / "candidatos.json"
    saida.write_text("velho")
    saida.chmod(0o644)
    assert extrair.main(["--banco", banco, "--brain", str(brain), "--saida", str(saida)]) == 0
    assert saida.stat().st_mode & 0o777 == 0o600

def test_main_exige_argumentos_sem_resumo():
    import pytest
    with pytest.raises(SystemExit):
        extrair.main(["--saida", "/tmp/x.json"])

def test_respondido_sem_email_nao_qualifica_e_nunca_zero_interacoes():
    emails = [{"remetente": "x@y.com", "assunto": "a", "recebida_em": "2026-11-01T10:00:00Z", "conta": "c", "classe": "normal", "lista": 0}]
    ps = extrair.pessoas(emails, {"x@y.com", "z@y.com", ""}, {}, set())
    assert [p["endereco"] for p in ps] == ["x@y.com"] and all(p["interacoes"] >= 1 for p in ps)
    assert ps[0]["ultima"] == "2026-11-01"


def test_robo_sem_contato_e_sem_resposta_nao_vira_pessoa_nem_tema():
    em = [{"conta": "c", "remetente": "monitor@ness.com.br", "assunto": "[ness.os] monitor do hub com falha",
           "recebida_em": f"2026-11-{d:02d}T10:00:00Z", "classe": "normal", "lista": 0} for d in range(1, 8)]
    em += [{"conta": "c", "remetente": "ana@acme.com.br", "assunto": "Proposta Acme",
            "recebida_em": f"2026-11-{d:02d}T10:00:00Z", "classe": "normal", "lista": 0} for d in range(1, 4)]
    ps = extrair.pessoas(em, set(), {"ana@acme.com.br": "Ana Souza"}, set())
    assert [p["endereco"] for p in ps] == ["ana@acme.com.br"]
    ts = extrair.temas(em, [], set(), set(), remetentes={p["endereco"] for p in ps})
    assert [t["tema"] for t in ts] == ["proposta acme"]


def test_empresa_casa_ficha_com_hifen():
    ps = [{"endereco": "x@ionic.health", "interacoes": 3}]
    assert extrair.empresas(ps, {"ionic-health", "ness"})[0]["ficha"] == "ionic-health"
