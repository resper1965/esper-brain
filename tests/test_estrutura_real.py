import pathlib, sys
RAIZ = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "tools"))
import esper_mcp as m


def test_estrutura_migrada(monkeypatch):
    monkeypatch.setattr(m, "RAIZ", RAIZ)
    soltos = [p.name for p in (RAIZ / "projetos").glob("*.md") if not p.name.startswith("_")]
    assert soltos == [], f"temas fora de área: {soltos}"
    trab = m.listar_temas(area="trabalho")
    assert "ness · Pinheiro Guimarães" in trab and "Alupar" in trab
    pat = m.listar_temas(area="patrimonio")
    for bem in ("fazenda-piedade", "casa-bento-de-andrade", "apto-rua-caconde", "armazem-rua-mendes-caldeira"):
        assert bem in pat
    assert "Fazenda em Piedade" in (RAIZ / "empresas/baalbeck.md").read_text(encoding="utf-8")
    fk = (RAIZ / "empresas/fakiha.md").read_text(encoding="utf-8")
    assert all(x in fk for x in ("Bento de Andrade", "Caconde", "Mendes Caldeira", "herança"))
    assert (RAIZ / "entrada.md").read_text(encoding="utf-8").startswith("# Entrada")

