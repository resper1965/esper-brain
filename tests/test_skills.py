import pathlib, re, sys
RAIZ = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "tools"))
import esper_mcp as m

FERRAMENTAS = {"inicio", "ler", "buscar", "listar_temas", "criar_tema", "mover_tema", "anotar", "acrescentar",
               "substituir", "reescrever_hot", "gravar", "entrada_guardar", "entrada_ler", "entrada_processar"}


def test_ferramentas_existem_no_mcp():
    assert all(callable(getattr(m, f, None)) for f in FERRAMENTAS)


def test_skills_tem_frontmatter_e_citam_so_ferramentas_reais():
    nomes = {"capturar", "organizar", "pensar-junto", "retomar", "salvar-sessao", "digestao"}
    achadas = {p.parent.name for p in (RAIZ / "skills").glob("*/SKILL.md")}
    assert nomes <= achadas
    for p in (RAIZ / "skills").glob("*/SKILL.md"):
        t = p.read_text(encoding="utf-8")
        assert re.match(rf"^---\nname: {re.escape(p.parent.name)}\ndescription: .+\n---\n", t), p
        citadas = set(re.findall(r"`([a-z_]+)\(", t))
        desconhecidas = {c for c in citadas if c.startswith(("entrada", "mover", "criar", "listar"))} - FERRAMENTAS
        assert not desconhecidas, (p, desconhecidas)


def test_capturar_usa_entrada_e_organizar_processa():
    cap = (RAIZ / "skills/capturar/SKILL.md").read_text(encoding="utf-8")
    org = (RAIZ / "skills/organizar/SKILL.md").read_text(encoding="utf-8")
    assert "entrada_guardar(" in cap and "entrada_ler(" in org and "entrada_processar(" in org
