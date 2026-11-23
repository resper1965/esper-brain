# Etapa 4 — Resultado do teste do GBrain (2026-11-23)

**Decisão:** GBrain **não adotado agora**. Revalidar quando o cérebro crescer (sugestão: ~2026-12-23, depois de um mês de digestão e do backfill).

## Como rodou
- GBrain 0.60.765.0 (Bun 1.4.5), `pglite`, **sem embeddings** (só palavra-chave), lendo um clone do esper-brain sem `pessoal/cofre/` e sem `docs/ tools/ tests/ skills/ deploy/` (a primeira rodada indexou `docs/` e os specs com as perguntas e o gabarito dominaram o top-3; foi descartada).
- Base de comparação: a camada markdown imita o `buscar` da Gabi (`tools/esper_mcp.py`: substring sem acento e sem caixa), com palavras só da pergunta (4+ letras, sem stopwords).
- Acerto = a página esperada está entre as 3 primeiras (Q3 e Q4 exigem todas as páginas esperadas). Harness: `tools/etapa4/`.

## Tabela

| n | pergunta | markdown: página? | markdown: ms | gbrain-search: página? | gbrain-search: ms |
|---|---|---|---|---|---|
| 1 | Que carro o Ricardo tem? | sim | 186 | não | 4638 |
| 2 | Quem é a esposa do Ricardo? | não | 44 | não | 3819 |
| 3 | Quem são as filhas dele? | não | 49 | não | 3234 |
| 4 | Quais empresas são holdings patrimoniais? | não | 42 | não | 2966 |
| 5 | Qual empresa era a NESS Law antes? | não | 43 | não | 5275 |
| 6 | Qual é a PJ do Ricardo? | não | 38 | não | 3536 |
| 7 | Giovanna é filha de qual mãe? | sim | 38 | sim | 3567 |
| 8 | Em qual empresa o Ricardo é CISO e cofundador? | sim | 39 | não | 3230 |
| 9 | Quem na família tem ficha, além da esposa e das filhas? | não | 34 | não | 3070 |
| 10 | O que ainda está pendente para resolver? | não | 39 | não | 3616 |
| | **total** | **3/10** | ~40 ms | **1/10** | 3–5 s |

RAM do GBrain por consulta: ~290 MB (Maximum resident set size 293.708 kB).

## Leitura
- Sem embeddings, o GBrain é uma busca por palavra-chave mais lenta (~80×) e mais pesada que a da Gabi, e não acertou nada que ela não acerte. Pelo critério do spec (ganhar nas perguntas 4, 6, 7, 8), não compensa; a camada semântica (Task 5, com chave e envio de texto ao provedor de embeddings) não foi rodada porque a camada keyless não mostrou ganho.
- Cérebro ainda pequeno (~100 páginas). O GBrain foi feito para milhares; num cérebro magro a busca simples empata ou ganha.
- Achado colateral: a busca da Gabi acerta 3/10 por casar só a palavra exata ("esposa" × "companheira", "filhas" × "filha", "holdings" × "holding"). Melhorar isso é barato e independe do GBrain.

## Para revalidar
1. Refazer o clone sem cofre e sem `docs/ tools/ tests/ skills/ deploy/` e reindexar.
2. Rodar `tools/etapa4/harness.py` nas camadas `markdown` e `gbrain-search`; se o GBrain ganhar nas perguntas 4, 6, 7, 8, rodar a camada semântica (Task 5 do plano `docs/superpowers/plans/2026-11-19-etapa4-gbrain.md`).
