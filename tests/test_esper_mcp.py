import subprocess, sys, shutil, pathlib, pytest
RAIZ_REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ_REPO / "tools"))
import esper_mcp as m

@pytest.fixture
def cerebro(tmp_path, monkeypatch):
    remoto = tmp_path / "remoto.git"
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(remoto)], check=True)
    r = tmp_path / "eb"
    subprocess.run(["git", "clone", "-q", str(remoto), str(r)], check=True, capture_output=True)
    g = lambda *a: subprocess.run(["git", "-C", str(r), *a], check=True, capture_output=True)
    g("checkout", "-q", "-b", "main"); g("config", "user.email", "t@t"); g("config", "user.name", "t")
    (r / "tools").mkdir(); shutil.copy(RAIZ_REPO / "tools/gravar.sh", r / "tools/gravar.sh")
    (r / "projetos").mkdir(); shutil.copy(RAIZ_REPO / "projetos/_modelo.md", r / "projetos/_modelo.md")
    (r / "pessoal/cofre").mkdir(parents=True); (r / "pessoal/cofre/doc.md").write_bytes(b"\x00GITCRYPT\x00xx")
    for n in ("AGENTS.md", "mapa.md", "hot.md", "pendencias.md"):
        (r / n).write_text(f"# {n}\n", encoding="utf-8")
    g("add", "-A"); g("commit", "-qm", "init"); g("push", "-qu", "origin", "main")
    monkeypatch.setattr(m, "RAIZ", r.resolve())
    return r

def test_fluxo_capturar(cerebro):
    assert "nenhum tema" in m.listar_temas()
    m.criar_tema("trocar-de-carro", "Trocar de carro", ["carro", "suv"], area="casa")
    assert "Trocar de carro" in m.listar_temas() and "casa" in m.listar_temas()
    m.anotar("projetos/casa/trocar-de-carro.md", "Ideias soltas", "2026-11-17: ver híbrido")
    m.anotar("projetos/casa/trocar-de-carro.md", "ideias soltas", "2026-11-18: mais nova")
    t = (cerebro / "projetos/casa/trocar-de-carro.md").read_text()
    assert t.index("mais nova") < t.index("ver híbrido") and t.index("## Ideias soltas") < t.index("mais nova")
    assert m.gravar("capturar(trocar-de-carro): híbrido").startswith("gravado:")
    assert m.gravar("de novo") == "nada a gravar"
    assert "hibrido" in m.buscar("HIBRIDO") or "híbrido" in m.buscar("HIBRIDO")

def test_recusas(cerebro):
    for c in ("/etc/passwd", "../x.md", "projetos/../../x.md", ".git/config", "tools/gravar.sh", "bruto/a.md"):
        with pytest.raises(m.Recusa):
            m.ler(c)
    with pytest.raises(m.Recusa):
        m.acrescentar("AGENTS.md", "mudar regras")
    with pytest.raises(m.Recusa):
        m.acrescentar("pessoal/cofre/novo.md", "CPF")
    with pytest.raises(m.Recusa):
        m.anotar("projetos/_modelo.md", "Ideias soltas", "x")
    with pytest.raises(m.Recusa):
        m.ler("pessoal/cofre/doc.md")  # cifrado: avisa que falta destravar
    with pytest.raises(m.Recusa):
        m.criar_tema("Tem Acento", "x", area="casa")
    (cerebro / "fora").mkdir(); (cerebro / "projetos/link.md").symlink_to("/etc/hostname")
    with pytest.raises(m.Recusa):
        m.ler("projetos/link.md")

def test_diario_e_substituir(cerebro):
    m.acrescentar("diario/2026/11-17.md", "# 2026-11-17\n\n## 19:30 · telegram\n- decidi X")
    m.acrescentar("pendencias.md", "- 2026-11-20 [teste]: fazer Y")
    m.criar_tema("t", "T", area="pessoal")
    m.substituir("projetos/pessoal/t.md", 'proximo_passo: ""', 'proximo_passo: "ligar"')
    with pytest.raises(m.Recusa):
        m.substituir("projetos/pessoal/t.md", "não existe", "x")
    out = m.gravar("sessão")
    assert out.startswith("gravado:")
    log = subprocess.run(["git", "-C", str(cerebro), "show", "--stat", "HEAD"], capture_output=True, text=True).stdout
    assert "diario/2026/11-17.md" in log and "pendencias.md" in log and "projetos/pessoal/t.md" in log
    assert "proximo_passo: \"ligar\"" in m.listar_temas() or "ligar" in m.listar_temas()

