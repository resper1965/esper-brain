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
    assert c["pessoas"][1]["respondido"] is True
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
