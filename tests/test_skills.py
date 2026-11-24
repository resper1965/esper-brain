import inspect, pathlib, re, sys
RAIZ = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "tools"))
import esper_mcp as m

FERRAMENTAS = {"inicio", "ler", "buscar", "listar_temas", "criar_tema", "mover_tema", "anotar", "acrescentar",
               "substituir", "reescrever_hot", "gravar", "entrada_guardar", "entrada_ler", "entrada_processar",
               "temas_atencao", "pedido_pc_criar", "pedidos_pc_listar", "pedido_pc_concluir"}


def test_ferramentas_existem_no_mcp():
    assert all(callable(getattr(m, f, None)) for f in FERRAMENTAS)


EXTERNAS = {"documentos_buscar", "documentos_baixar", "documentos_texto", "documentos_novos", "documentos_vencimentos",
            "email_listar", "email_ler", "agenda_listar", "teams_pendentes", "promessas_candidatas", "atividade_listar",
            "olhar_a_frente", "familia_vencimentos"}


def test_skills_tem_frontmatter_e_citam_so_ferramentas_reais():
    nomes = {"capturar", "organizar", "pensar-junto", "retomar", "salvar-sessao", "digestao", "vigiar"}
    achadas = {p.parent.name for p in (RAIZ / "skills").glob("*/SKILL.md")}
    assert nomes <= achadas
    for p in (RAIZ / "skills").glob("*/SKILL.md"):
        t = p.read_text(encoding="utf-8")
        assert re.match(rf"^---\nname: {re.escape(p.parent.name)}\ndescription: .+\n---\n", t), p
        for nome, args in re.findall(r"`([a-z_]+)\(([^`]*)\)`", t):
            assert nome in FERRAMENTAS | EXTERNAS, (p, nome)
            if nome in FERRAMENTAS:
                params = set(inspect.signature(getattr(m, nome)).parameters)
                usados = set(re.findall(r"\b([a-z_]+)=", args))
                assert usados <= params, (p, nome, usados - params)


def test_capturar_usa_entrada_e_organizar_processa():
    cap = (RAIZ / "skills/capturar/SKILL.md").read_text(encoding="utf-8")
    org = (RAIZ / "skills/organizar/SKILL.md").read_text(encoding="utf-8")
    assert "entrada_guardar(" in cap and "entrada_ler(" in org and "entrada_processar(" in org
