---
name: pensar-junto
description: Ajuda o Ricardo a pensar uma decisão, dilema ou plano em passos curtos (contexto, clarear, pesar, fechar, registrar) usando o que o esper-brain sabe, e registra o resultado no tema. Use quando ele aceitar o "quer pensar junto?" ou pedir "me ajuda a pensar", "vamos pensar", "o que você acha de".
---
# Pensar junto

Uma pergunta por vez. Respostas curtas. Ferramentas do `esper_brain` (+ leitura do `gabi_brain` e do `gabi_finance` para contexto).

1. **Contexto (sem perguntar):** ache o tema (`listar_temas`, `ler`); veja pessoas, prazos, documentos ligados e, se for dinheiro, o `gabi_finance`.
2. **Clarear:** até 3 perguntas, uma por mensagem, só as que mudam a decisão (prazo real? quem decide? o que não pode dar errado?). Pare antes se já estiver claro.
3. **Pesar:** prós, contras e riscos em até 8 linhas, citando o que veio do cérebro (`tema`, `paperless:N`). Termine com a sua recomendação em uma linha, marcada como sugestão.
4. **Fechar:** proponha um próximo passo concreto com data e pergunte se fecha.
5. **Registrar:** o que ele confirmou → `anotar(tema, "Fatos e decisões", "AAAA-MM-DD: ...")` e `substituir` o `proximo_passo:`; o resto → `anotar(tema, "Ideias soltas" | "Perguntas em aberto", ...)`; prazo → também `pendencias.md`. Sem tema → `criar_tema` com a área certa (Trabalho: empresa e cliente). `gravar` e só então "registrado em <tema>".

Tudo que você deduziu e registrar termina com `(sugestão)`.

Nunca: tratar sugestão sua como decisão dele; inventar valor; deduzir sócio.
