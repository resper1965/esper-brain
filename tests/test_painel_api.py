import subprocess, sys, shutil, pathlib, pytest

pytest.importorskip("httpx")
from starlette.testclient import TestClient

RAIZ_REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ_REPO / "tools"))
import esper_mcp as m
from painel.app import criar_app

BASE = "https://srv-hermes.x.ts.net:8448"
LOGIN = "ricardo@github"
H = {"Tailscale-User-Login": LOGIN}
HP = {**H, "Origin": BASE}


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
    (r / "entrada.md").write_text("# Entrada\n\n- 2026-11-20 10:00 · a\n- 2026-11-21 10:00 · b\n", encoding="utf-8")
    g("add", "-A"); g("commit", "-qm", "init"); g("push", "-qu", "origin", "main")
    monkeypatch.setattr(m, "RAIZ", r.resolve())
    return r


@pytest.fixture
def cli(cerebro):
    return TestClient(criar_app(cerebro.resolve(), {LOGIN}, {BASE}), base_url=BASE)


def remoto_log(cerebro):
    return subprocess.run(["git", "--git-dir", str(cerebro.parent / "remoto.git"), "log", "--format=%s", "main"],
                          capture_output=True, text=True, check=True).stdout


def arquivos_remoto(cerebro):
    return subprocess.run(["git", "--git-dir", str(cerebro.parent / "remoto.git"), "ls-tree", "-r", "--name-only",
                           "main"], capture_output=True, text=True, check=True).stdout.split()


def test_sem_cabecalho_e_login_fora(cli):
    r = cli.get("/api/quadro")
    assert r.status_code == 403 and r.json() == {"erro": "proibido"}
    r = cli.get("/api/quadro", headers={"Tailscale-User-Login": "outro@x"})
    assert r.status_code == 403 and r.json() == {"erro": "proibido"}
    assert cli.get("/", headers={"Tailscale-User-Login": "outro@x"}).status_code == 403


def test_post_sem_origin_ou_json(cli, cerebro):
    m.criar_tema("a", "A", area="casa")
    corpo = {"caminho": "projetos/casa/a.md", "estado": "parado"}
    r = cli.post("/api/campos", json=corpo, headers=H)
    assert r.status_code == 403 and r.json() == {"erro": "origem"}
    r = cli.post("/api/campos", json=corpo, headers={**H, "Origin": "https://mal.example"})
    assert r.status_code == 403 and r.json() == {"erro": "origem"}
    r = cli.post("/api/campos", content="estado=parado", headers={**HP, "Content-Type": "text/plain"})
    assert r.status_code == 403 and r.json() == {"erro": "origem"}


def test_quadro(cli, cerebro):
    m.criar_tema("casa-a", "Casa A", area="casa")
    m.criar_tema("venda", "Venda", area="trabalho", empresa="ness", marca="trustness", cliente="ACME")
    m.criar_tema("pki", "PKI", area="trabalho", empresa="ionic", frente="produto")
    m.criar_tema("solto", "Solto", area="trabalho")
    m.criar_tema("imovel", "Imóvel", area="patrimonio", holding="fakiha")
    m.criar_tema("prazo-longe", "Prazo longe", area="casa")
    (cerebro / "projetos/sem-area.md").write_text("---\ntema: \"Sem área\"\n---\n# x\n", encoding="utf-8")
    t = cerebro / "projetos/casa/prazo-longe.md"
    t.write_text(t.read_text().replace("prazo:                   # AAAA-MM-DD", "prazo: 2099-01-01"), encoding="utf-8")
    t = cerebro / "projetos/casa/casa-a.md"
    t.write_text(t.read_text().replace("prazo:                   # AAAA-MM-DD", "prazo: 2020-01-01"), encoding="utf-8")
    r = cli.get("/api/quadro", headers=H)
    assert r.status_code == 200
    q = r.json()
    assert [c["id"] for c in q["colunas"]] == ["familia", "casa", "saude", "pessoal", "patrimonio", "ness", "ionic",
                                               "bekaa", "trabalho"]
    assert q["colunas"][-1]["rotulo"] == "Trabalho (sem empresa)" and q["colunas"][4]["rotulo"] == "Patrimônio"
    assert q["entrada"] == 2 and len(q["hoje"]) == 10
    assert q["frentes"] == list(m.FRENTES_IONIC) and q["marcas"] == list(m.MARCAS["ness"])
    assert q["holdings"] == list(m.HOLDINGS)
    col = {c["id"]: c["cartoes"] for c in q["colunas"]}
    assert [c["tema"] for c in col["casa"]] == ["Casa A", "Prazo longe"]
    assert col["ness"][0]["marca"] == "trustness" and col["ness"][0]["cliente"] == "ACME"
    assert col["ionic"][0]["frente"] == "produto"
    assert col["trabalho"][0]["tema"] == "Solto"
    assert col["patrimonio"][0]["holding"] == "fakiha"
    assert [c["tema"] for c in col["pessoal"]] == ["Sem área"]
    c = col["casa"][0]
    assert set(c) == {"caminho", "tema", "estado", "proximo_passo", "prazo", "cliente", "marca", "frente", "holding",
                      "mudanca", "parado_dias"}
    assert c["caminho"] == "projetos/casa/casa-a.md" and c["prazo"] == "2020-01-01" and c["estado"] == "ativo"
    assert isinstance(c["parado_dias"], int)