def test_inicio(cerebro):
    t = m.inicio()
    assert "===== AGENTS.md" in t and "===== pendencias.md" in t

def test_reescrever_hot(cerebro):
    with pytest.raises(m.Recusa):
        m.reescrever_hot("sem título")
    m.reescrever_hot("# Hot\n\n- agenda: reunião 10h")
    assert m.gravar("digestão").startswith("gravado:")
    assert "reunião 10h" in (cerebro / "hot.md").read_text()

def test_acrescentar_item_de_lista_sem_linha_em_branco(cerebro):
    (cerebro / "pendencias.md").write_text("# Pendências\n\n- [ ] a\n", encoding="utf-8")
    m.acrescentar("pendencias.md", "- [ ] b")
    assert (cerebro / "pendencias.md").read_text() == "# Pendências\n\n- [ ] a\n- [ ] b\n"


def test_buscar_nao_devolve_cofre_destravado(cerebro):
    # clone destravado: o cofre está em claro no disco
    (cerebro / "pessoal/cofre/doc.md").write_text("CPF 123.456.789-00\n", encoding="utf-8")
    (cerebro / "pendencias.md").write_text("# p\n- ver CPF da Giovanna\n", encoding="utf-8")
    r = m.buscar("CPF")
    assert "pendencias.md" in r
    assert "pessoal/cofre" not in r and "123.456" not in r
    with pytest.raises(m.Recusa):
        m.buscar("CPF", "pessoal/cofre")
    assert "123.456" in m.ler("pessoal/cofre/doc.md")  # ler por caminho explícito continua


def test_buscar_pasta_fica_dentro_do_cerebro(cerebro):
    irmao = cerebro.parent / (cerebro.name + "-x")
    irmao.mkdir()
    (irmao / "fora.md").write_text("segredo de fora\n", encoding="utf-8")
    for pasta in ("../" + irmao.name, "..", "../..", ".git", "bruto"):
        with pytest.raises(m.Recusa):
            m.buscar("segredo", pasta)


def test_gravar_caminho_com_espaco(cerebro):
    m.criar_tema("x", "X", area="casa")
    (cerebro / "projetos/com espaco.md").write_text("# a\n", encoding="utf-8")
    assert m.gravar("teste espaço").startswith("gravado:")
    st = subprocess.run(["git", "-C", str(cerebro), "status", "--porcelain"], capture_output=True, text=True).stdout
    assert st == ""


@pytest.mark.parametrize("palavra,radical", [
    ("filhas", "filha"), ("filha", "filha"), ("holdings", "holding"), ("patrimoniais", "patrimonial"),
    ("pendências", "pendencia"), ("pendentes", "pendente"), ("questões", "questao"), ("pães", "pao"),
    ("papéis", "papel"), ("carros", "carro"), ("mês", "mes"), ("gás", "gas"), ("ônibus", "onibus"),
])
def test_radical(palavra, radical):
    assert m._radical(m._sem_acento(palavra)) == radical


def test_buscar_acha_singular_e_plural_e_varias_palavras(cerebro):
    (cerebro / "empresas").mkdir()
    (cerebro / "empresas/baalbeck.md").write_text("papel: titular — holding patrimonial do Ricardo\n", encoding="utf-8")
    (cerebro / "pessoal/familia").mkdir(parents=True)
    (cerebro / "pessoal/familia/louise.md").write_text("- parentesco: filha\n", encoding="utf-8")
    assert "louise.md" in m.buscar("filhas")
    assert "baalbeck.md" in m.buscar("holdings patrimoniais")
    assert "nada encontrado" == m.buscar("holdings vinicolas")      # todas as palavras precisam estar na linha
    assert "baalbeck.md" in m.buscar("Holding Patrimonial")          # frase exata continua achando


