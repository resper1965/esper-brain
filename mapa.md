# Mapa

| Onde | O quê |
|---|---|
| `hot.md` | o que está quente hoje (digestão diária reescreve) |
| `pendencias.md` | pendências soltas, com prazo e origem |
| `decisoes.md` | decisões do Ricardo (não financeiras), com data |
| `people/` | uma ficha por pessoa; `_aprovados.md` diz quem a Gabi escuta |
| `pessoal/familia/` | fichas da família (sem número de documento) |
| `pessoal/casa/` | pets, bens, casa, Home Assistant |
| `empresas/<nome>.md` | uma ficha cadastral por empresa (sócios, quem assina, contrato social no Paperless); assuntos de trabalho ficam em `projetos/trabalho/<empresa>/` até a empresa ter cérebro próprio |
| `pessoal/cofre/` | números de documento, CNPJ/IE/IM — **cifrado** (git-crypt); sem a chave aparece binário |
| `projetos/<área>/` | temas por área: `familia/`, `trabalho/` (`ness/`, `ionic/<frente>/`, `bekaa/`, inclui freelancer), `patrimonio/` (`baalbeck/`, `fakiha/`), `saude/`, `casa/`, `pessoal/`; formato em `projetos/_modelo.md` |
| `entrada.md` | caixa de entrada: pedaços soltos com palpite, até a consolidação (skill `organizar`, 21:30) |
| `diario/AAAA/MM-DD.md` | nota do dia |
| `skills/` | instruções portáveis: `capturar`, `organizar`, `pensar-junto`, `retomar`, `salvar-sessao`, `digestao` (diária, 06:30), `vigiar` (avisos: diário 08:40, revisão segunda 08:50) |
| `tools/gravar.sh` | o único jeito de gravar: trava, pull --rebase, confere o cofre, commit, push |
| `tools/esper_mcp.py` | MCP `esper_brain`: a porta da Gabi para o cérebro (ler, buscar, anotar, gravar), sem shell |
| `deploy/hermes/` | instalação no Hermes da VPS (SOUL, ferramentas); passo a passo em `docs/etapa3a.md` |

## Ferramentas fora do markdown
- **Dinheiro:** MCP `gabi-finance`. `gabi-finance projeto:N` = gastos/orçamento do projeto N.
- **Documentos:** Paperless. `paperless:123` = documento 123 → `https://srv-hermes.tail985643.ts.net:8444/documents/123/details`.
- `gabi-brain pessoa:x` / `gabi-brain projeto:N` = id de origem na migração (some depois da virada).

## Endereços (só pela Tailscale)
A VPS se chama `srv-hermes` na Tailscale. Estes são os endereços para mandar ao Ricardo; `127.0.0.1` e sockets são internos, nunca mande. Os nomes antigos `gabi.` e `gabi-brain.tail985643.ts.net` não funcionam mais.

| O quê | Endereço |
|---|---|
| Painel do gabi-brain (agenda, e-mail, família, avisos) | https://srv-hermes.tail985643.ts.net |
| MCP do gabi-brain para agentes externos | https://srv-hermes.tail985643.ts.net:8443/mcp |
| Paperless (documentos) | https://srv-hermes.tail985643.ts.net:8444 |
| Painel do gabi-finance (dinheiro) | https://srv-hermes.tail985643.ts.net:8446 |
| Painel de temas (quadro estilo Trello do esper-brain) | https://srv-hermes.tail985643.ts.net:8448 |
| Hermes (painel do agente) | https://srv-hermes.tail985643.ts.net:8449 (login do dashboard: usuário e senha em `~/.hermes/config.yaml` › `dashboard.basic_auth`, nunca no cérebro; o endereço público está em `dashboard.public_url`) |
| GitHub do cérebro | https://github.com/resper1965/esper-brain |