def test_tema_e_cofre(cli, cerebro):
    m.criar_tema("a", "A", area="casa")
    r = cli.get("/api/tema", params={"caminho": "projetos/casa/a.md"}, headers=H)
    assert r.status_code == 200 and r.json()["caminho"] == "projetos/casa/a.md" and "# A" in r.json()["texto"]
    for c in ("pessoal/cofre/doc.md", "../x.md", "projetos/_modelo.md", "hot.md", "projetos/casa/nao.md"):
        r = cli.get("/api/tema", params={"caminho": c}, headers=H)
        assert r.status_code == 400 and "erro" in r.json()
    r = cli.post("/api/campos", json={"caminho": "pessoal/cofre/doc.md", "estado": "parado"}, headers=HP)
    assert r.status_code == 400
    r = cli.post("/api/anotar", json={"caminho": "pessoal/cofre/doc.md", "secao": "Prazos", "texto": "x"}, headers=HP)
    assert r.status_code == 400


def test_mover(cli, cerebro):
    m.criar_tema("pki", "PKI", area="trabalho", empresa="ness")
    assert m.gravar("init").startswith("gravado:")
    r = cli.post("/api/mover", json={"caminho": "projetos/trabalho/ness/pki.md", "coluna": "ionic"}, headers=HP)
    assert r.status_code == 400 and "frente" in r.json()["erro"]
    r = cli.post("/api/mover", json={"caminho": "projetos/trabalho/ness/pki.md", "coluna": "ness"}, headers=HP)
    assert r.status_code == 200 and r.json()["mudou"] is False
    r = cli.post("/api/mover", json={"caminho": "projetos/trabalho/ness/pki.md", "coluna": "ionic",
                                     "frente": "produto"}, headers=HP)
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["mudou"] is True and j["caminho"] == "projetos/trabalho/ionic/produto/pki.md"
    assert j["cartao"]["frente"] == "produto"
    assert "painel: move PKI" in remoto_log(cerebro)
    arqs = arquivos_remoto(cerebro)
    assert "projetos/trabalho/ionic/produto/pki.md" in arqs and "projetos/trabalho/ness/pki.md" not in arqs
    r = cli.post("/api/mover", json={"caminho": "projetos/trabalho/ionic/produto/pki.md", "coluna": "xyz"}, headers=HP)
    assert r.status_code == 400
    r = cli.post("/api/mover", json={"caminho": "projetos/trabalho/ionic/produto/pki.md", "coluna": "patrimonio",
                                     "holding": "baalbeck"}, headers=HP)
    assert r.status_code == 200 and r.json()["caminho"] == "projetos/patrimonio/baalbeck/pki.md"


def test_campos(cli, cerebro):
    m.criar_tema("a", "A", area="casa")
    m.criar_tema("v", "V", area="trabalho", empresa="ness")
    assert m.gravar("init").startswith("gravado:")
    c = "projetos/casa/a.md"
    for corpo in ({"prazo": "31/03/2027"}, {"prazo": "2027-02-30"}, {"cliente": "ACME"}, {"marca": "trustness"},
                  {"estado": "feito"}, {"proximo_passo": "a\nb"}, {"proximo_passo": "x" * 301}, {}):
        r = cli.post("/api/campos", json={"caminho": c, **corpo}, headers=HP)
        assert r.status_code == 400, corpo
    r = cli.post("/api/campos", json={"caminho": c, "estado": "parado", "proximo_passo": "ligar \"já\"",
                                      "prazo": "2027-03-31"}, headers=HP)
    assert r.status_code == 200, r.text
    t = (cerebro / c).read_text()
    assert "\nprazo: 2027-03-31\n" in t and 'estado: "parado"' in t and "ligar 'já'" in t
    assert r.json()["cartao"]["prazo"] == "2027-03-31" and r.json()["cartao"]["estado"] == "parado"
    assert "painel: A" in remoto_log(cerebro)
    r = cli.post("/api/campos", json={"caminho": c, "prazo": ""}, headers=HP)
    assert r.status_code == 200 and "\nprazo:\n" in (cerebro / c).read_text()
    r = cli.post("/api/campos", json={"caminho": "projetos/trabalho/ness/v.md", "marca": "forense.io",
                                      "cliente": "ACME"}, headers=HP)
    assert r.status_code == 200
    fm = m._frontmatter((cerebro / "projetos/trabalho/ness/v.md").read_text())
    assert fm["marca"] == "forense.io" and fm["cliente"] == "ACME"
    r = cli.post("/api/campos", json={"caminho": "projetos/trabalho/ness/v.md", "marca": "outra"}, headers=HP)
    assert r.status_code == 400


