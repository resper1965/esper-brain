# Mapa

| Onde | O quê |
|---|---|
| `hot.md` | o que está quente hoje (digestão diária reescreve) |
| `pendencias.md` | pendências soltas, com prazo e origem |
| `decisoes.md` | decisões do Ricardo (não financeiras), com data |
| `people/` | uma ficha por pessoa; `_aprovados.md` diz quem a Gabi escuta |
| `pessoal/familia/` | fichas da família (sem número de documento) |
| `pessoal/casa/` | pets, bens, casa, Home Assistant |
| `empresas/<nome>/` | empresas que o Ricardo toca: ness, ionic-health, baalbeck, fakiha, bekaa (README = cadastro, sócios, documentos societários) |
| `empresas/participacoes/` | uma ficha cadastral por empresa em que ele é sócio sem gerir |
| `pessoal/cofre/` | números de documento, CNPJ/IE/IM — **cifrado** (git-crypt); sem a chave aparece binário |
| `projetos/` | um tema por arquivo (ou pasta, se tiver documentos); formato em `projetos/_modelo.md` |
| `diario/AAAA/MM-DD.md` | nota do dia |
| `skills/` | instruções portáveis (digestão, salvar sessão, capturar, retomar) |

## Ferramentas fora do markdown
- **Dinheiro:** MCP `gabi-finance`. `gabi-finance projeto:N` = gastos/orçamento do projeto N.
- **Documentos:** Paperless. `paperless:123` = documento 123 → `<PAPERLESS_URL>/documents/123/details`.
- `gabi-brain pessoa:x` / `gabi-brain projeto:N` = id de origem na migração (some depois da virada).
