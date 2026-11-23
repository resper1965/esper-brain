"""Paperless só leitura: correspondentes e títulos de documentos na janela. Nunca lê o texto do documento."""
import json
import urllib.request


def _get(url: str, token: str) -> dict:
    pedido = urllib.request.Request(url, headers={"Authorization": f"Token {token}", "Accept": "application/json"})
    with urllib.request.urlopen(pedido, timeout=30) as r:
        return json.load(r)


def _todas(base, url, token, http):
    while url:
        pagina = http(url, token)
        yield from pagina.get("results", [])
        url = pagina.get("next")
        if url and not url.startswith(base + "/"):
            raise ValueError("paginação do Paperless fora da base configurada")


def correspondentes(base: str, token: str, desde: str, http=None) -> list[dict]:
    http = http or _get
    base = base.rstrip("/")
    nomes = {c["id"]: c["name"] for c in _todas(base, f"{base}/api/correspondents/?page_size=100", token, http)}
    url = f"{base}/api/documents/?page_size=100&created__date__gte={desde}&fields=id,title,created,correspondent"
    grupos: dict[str, list] = {}
    for d in _todas(base, url, token, http):
        if d.get("correspondent") in nomes:
            grupos.setdefault(nomes[d["correspondent"]], []).append(
                {"id": d["id"], "titulo": d.get("title", ""), "data": str(d.get("created", ""))[:10]})
    return sorted(({"nome": n, "docs": docs} for n, docs in grupos.items()), key=lambda g: -len(g["docs"]))
