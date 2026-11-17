"""config.yaml do Hermes para a etapa 3A, editando só as linhas necessárias (o resto fica igual) e conferindo com YAML:
(1) acrescenta o servidor MCP esper_brain (stdio, sem shell para o agente);
(2) tira do include do gabi_brain as ferramentas de projetos e família (agora no esper-brain).
Sem --gravar é simulação. Uso: python3 configurar_hermes.py ~/.hermes/config.yaml --python <venv>/bin/python --eb ~/esper-brain [--gravar]"""
import argparse, os, re, sys, yaml
TIRAR = {
    "projeto_criar", "projeto_ligar", "projeto_listar", "projeto_ver", "projeto_atualizar", "projeto_pessoa",
    "projeto_gasto", "projeto_fato", "projeto_fatos", "projeto_anexar", "anexo_recentes",
    "familia_listar", "familia_consultar", "familia_atualizar_contato", "familia_registrar_pessoa",
    "familia_registrar_pet", "familia_propor_documento",
}  # ficam no gabi_brain: familia_vencimentos e atividade_* (Linear)
ESPER = ["inicio", "ler", "buscar", "listar_temas", "criar_tema", "anotar", "acrescentar", "substituir", "gravar"]

def bloco_do(linhas, nome):
    ini = [i for i, l in enumerate(linhas) if re.match(rf"^\s*{nome}:\s*$", l)]
    if len(ini) != 1:
        return None, None, None
    i0 = ini[0]; ind = len(linhas[i0]) - len(linhas[i0].lstrip()); fim = len(linhas)
    for j in range(i0 + 1, len(linhas)):
        l = linhas[j]
        if l.strip() and not l.lstrip().startswith("#") and len(l) - len(l.lstrip()) <= ind:
            fim = j; break
    return i0, fim, ind

def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("config"); ap.add_argument("--python", required=True); ap.add_argument("--eb", required=True)
    ap.add_argument("--gravar", action="store_true")
    a = ap.parse_args(argv)
    linhas = open(a.config, encoding="utf-8").read().split("\n")
    i0, fim, ind = bloco_do(linhas, "gabi_brain")
    if i0 is None: sys.exit("esperava exatamente 1 gabi_brain: nada feito")
    novo, tiradas = [], []
    for j, l in enumerate(linhas):
        m = re.match(r"^\s*-\s*['\"]?(\w+)['\"]?\s*$", l)
        if i0 < j < fim and m and m.group(1) in TIRAR:
            tiradas.append(m.group(1)); continue
        novo.append(l)
    ja_tem = bloco_do(novo, "esper_brain")[0] is not None
    if not ja_tem:
        p = " " * ind
        bloco = [p + "esper_brain:", p + f"  command: {a.python}",
                 p + f"  args: [{os.path.join(a.eb, 'tools', 'esper_mcp.py')}, --raiz, {a.eb}]",
                 p + "  tools:", p + "    include:"] + [p + "    - " + t for t in ESPER]
        k = bloco_do(novo, "gabi_brain")[0]
        novo[k:k] = bloco
    texto = "\n".join(novo)
    s = yaml.safe_load(texto)["mcp_servers"]
    inc_b = (s["gabi_brain"].get("tools") or {}).get("include")
    if inc_b is None: sys.exit("gabi_brain sem include explícito: nada feito")
    e = s.get("esper_brain") or {}
    print("servidores:", sorted(s))
    print("tiradas do gabi_brain:", len(tiradas), sorted(tiradas))
    print("ainda no gabi_brain (deveria ser nenhuma):", sorted(set(inc_b) & TIRAR) or "nenhuma")
    print("ficam (família/atividades):", sorted(t for t in inc_b if t.startswith(("familia_", "atividade_"))))
    print("esper_brain:", "já existia" if ja_tem else "acrescentado", "| command:", e.get("command"), "| ferramentas:", len((e.get("tools") or {}).get("include") or []))
    if set(inc_b) & TIRAR or sorted((e.get("tools") or {}).get("include") or []) != sorted(ESPER):
        sys.exit("conferência falhou: nada gravado")
    if texto == "\n".join(linhas): print("nada a mudar"); return 0
    if a.gravar:
        open(a.config, "w", encoding="utf-8").write(texto); print("config.yaml gravado")
    else:
        print("simulação ok (nada gravado). Rode de novo com --gravar")
    return 0

if __name__ == "__main__":
    sys.exit(main())
