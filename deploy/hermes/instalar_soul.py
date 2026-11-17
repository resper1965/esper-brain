"""Acrescenta (ou atualiza) a seção "Segundo cérebro" no SOUL do Hermes, entre marcadores. Idempotente.
Uso (como o usuário do Hermes): python3 instalar_soul.py [--soul ~/.hermes/SOUL.md] [--data AAAA-MM-DD-HHMM]"""
import argparse, os, shutil, sys
INI, FIM = "<!-- esper-brain:inicio -->", "<!-- esper-brain:fim -->"
BLOCO = f"""{INI}
## Segundo cérebro (esper-brain)
- O cérebro do Ricardo é o repositório esper-brain (markdown), acessado só pelo MCP `esper_brain`. No começo de toda conversa nova chame `mcp__esper_brain__inicio` e siga o AGENTS.md que vem nele.
- Temas e projetos da vida, pessoas, família, casa, ficha cadastral das empresas e decisões estão lá. Use `buscar` e `ler` antes de responder; não invente.
- Anotar ideia/fato/prazo de um tema: skill `capturar`. Retomar um tema: skill `retomar`. Guardar o que importou da conversa: skill `salvar-sessao`.
- Só diga "anotado" depois que `gravar` responder `gravado:`. Se não, diga que não gravou e por quê.
- Dinheiro: MCP `gabi_finance`. Documentos: Paperless. Agenda, e-mail, atividades (Linear) e avisos não financeiros: `gabi_brain`, como antes.
- Projetos e família não estão mais no `gabi_brain`: estão no esper-brain.
{FIM}"""
def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--soul", default=os.path.expanduser("~/.hermes/SOUL.md"))
    ap.add_argument("--data", default="")
    a = ap.parse_args(argv)
    txt = open(a.soul, encoding="utf-8").read()
    if INI in txt and FIM in txt:
        ini = txt.index(INI); fim = txt.index(FIM) + len(FIM)
        novo = txt[:ini] + BLOCO + txt[fim:]
    else:
        novo = txt.rstrip("\n") + "\n\n" + BLOCO + "\n"
    if novo == txt:
        print("SOUL já tem a seção atual: nada a mudar"); return 0
    if a.data:
        bak = f"{a.soul}.bak-antes-esper-brain-{a.data}"
        if not os.path.exists(bak):
            shutil.copy2(a.soul, bak); print("backup:", bak)
    open(a.soul, "w", encoding="utf-8").write(novo)
    print("SOUL: seção 'Segundo cérebro (esper-brain)' gravada. Falta: systemctl restart hermes-gateway e /new")
    return 0
if __name__ == "__main__":
    sys.exit(main())
