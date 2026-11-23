import subprocess, sys
from pathlib import Path
from tools.backfill import varrer

def test_achados():
    assert varrer.achados("CPF 123.456.789-09") == ["cpf"]
    assert varrer.achados("cnpj 12.345.678/0001-90") == ["cnpj"]
    assert varrer.achados("RG: 12.345.678-9") == ["rg"]
    assert varrer.achados("reunião em 2026-11-10 às 14:00, sala 1203") == []

def test_rg_com_nº():
    assert varrer.achados("RG nº 12345678") == ["rg"]
    assert varrer.achados("RG n° 12.345.678-9") == ["rg"]

def test_passaporte():
    assert varrer.achados("passaporte: FX123456") == ["passaporte"]
    assert varrer.achados("passaporte renovado em 2026") == []

def test_cnh():
    assert varrer.achados("CNH nº 123456789") == ["cnh"]
    # 11 dígitos também têm forma de CPF: bloqueia, com os dois rótulos
    assert "cnh" in varrer.achados("CNH 12345678901")

def test_renavam():
    assert varrer.achados("RENAVAM: 123456789") == ["renavam"]

def test_cli_barra_cofre_e_numero(tmp_path):
    ok = tmp_path / "people" / "a.md"; ok.parent.mkdir(); ok.write_text("tudo certo")
    ruim = tmp_path / "people" / "b.md"; ruim.write_text("CPF 12345678909")
    script = Path(varrer.__file__)
    rodar = lambda *a: subprocess.run([sys.executable, str(script), *a], cwd=tmp_path).returncode
    assert rodar("people/a.md") == 0
    assert rodar("people/b.md") == 1
    assert rodar("pessoal/cofre/x.md") == 1
    assert rodar("./pessoal/cofre/x.md") == 1

def test_cli_varre_pasta_recursivamente(tmp_path):
    fundo = tmp_path / "projetos" / "tema" / "sub"; fundo.mkdir(parents=True)
    (fundo / "nota.md").write_text("CPF 12345678909")
    script = Path(varrer.__file__)
    rodar = lambda *a: subprocess.run([sys.executable, str(script), *a], cwd=tmp_path).returncode
    assert rodar("projetos") == 1

def test_cli_caminho_ausente_bloqueia(tmp_path):
    script = Path(varrer.__file__)
    r = subprocess.run([sys.executable, str(script), "people/nao_existe.md"], cwd=tmp_path, capture_output=True, text=True)
    assert r.returncode == 1
    assert "AVISO: não encontrado: people/nao_existe.md" in r.stdout
