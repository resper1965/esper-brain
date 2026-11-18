"""Reescreve no SOUL do Hermes as instruções antigas de projetos/família (ferramentas projeto_* e familia_* do
gabi_brain, que saíram na etapa 3A) para o esper-brain. Mexe só nessas linhas; confere antes de gravar.
Sem --gravar é simulação. Uso: python3 ajustar_soul_antigo.py [--soul ~/.hermes/SOUL.md] [--data AAAA-MM-DD-HHMM] [--gravar]"""
import argparse, os, re, shutil, sys

DADOS_ANTES = "Os dados vêm do gabi.brain (ferramentas MCP)."
DADOS_DEPOIS = "Os dados vêm do esper-brain (MCP `esper_brain`), do `gabi_finance` e do `gabi_brain`."
FAMILIA_EXC = ("- Exceção: pessoa, parentesco, apelido, nascimento, pet e contato da família você grava direto no esper-brain "
               "(ficha em `pessoal/familia/` ou `people/`: `anotar`, `acrescentar` ou `substituir`, depois `gravar`), só quando "
               "o Ricardo pedir ou contar. Número de documento nunca: fica no cofre, que só o Ricardo edita.")
PROJ_NA_EXC = ('tema ou projeto da vida ("vou começar X", "tenho um problema com X", fato, prazo, pessoa, gasto citado, print) '
               'vai para a skill `capturar` (tema novo e fato só depois do sim); "como está X?" vai para a skill `retomar`.')
PROJ_LINHAS = [
    '- Tema ou projeto da vida (carro, obra, sucessão, crise de família): "vou começar X" / "tenho um problema com X" / ideia, '
    'fato, prazo, pessoa ou gasto citado → skill `capturar`. Tema novo só depois do sim; fato só o que ele afirmou ou '
    'confirmou; print, áudio e transcrição são sugestão: proponha nas palavras dele e grave depois do sim.',
    '- "como está X?" / "quais temas tenho?" → skill `retomar` (ou `listar_temas`). "conclui / pausa / cancela X" → depois do '
    'sim, `substituir` o `estado` (ativo, parado ou concluído) e `gravar`. As atividades (to-dos do Linear) seguem com `atividade_*`.',
]
PROJ_INICIOS = ('- "vou começar o projeto X"', '- "como está o projeto X?"', '- "o mecânico disse', '- "gastei R$ 300',
                '- "conclui o projeto X"')
VALOR_DEPOIS = ("tema, projeto, pessoa e família → MCP `esper_brain` (`criar_tema`, `anotar`, `acrescentar`, `substituir`, "
                "depois `gravar`), sempre depois do sim dele (o fato, só do que ele afirmou ou confirmou).")
PESSOA_LINHA = ("- Pessoa, parentesco, apelido, nascimento, contato e pet → ficha no esper-brain (`buscar` o nome primeiro; "
                "ficha nova só depois do sim; `gravar` no fim). Documento: só o Ricardo, no cofre.")
PROIBIDAS = re.compile(r"\b(projeto_(criar|ligar|listar|ver|atualizar|pessoa|gasto|fato|fatos|anexar)|anexo_recentes|"
                       r"familia_(listar|consultar|atualizar_contato|registrar_pessoa|registrar_pet|propor_documento))\b")


def um(linhas, inicio):
    achou = [i for i, l in enumerate(linhas) if l.startswith(inicio)]
    if len(achou) != 1:
        sys.exit(f"esperava 1 linha começando com {inicio!r}, achei {len(achou)}: nada feito")
    return achou[0]


def ajustar(txt):
    if not PROIBIDAS.search(txt):
        return txt, ["nada a ajustar"]
    linhas, feito = txt.split("\n"), []
    i = um(linhas, "- " + DADOS_ANTES)
    linhas[i] = linhas[i].replace(DADOS_ANTES, DADOS_DEPOIS); feito.append(f"linha {i+1}: origem dos dados")
    i = um(linhas, "- Exceção: pessoa, parentesco")
    linhas[i] = FAMILIA_EXC; feito.append(f"linha {i+1}: exceção da família")
    i = um(linhas, "- Exceção (a pedido explícito")
    novo, n = re.subn(r'"vou começar o projeto X".*?vai para `projeto_fato`\.', PROJ_NA_EXC, linhas[i], count=1, flags=re.S)
    if n != 1: sys.exit("trecho de projetos na exceção não encontrado: nada feito")
    linhas[i] = novo; feito.append(f"linha {i+1}: projetos na exceção")
    idx = [um(linhas, p) for p in PROJ_INICIOS]
    for k in sorted(idx, reverse=True):
        del linhas[k]
    linhas[min(idx):min(idx)] = PROJ_LINHAS; feito.append(f"linhas {min(idx)+1}-{max(idx)+1}: 5 regras de projeto viram 2")
    i = um(linhas, "- Valor a receber →")
    novo, n = re.subn(r"projeto → `projeto_criar`.*?\(o fato, só do que ele afirmou ou confirmou\)\.", VALOR_DEPOIS, linhas[i], count=1)
    if n != 1: sys.exit("trecho de projeto na lista de gravações não encontrado: nada feito")
    linhas[i] = novo; feito.append(f"linha {i+1}: lista de gravações")
    i = um(linhas, "- Pessoa, parentesco, apelido, nascimento →")
    linhas[i] = PESSOA_LINHA; feito.append(f"linha {i+1}: pessoa e pet")
    out = "\n".join(linhas)
    resto = sorted({m.group(0) for m in PROIBIDAS.finditer(out)})
    if resto:
        sys.exit(f"ainda sobraram {resto}: nada feito")
    return out, feito


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--soul", default=os.path.expanduser("~/.hermes/SOUL.md"))
    ap.add_argument("--data", default="")
    ap.add_argument("--gravar", action="store_true")
    a = ap.parse_args(argv)
    txt = open(a.soul, encoding="utf-8").read()
    novo, feito = ajustar(txt)
    for f in feito: print(f)
    if novo == txt: return 0
    print("sobraram ferramentas antigas: nenhuma")
    if not a.gravar:
        print("simulação ok (nada gravado). Rode de novo com --gravar"); return 0
    if a.data:
        bak = f"{a.soul}.bak-antes-ajuste-{a.data}"
        if not os.path.exists(bak): shutil.copy2(a.soul, bak); print("backup:", bak)
    open(a.soul, "w", encoding="utf-8").write(novo); print("SOUL gravado")
    return 0


if __name__ == "__main__":
    sys.exit(main())
