import pathlib, re, shutil, subprocess, sys, pytest

RAIZ_REPO = pathlib.Path(__file__).resolve().parents[1]
PAGINA = RAIZ_REPO / "tools/painel/index.html"
BASE = "https://srv-hermes.x.ts.net:8448"
LOGIN = "ricardo@github"


def html():
    return PAGINA.read_text(encoding="utf-8")


def test_get_raiz_devolve_pagina(tmp_path, monkeypatch):
    pytest.importorskip("httpx")
    from starlette.testclient import TestClient
    sys.path.insert(0, str(RAIZ_REPO / "tools"))
    import esper_mcp as m
    from painel.app import criar_app
    monkeypatch.setattr(m, "RAIZ", m.RAIZ)  # criar_app troca a global; o monkeypatch devolve
    cli = TestClient(criar_app(tmp_path, {LOGIN}, {BASE}), base_url=BASE)
    r = cli.get("/", headers={"Tailscale-User-Login": LOGIN})
    assert r.status_code == 200
    assert "<title>Temas</title>" in r.text
    assert r.headers["content-type"].startswith("text/html")
    assert r.headers["cache-control"] == "no-store"


def test_js_sem_erro_de_sintaxe(tmp_path):
    node = shutil.which("node") or ("/opt/node22/bin/node" if pathlib.Path("/opt/node22/bin/node").exists() else None)
    if not node:
        pytest.skip("sem node")
    scripts = re.findall(r"<script>(.*?)</script>", html(), re.S)
    assert len(scripts) == 1
    js = tmp_path / "painel.js"
    js.write_text(scripts[0], encoding="utf-8")
    r = subprocess.run([node, "--check", str(js)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr


def test_sem_recurso_externo_e_pequena():
    h = html()
    assert not re.search(r"https?://", h)
    assert not re.search(r"<(script|link|img|iframe)[^>]*\s(src|href)=(?!\"data:)", h, re.I)
    assert "@import" not in h
    assert len(h.encode("utf-8")) <= 60 * 1024


def test_nao_injeta_html():
    h = html()
    assert "innerHTML" not in h and "outerHTML" not in h and "insertAdjacentHTML" not in h
    assert "document.write" not in h


def test_post_manda_json_e_todas_as_rotas():
    h = html()
    assert '"Content-Type"] = "application/json"' in h
    for rota in ("/api/quadro", "/api/tema", "/api/mover", "/api/campos", "/api/anotar", "/api/criar"):
        assert rota in h