def test_anotar(cli, cerebro):
    m.criar_tema("a", "A", area="casa")
    assert m.gravar("init").startswith("gravado:")
    c = "projetos/casa/a.md"
    r = cli.post("/api/anotar", json={"caminho": c, "secao": "Histórico", "texto": "x"}, headers=HP)
    assert r.status_code == 400
    r = cli.post("/api/anotar", json={"caminho": c, "secao": "Ideias soltas", "texto": "ver híbrido"}, headers=HP)
    assert r.status_code == 200, r.text
    hoje = m._agora().date().isoformat()
    assert f"## Ideias soltas\n- {hoje}: ver híbrido" in (cerebro / c).read_text()
    assert "painel: anota A" in remoto_log(cerebro)


def test_criar_com_colisao(cli, cerebro):
    m.criar_tema("trocar-de-carro", "Trocar de carro", area="casa")
    assert m.gravar("init").startswith("gravado:")
    r = cli.post("/api/criar", json={"coluna": "saude", "tema": "Trocar de Carro!"}, headers=HP)
    assert r.status_code == 200, r.text
    assert r.json()["cartao"]["caminho"] == "projetos/saude/trocar-de-carro-2.md"
    r = cli.post("/api/criar", json={"coluna": "familia", "tema": "Trocar de carro"}, headers=HP)
    assert r.json()["cartao"]["caminho"] == "projetos/familia/trocar-de-carro-3.md"
    r = cli.post("/api/criar", json={"coluna": "ionic", "tema": "Ação nº 1: Ótima", "frente": "pessoas",
                                     "cliente": "X"}, headers=HP)
    assert r.status_code == 200, r.text
    card = r.json()["cartao"]
    assert card["caminho"] == "projetos/trabalho/ionic/pessoas/acao-n-1-otima.md"
    assert card["tema"] == "Ação nº 1: Ótima" and card["cliente"] == "X" and card["frente"] == "pessoas"
    assert "projetos/trabalho/ionic/pessoas/acao-n-1-otima.md" in arquivos_remoto(cerebro)
    assert "painel: cria Ação nº 1: Ótima" in remoto_log(cerebro)
    r = cli.post("/api/criar", json={"coluna": "casa", "tema": "X", "cliente": "Y"}, headers=HP)
    assert r.status_code == 400
    r = cli.post("/api/criar", json={"coluna": "casa", "tema": "  "}, headers=HP)
    assert r.status_code == 400
    r = cli.post("/api/criar", json={"coluna": "casa", "tema": "a" * 200}, headers=HP)
    assert r.status_code == 200 and len(pathlib.Path(r.json()["cartao"]["caminho"]).stem) <= 60


def test_gravar_falha_502(cli, cerebro):
    m.criar_tema("a", "A", area="casa")
    assert m.gravar("init").startswith("gravado:")
    subprocess.run(["git", "-C", str(cerebro), "remote", "set-url", "origin", str(cerebro.parent / "nao.git")],
                   check=True)
    r = cli.post("/api/campos", json={"caminho": "projetos/casa/a.md", "estado": "parado"}, headers=HP)
    assert r.status_code == 502 and r.json()["erro"]


def head(cerebro):
    return subprocess.run(["git", "-C", str(cerebro), "rev-parse", "HEAD"], capture_output=True, text=True).stdout


def test_403_nao_muda_arquivo(cli, cerebro):
    m.criar_tema("a", "A", area="casa")
    antes = (cerebro / "projetos/casa/a.md").read_text()
    for h in ({}, H, {**H, "Origin": "https://mal.example"}):
        r = cli.post("/api/campos", json={"caminho": "projetos/casa/a.md", "estado": "parado"}, headers=h)
        assert r.status_code == 403
    assert (cerebro / "projetos/casa/a.md").read_text() == antes


