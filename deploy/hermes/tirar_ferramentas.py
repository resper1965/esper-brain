"""Tira do include do servidor gabi_brain (config.yaml do Hermes) as ferramentas de projetos e família, que passam a viver no esper-brain.
Edita só as linhas do include (o resto do arquivo fica igual), confere com YAML antes de gravar. Sem --gravar é simulação.
Uso: python3 tirar_ferramentas.py ~/.hermes/config.yaml [--gravar]"""
import re, sys, yaml
TIRAR = {
    "projeto_criar", "projeto_ligar", "projeto_listar", "projeto_ver", "projeto_atualizar", "projeto_pessoa",
    "projeto_gasto", "projeto_fato", "projeto_fatos", "projeto_anexar", "anexo_recentes",
    "familia_listar", "familia_consultar", "familia_atualizar_contato", "familia_registrar_pessoa",
    "familia_registrar_pet", "familia_propor_documento",
}
# fica no gabi_brain: familia_vencimentos (vencimentos de documentos), atividade_* (Linear)
def main(argv):
    cfg, gravar = argv[0], "--gravar" in argv
    linhas = open(cfg, encoding="utf-8").read().split("\n")
    ini = [i for i, l in enumerate(linhas) if re.match(r"^\s*gabi_brain:\s*$", l)]
    if len(ini) != 1: sys.exit(f"esperava 1 gabi_brain, achei {len(ini)}: nada feito")
    i0 = ini[0]; ind = len(linhas[i0]) - len(linhas[i0].lstrip()); fim = len(linhas)
    for j in range(i0 + 1, len(linhas)):
        l = linhas[j]
        if l.strip() and not l.lstrip().startswith("#") and len(l) - len(l.lstrip()) <= ind:
            fim = j; break
    novo, tiradas = [], []
    for j, l in enumerate(linhas):
        m = re.match(r"^\s*-\s*['\"]?(\w+)['\"]?\s*$", l)
        if i0 < j < fim and m and m.group(1) in TIRAR:
            tiradas.append(m.group(1)); continue
        novo.append(l)
    texto = "\n".join(novo)
    inc = (yaml.safe_load(texto)["mcp_servers"]["gabi_brain"].get("tools") or {}).get("include")
    if inc is None: sys.exit("gabi_brain sem include explícito: nada feito")
    print("tiradas:", len(tiradas), sorted(tiradas))
    print("ainda no gabi_brain (deveria ser nenhuma):", sorted(set(inc) & TIRAR) or "nenhuma")
    print("ficam (família/atividades):", sorted(t for t in inc if t.startswith(("familia_", "atividade_"))))
    if set(inc) & TIRAR: sys.exit("conferência falhou: nada gravado")
    if not tiradas: print("nada a tirar"); return 0
    if gravar:
        open(cfg, "w", encoding="utf-8").write(texto); print("config.yaml gravado")
    else:
        print("simulação ok (nada gravado). Rode de novo com --gravar")
    return 0
if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
