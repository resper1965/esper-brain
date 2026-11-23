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

def test_metodo_so_get():
    import inspect
    assert "POST" not in inspect.getsource(paperless) and "PATCH" not in inspect.getsource(paperless)