def test_campos_sem_mudanca_nao_grava(cli, cerebro):
    m.criar_tema("a", "A", area="casa")
    assert m.gravar("init").startswith("gravado:")
    corpo = {"caminho": "projetos/casa/a.md", "estado": "parado", "proximo_passo": "x", "prazo": "2027-01-01"}
    r = cli.post("/api/campos", json=corpo, headers=HP)
    assert r.status_code == 200 and r.json()["mudou"] is True
    h = head(cerebro)
    r = cli.post("/api/campos", json=corpo, headers=HP)
    assert r.status_code == 200, r.text
    assert r.json()["mudou"] is False and r.json()["cartao"]["estado"] == "parado"
    assert head(cerebro) == h


def test_campos_cliente_vazio_fora_de_trabalho_nao_entra(cli, cerebro):
    (cerebro / "projetos/casa").mkdir(parents=True)
    f = cerebro / "projetos/casa/b.md"
    f.write_text('---\ntema: "B"\narea: casa\nestado: ativo\n---\n# B\n', encoding="utf-8")
    assert m.gravar("init").startswith("gravado:")
    r = cli.post("/api/campos", json={"caminho": "projetos/casa/b.md", "cliente": "", "marca": "",
                                      "estado": "parado"}, headers=HP)
    assert r.status_code == 200, r.text
    t = f.read_text()
    assert "cliente" not in t and "marca" not in t and 'estado: "parado"' in t


def test_prazo_sem_frontmatter_400(cli, cerebro):
    (cerebro / "projetos/sem.md").write_text("# sem frontmatter\n", encoding="utf-8")
    r = cli.post("/api/campos", json={"caminho": "projetos/sem.md", "prazo": "2027-01-01"}, headers=HP)
    assert r.status_code == 400 and "frontmatter" in r.json()["erro"]


def test_quadro_tema_em_pasta_e_ordem_sem_prazo(cli, cerebro):
    import os
    (cerebro / "projetos/casa/reforma").mkdir(parents=True)
    (cerebro / "projetos/casa/reforma/README.md").write_text("---\narea: casa\n---\n# r\n", encoding="utf-8")
    m.criar_tema("velho", "Velho", area="casa")
    m.criar_tema("novo", "Novo", area="casa")
    for nome, ts in (("velho.md", 1_600_000_000), ("novo.md", 1_700_000_000),
                     ("reforma/README.md", 1_650_000_000)):
        os.utime(cerebro / "projetos/casa" / nome, (ts, ts))
    col = {c["id"]: c["cartoes"] for c in cli.get("/api/quadro", headers=H).json()["colunas"]}
    assert [c["tema"] for c in col["casa"]] == ["Novo", "reforma", "Velho"]


def test_socket_privado(tmp_path):
    from painel.app import _abrir_socket
    p = tmp_path / "s.sock"
    p.write_text("velho")
    s = _abrir_socket(str(p))
    try:
        assert (p.stat().st_mode & 0o777) == 0o600
    finally:
        s.close()


def test_cabecalhos_contra_embutir(cli):
    r = cli.get("/api/quadro", headers=H)
    assert r.headers["x-frame-options"] == "DENY" and "frame-ancestors 'none'" in r.headers["content-security-policy"]


def test_pedidos_do_computador(cli, cerebro):
    import esper_mcp as em
    em.pedido_pc_criar("baixar o recibo da Vivo")
    assert cli.get("/api/pedidos").status_code == 403
    p = cli.get("/api/pedidos", headers=H).json()["pedidos"]
    assert [(x["numero"], x["tarefa"]) for x in p] == [(1, "baixar o recibo da Vivo")]
    assert cli.post("/api/pedidos/feito", json={"numero": 1, "resultado": "ok"}, headers=H).status_code == 403  # sem Origin
    r = cli.post("/api/pedidos/feito", json={"numero": 1, "resultado": "1 PDF no Paperless"}, headers=HP)
    assert r.status_code == 200 and r.json()["gravado"].startswith("gravado:")
    assert cli.get("/api/pedidos", headers=H).json()["pedidos"] == []
    assert cli.post("/api/pedidos/feito", json={"numero": 1, "resultado": "de novo"}, headers=HP).status_code == 400
    assert cli.post("/api/pedidos/feito", json={"numero": "1", "resultado": "x"}, headers=HP).status_code == 400
