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
    m.criar_tema("trocar-de-carro", "Trocar de carro", ["carro", "suv"])
    assert "Trocar de carro" in m.listar_temas() and "carro, suv" in m.listar_temas()
    m.anotar("projetos/trocar-de-carro.md", "Ideias soltas", "2026-11-17: ver híbrido")
    m.anotar("projetos/trocar-de-carro.md", "ideias soltas", "2026-11-18: mais nova")
    t = (cerebro / "projetos/trocar-de-carro.md").read_text()
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
        m.criar_tema("Tem Acento", "x")
    (cerebro / "fora").mkdir(); (cerebro / "projetos/link.md").symlink_to("/etc/hostname")
    with pytest.raises(m.Recusa):
        m.ler("projetos/link.md")

def test_diario_e_substituir(cerebro):
    m.acrescentar("diario/2026/11-17.md", "# 2026-11-17\n\n## 19:30 · telegram\n- decidi X")
    m.acrescentar("pendencias.md", "- 2026-11-20 [teste]: fazer Y")
    m.criar_tema("t", "T")
    m.substituir("projetos/t.md", 'proximo_passo: ""', 'proximo_passo: "ligar"')
    with pytest.raises(m.Recusa):
        m.substituir("projetos/t.md", "não existe", "x")
    out = m.gravar("sessão")
    assert out.startswith("gravado:")
    log = subprocess.run(["git", "-C", str(cerebro), "show", "--stat", "HEAD"], capture_output=True, text=True).stdout
    assert "diario/2026/11-17.md" in log and "pendencias.md" in log and "projetos/t.md" in log
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
