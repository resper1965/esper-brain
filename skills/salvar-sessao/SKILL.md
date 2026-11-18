---
name: salvar-sessao
description: Salva o que importou de uma conversa no esper-brain (diário, pendências, decisões, pessoas, temas). Use quando o Ricardo disser "salva a sessão", "guarda isso", "registra a conversa", antes de um /new que ele anunciar, ou quando a conversa trouxe decisões ou pendências novas e ele concordar em salvar.
---
# Salvar sessão

Ferramentas do MCP `esper_brain`.

1. Separe só o durável da conversa: **decisões do Ricardo** (não as suas sugestões), **pendências** (com prazo, se houver), **fatos novos** sobre pessoas que já têm ficha, **avanços em temas**. Nada disso → "nada para salvar" e pare.
2. Diário: `acrescentar("diario/AAAA/MM-DD.md", ...)` com `# AAAA-MM-DD` se o arquivo for novo (confira com `ler`; se não existir, comece com o título) e uma seção `## HH:MM · <canal>` de 3 a 8 linhas.
3. Propague:
   - Decisões → `acrescentar("decisoes.md", "- AAAA-MM-DD: <decisão> (contexto: <uma linha>)")`.
   - Pendências → `acrescentar("pendencias.md", "- [ ] <o quê> · vence AAAA-MM-DD · origem <origem>")` (sem prazo: omita o "vence").
   - Pessoa com ficha (`buscar` o nome em `people/` e `pessoal/familia/`) → `anotar(ficha, "Histórico", "AAAA-MM-DD: <fato>")`. Se a ficha não tiver `## Histórico`, use `acrescentar` com `## Histórico` e a linha.
   - **Pessoa nova** → não crie ficha; pergunte "crio ficha para <nome>?".
   - Tema → `anotar(tema, "Histórico", ...)` e, se mudou, `substituir` o "Onde estou".
4. `gravar("sessão AAAA-MM-DD HH:MM: <resumo>")` uma vez no fim.
5. Só depois de `gravado:` responda o resumo (uma linha por arquivo). Senão: `não gravei: <motivo>`.

Mesmas proibições do AGENTS.md.