@pytest.mark.parametrize("kw,pasta", [
    (dict(area="familia"), "projetos/familia"),
    (dict(area="trabalho"), "projetos/trabalho"),
    (dict(area="trabalho", empresa="ness", marca="forense.io", cliente="Zacarelli"), "projetos/trabalho/ness"),
    (dict(area="trabalho", empresa="ionic", frente="produto"), "projetos/trabalho/ionic/produto"),
    (dict(area="trabalho", empresa="bekaa"), "projetos/trabalho/bekaa"),
    (dict(area="trabalho", empresa="pf"), "projetos/trabalho/pf"),
    (dict(area="patrimonio", holding="fakiha"), "projetos/patrimonio/fakiha"),
    (dict(area="patrimonio"), "projetos/patrimonio"),
])
def test_pasta_do_tema(kw, pasta):
    assert m._pasta_do_tema(**kw) == pasta


@pytest.mark.parametrize("kw", [
    dict(area=""), dict(area="trabalhos"), dict(area="trabalho", empresa="secops"),
    dict(area="trabalho", empresa="ionic"),                       # IONIC exige frente
    dict(area="trabalho", empresa="ness", frente="produto"),       # frente só na IONIC
    dict(area="trabalho", empresa="bekaa", marca="trustness"),     # marca só da ness
    dict(area="trabalho", marca="trustness"),                      # marca exige empresa
    dict(area="casa", empresa="ness"), dict(area="casa", cliente="X"),
    dict(area="patrimonio", holding="outra"), dict(area="casa", holding="fakiha"),
])
def test_pasta_do_tema_recusa(kw):
    with pytest.raises(m.Recusa):
        m._pasta_do_tema(**kw)


def test_criar_tema_preenche_campos_e_papel(cerebro):
    r = m.criar_tema("proposta-pentest", "Proposta pentest", ["pentest"], area="trabalho", empresa="ness",
                     cliente="Pinheiro Guimarães")
    assert "projetos/trabalho/ness/proposta-pentest.md" in r
    fm = m._frontmatter((cerebro / "projetos/trabalho/ness/proposta-pentest.md").read_text())
    assert (fm["area"], fm["empresa"], fm["cliente"], fm["papel"]) == ("trabalho", "ness", "Pinheiro Guimarães", "CEO")
    with pytest.raises(m.Recusa):   # slug único no cérebro todo
        m.criar_tema("proposta-pentest", "Outra", area="pessoal")


def test_listar_temas_filtra_por_area_e_empresa(cerebro):
    m.criar_tema("a", "Tema A", area="trabalho", empresa="ionic", frente="governanca")
    m.criar_tema("b", "Tema B", area="trabalho", empresa="ness", cliente="Alupar")
    m.criar_tema("c", "Tema C", area="patrimonio", holding="baalbeck")
    tudo = m.listar_temas()
    assert all(x in tudo for x in ("Tema A", "Tema B", "Tema C"))
    assert "ness · Alupar" in tudo
    so_trab = m.listar_temas(area="trabalho")
    assert "Tema A" in so_trab and "Tema C" not in so_trab
    assert "Tema B" not in m.listar_temas(empresa="ionic")
    assert m.listar_temas(area="saude") == "nenhum tema nessa área"


def test_mover_tema(cerebro):
    m.criar_tema("armazem", "Armazém", area="trabalho", empresa="ness", marca="trustness")
    r = m.mover_tema("projetos/trabalho/ness/armazem.md", area="patrimonio", holding="fakiha")
    assert "projetos/patrimonio/fakiha/armazem.md" in r
    assert not (cerebro / "projetos/trabalho/ness/armazem.md").exists()
    fm = m._frontmatter((cerebro / "projetos/patrimonio/fakiha/armazem.md").read_text())
    assert (fm["area"], fm["holding"], fm["empresa"], fm["marca"], fm["papel"]) == ("patrimonio", "fakiha", "", "", "")
    with pytest.raises(m.Recusa):
        m.mover_tema("projetos/patrimonio/fakiha/armazem.md", area="patrimonio", holding="fakiha")  # já está lá
    with pytest.raises(m.Recusa):
        m.mover_tema("hot.md", area="casa")
    with pytest.raises(m.Recusa):
        m.mover_tema("projetos/_modelo.md", area="casa")
    assert "Armazém" in m.listar_temas(area="patrimonio")


def test_gravar_tema_movido(cerebro):
    m.criar_tema("x", "X", area="casa"); m.gravar("cria x")
    m.mover_tema("projetos/casa/x.md", area="pessoal")
    assert m.gravar("move x").startswith("gravado:")
    st = subprocess.run(["git", "-C", str(cerebro), "status", "--porcelain"], capture_output=True, text=True).stdout
    assert st.strip() == ""


