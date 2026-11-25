"""Liga o ness.know (normas, leis e frameworks da ness.) ao Hermes como servidor MCP remoto, só leitura.
Acrescenta mcp_servers.ness_know ao config.yaml sem mexer no resto; a chave fica em ~/.hermes/.env (NESS_KNOW_TOKEN).
Idempotente. Sem --gravar é simulação. Uso: python3 ligar_ness_know.py ~/.hermes/config.yaml [--gravar]"""
import argparse, os, sys, yaml
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from configurar_hermes import bloco_do

URL = "https://know.ness.com.br/mcp"
FERRAMENTAS = ["listar_pacotes", "buscar_conhecimento", "correlacionar", "cobertura", "detalhar_controle", "obter_skill"]


def bloco(ind):
    p = " " * ind
    return [p + "ness_know:", p + f"  url: {URL}", p + "  headers:",
            p + "    Authorization: Bearer ${NESS_KNOW_TOKEN}", p + "  timeout: 60", p + "  tools:",
            p + "    include:"] + [p + "    - " + t for t in FERRAMENTAS] + [p + "    resources: false", p + "    prompts: false"]


def aplicar(texto):
    linhas = texto.split("\n")
    m0, mfim, _ = bloco_do(linhas, "mcp_servers")
    if m0 is None:
        raise SystemExit("esperava exatamente 1 mcp_servers: nada feito")
    if bloco_do(linhas, "ness_know")[0] is not None:
        return texto, False
    filhos = [l for l in linhas[m0 + 1:mfim] if l.strip() and not l.lstrip().startswith("#")]
    ind = len(filhos[0]) - len(filhos[0].lstrip()) if filhos else 2
    fim = mfim
    while fim > m0 + 1 and not linhas[fim - 1].strip():
        fim -= 1
    novo = linhas[:fim] + bloco(ind) + linhas[fim:]
    return "\n".join(novo), True


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("config"); ap.add_argument("--gravar", action="store_true")
    a = ap.parse_args(argv)
    texto = open(a.config, encoding="utf-8").read()
    novo, mudou = aplicar(texto)
    s = yaml.safe_load(novo)["mcp_servers"]
    nk = s.get("ness_know") or {}
    inc = (nk.get("tools") or {}).get("include") or []
    print("servidores:", sorted(s))
    print("ness_know:", "acrescentado" if mudou else "já existia", "| url:", nk.get("url"), "| ferramentas:", len(inc))
    if nk.get("url") != URL or sorted(inc) != sorted(FERRAMENTAS):
        sys.exit("conferência falhou: nada gravado")
    if not mudou:
        print("nada a mudar"); return 0
    if a.gravar:
        open(a.config, "w", encoding="utf-8").write(novo); print("config.yaml gravado")
    else:
        print("simulação ok (nada gravado). Rode de novo com --gravar")
    return 0


if __name__ == "__main__":
    sys.exit(main())
