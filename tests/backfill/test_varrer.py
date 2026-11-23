import subprocess, sys
from pathlib import Path
from tools.backfill import varrer

def test_achados():
    assert varrer.achados("CPF 123.456.789-09") == ["cpf"]
    assert varrer.achados("cnpj 12.345.678/0001-90") == ["cnpj"]
    assert varrer.achados("RG: 12.345.678-9") == ["rg"]
    assert varrer.achados("reunião em 2026-11-10 às 14:00, sala 1203") == []

def test_cli_barra_cofre_e_numero(tmp_path):
    ok = tmp_path / "people" / "a.md"; ok.parent.mkdir(); ok.write_text("tudo certo")
    ruim = tmp_path / "people" / "b.md"; ruim.write_text("CPF 12345678909")
    script = Path(varrer.__file__)
    rodar = lambda *a: subprocess.run([sys.executable, str(script), *a], cwd=tmp_path).returncode
    assert rodar("people/a.md") == 0
    assert rodar("people/b.md") == 1
    assert rodar("pessoal/cofre/x.md") == 1
