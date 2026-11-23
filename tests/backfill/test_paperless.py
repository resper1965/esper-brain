from tools.backfill import paperless

PAGINAS = {
    "http://p/api/correspondents/?page_size=100": {"results": [{"id": 1, "name": "Acme"}, {"id": 2, "name": "Cartório"}], "next": None},
    "http://p/api/documents/?page_size=100&created__date__gte=2026-08-25&fields=id,title,created,correspondent":
        {"results": [{"id": 10, "title": "Contrato Acme", "created": "2026-11-01", "correspondent": 1},
                     {"id": 11, "title": "Aditivo Acme", "created": "2026-11-02", "correspondent": 1},
                     {"id": 12, "title": "Sem dono", "created": "2026-11-03", "correspondent": None}],
         "next": None},
}

def falso(url, token):
    assert token == "tk"
    return PAGINAS[url]

def test_correspondentes_agrupa_titulos():
    r = paperless.correspondentes("http://p/", "tk", "2026-08-25", http=falso)
    assert r == [{"nome": "Acme", "docs": [{"id": 10, "titulo": "Contrato Acme", "data": "2026-11-01"},
                                           {"id": 11, "titulo": "Aditivo Acme", "data": "2026-11-02"}]}]

def test_pagina_dentro_da_base_junta_paginas():
    chamadas = []
    paginas = {
        "http://p/api/correspondents/?page_size=100": {"results": [{"id": 1, "name": "Acme"}],
                                                       "next": "http://p/api/correspondents/?page=2&page_size=100"},
        "http://p/api/correspondents/?page=2&page_size=100": {"results": [{"id": 2, "name": "Cartório"}], "next": None},
        "http://p/api/documents/?page_size=100&created__date__gte=2026-08-25&fields=id,title,created,correspondent":
            {"results": [{"id": 10, "title": "Contrato Acme", "created": "2026-11-01", "correspondent": 1}], "next": None},
    }
    def fake(url, token):
        chamadas.append(url)
        return paginas[url]
    r = paperless.correspondentes("http://p", "tk", "2026-08-25", http=fake)
    assert r == [{"nome": "Acme", "docs": [{"id": 10, "titulo": "Contrato Acme", "data": "2026-11-01"}]}]
    assert "http://p/api/correspondents/?page=2&page_size=100" in chamadas

def test_next_fora_da_base_levanta_e_nao_chama():
    chamadas = []
    fora = "http://outro/api/documents/?page=2"
    def fake(url, token):
        chamadas.append(url)
        return {"results": [], "next": fora}
    import pytest
    with pytest.raises(ValueError, match="fora da base configurada"):
        paperless.correspondentes("http://p", "tk", "2026-08-25", http=fake)
    assert fora not in chamadas

def test_get_envia_so_get_com_token(monkeypatch):
    capturado = {}
    class Resposta:
        def __enter__(self):
            return self
        def __exit__(self, *a):
            return False
        def read(self):
            return b'{"results": []}'
    def falso_urlopen(pedido, timeout=None):
        capturado["pedido"] = pedido
        return Resposta()
    monkeypatch.setattr(paperless.urllib.request, "urlopen", falso_urlopen)
    assert paperless._get("http://p/api/x", "tk") == {"results": []}
    assert capturado["pedido"].get_method() == "GET"
    assert capturado["pedido"].get_header("Authorization") == "Token tk"