def test_entrada(cerebro, monkeypatch):
    import datetime as dt
    monkeypatch.setattr(m, "_agora", lambda: dt.datetime(2026, 11, 23, 9, 5, tzinfo=m.FUSO))
    r = m.entrada_guardar("  tô pensando em trocar a Ranger  ", "Casa › Trocar de carro")
    assert r.startswith("gravado:")
    m.entrada_guardar("e o prazo é sexta")
    t = (cerebro / "entrada.md").read_text()
    assert "- 2026-11-23 09:05 · tô pensando em trocar a Ranger · palpite: Casa › Trocar de carro" in t
    assert "- 2026-11-23 09:05 · e o prazo é sexta\n" in t
    assert m.entrada_ler().splitlines()[0].startswith("1. 2026-11-23 09:05 · tô pensando")
    assert "processadas 1" in m.entrada_processar([2])
    assert "prazo é sexta" not in (cerebro / "entrada.md").read_text()
    d = (cerebro / "diario/2026/11-23.md").read_text()
    assert d.startswith("# 2026-11-23") and "## Entrada processada 09:05" in d and "e o prazo é sexta" in d
    with pytest.raises(m.Recusa):
        m.entrada_processar([5])
    with pytest.raises(m.Recusa):
        m.entrada_guardar("   ")
    m.entrada_processar([1])
    assert m.entrada_ler() == "entrada vazia"


def test_cliente_com_cerquilha_sobrevive_ao_mover(cerebro):
    m.criar_tema("loja", "Loja", area="trabalho", empresa="ness", cliente="Loja #1")
    m.mover_tema("projetos/trabalho/ness/loja.md", area="trabalho", empresa="bekaa")
    t = (cerebro / "projetos/trabalho/bekaa/loja.md").read_text()
    assert 'cliente: "Loja #1"' in t


def test_tema_em_pasta_e_readme_estrutural(cerebro):
    (cerebro / "projetos/casa/reforma/sub").mkdir(parents=True)
    (cerebro / "projetos/casa/reforma/README.md").write_text('---\ntema: "Reforma"\n---\n# R\n', encoding="utf-8")
    (cerebro / "projetos/casa/reforma/orc.md").write_text("# orçamento\n", encoding="utf-8")
    (cerebro / "projetos/casa/reforma/sub/x.md").write_text("# x\n", encoding="utf-8")
    (cerebro / "projetos/familia").mkdir()
    (cerebro / "projetos/familia/README.md").write_text("# Família\n", encoding="utf-8")
    m.criar_tema("t", "Tema T", area="familia")
    lista = m.listar_temas()
    assert "projetos/casa/reforma/README.md" in lista and "Tema T" in lista
    assert "orc.md" not in lista and "sub/x.md" not in lista and "familia/README.md" not in lista
    for c in ("projetos/casa/reforma/orc.md", "projetos/casa/reforma/sub/x.md", "projetos/casa/reforma/README.md"):
        with pytest.raises(m.Recusa):
            m.mover_tema(c, area="pessoal")
    assert (cerebro / "projetos/casa/reforma/orc.md").exists()


def test_campo_so_no_frontmatter_e_sem_quebra_de_linha(cerebro):
    txt = '---\ntema: "T"\n---\n# T\npapel: corpo\n'
    novo = m._campo(txt, "papel", "CEO")
    assert 'papel: corpo' in novo and novo.index('papel: "CEO"') < novo.index("# T")
    novo = m._campo(txt, "cliente", "X\r\narea: pessoal")
    assert novo.count("\n") == txt.count("\n") + 1 and 'cliente: "X area: pessoal"' in novo


def test_criar_tema_escapa_tema_e_apelidos(cerebro):
    m.criar_tema("q", 'Tema "aspas"', ["a\\1"], area="casa")
    t = (cerebro / "projetos/casa/q.md").read_text()
    assert m._frontmatter(t)["tema"] == "Tema 'aspas'" and "[a\\1]" in t


def test_entrada_processar_nao_inteiro_e_ordem(cerebro):
    m.entrada_guardar("um")
    with pytest.raises(m.Recusa):
        m.entrada_processar(["abc"])
    assert m.entrada_ler().startswith("1.")
